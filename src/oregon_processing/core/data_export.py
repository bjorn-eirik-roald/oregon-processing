import time
from datetime import date, datetime
from collections import defaultdict
from pathlib import Path

from oregon_processing.core.device_mode import DeviceMode, change_mode, get_current_mode
from oregon_processing.core.device_status import DeviceStatus, DeviceStatusChecker
from oregon_processing.core.device_format import FormatInfo, get_format_info, set_detection_record_format
from oregon_processing.core.upload_history import UploadHistory, get_upload_history
from oregon_processing.core.communication import DeviceCommand, ConnectionSession
from oregon_processing.exceptions import ExportFailedError


from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

DEFAULT_DETECTION_RECORD_FORMAT = {'ORSR':'DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA LON LAT',
                                    'ORMR':'DTY ARR SPC TRF DUR SPC TTY SPC ANT TAG SCD NCD EFA LON LAT'}

SEPARATOR = ','

def export_detection_records(dates: list[datetime], output_dir: Path,  session: ConnectionSession, device_status_checker: DeviceStatusChecker) -> bool:

    old_mode = _enter_export_mode(session, device_status_checker)
    device_status = device_status_checker.get_device_status()

    upload_history: UploadHistory = get_upload_history(session, device_status_checker)
    total_number_of_records = upload_history.total_records
    _log_export_start(total_number_of_records, output_dir, len(dates))

    _configure_detection_record_format(session, device_status_checker, device_status)
    response = _request_all_records(session, total_number_of_records)

    format_info = get_format_info(session, device_status_checker)
    arr_idx, tag_idx = _get_required_format_indices(format_info)

    target_dates = set(d.strftime("%Y-%m-%d") for d in dates)
    filtered_detection_records = _filter_detection_records(response, format_info, arr_idx, target_dates)
    detection_records_by_date, unique_tags_by_date, unique_tags = _organize_detection_records(
        filtered_detection_records,
        arr_idx,
        tag_idx,
        SEPARATOR
    )

    all_dates = sorted(dates)
    summary_message = _create_summary_message(filtered_detection_records, detection_records_by_date, unique_tags, len(all_dates))

    num_failed_exports = _write_detection_record_exports(
        output_dir=output_dir,
        device_status=device_status,
        all_dates=all_dates,
        detection_records_by_date=detection_records_by_date,
        unique_tags_by_date=unique_tags_by_date,
        format_info=format_info
    )

    _log_export_completion(num_failed_exports, summary_message)
    _restore_mode(session, device_status_checker, old_mode)
    return num_failed_exports == 0


def _enter_export_mode(session: ConnectionSession, device_status_checker: DeviceStatusChecker) -> str:
    old_mode = get_current_mode(session, device_status_checker)
    change_mode(session, device_status_checker, DeviceMode.STANDBY)
    LOGGER.info(f"Changed device mode to Standby for export. Will return to {old_mode} mode after export is complete.")
    return old_mode


def _log_export_start(total_number_of_records: int, output_dir: Path, num_dates: int) -> None:
    LOGGER.info("Initializing export of detection records from {} date(s).".format(num_dates))
    LOGGER.debug(f"Total records on device: {total_number_of_records}")
    LOGGER.debug(f"Output directory: {output_dir}")


def _configure_detection_record_format(
    session: ConnectionSession,
    device_status_checker: DeviceStatusChecker,
    device_status: DeviceStatus
) -> None:
    LOGGER.debug("Setting detection record format for export.")
    default_format = DEFAULT_DETECTION_RECORD_FORMAT[device_status.device_type]
    set_detection_record_format(session, device_status_checker, default_format)


def _request_all_records(session: ConnectionSession, total_number_of_records: int) -> list[str]:
    LOGGER.info(f"Requesting all ({total_number_of_records}) records from device. This may take a while if there are many records on the device. Please wait...")
    try:
        response = session.send_command(DeviceCommand.UP_ALL)
    except Exception as e:
        LOGGER.error(f"Failed to retrieve records from device: {e}")
        raise ExportFailedError(f"Failed to retrieve records from device: {e}")
    LOGGER.info("All records received.")
    return response


def _get_required_format_indices(format_info: FormatInfo) -> tuple[int, int]:
    arr_idx = format_info.column_indices.get('ARR', None)
    tag_idx = format_info.column_indices.get('TAG', None)

    if arr_idx is None:
        error_message = "ARR index not found in detection record format info. This is required for date filtering. Cannot continue."
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    if tag_idx is None:
        error_message = "TAG index not found in detection record format info. This is required for unique tag counting. Cannot continue."
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    return arr_idx, tag_idx


def _filter_detection_records(
    response: list[str],
    format_info: FormatInfo,
    arr_idx: int,
    target_dates: set[str]
) -> list[list[str]]:
    LOGGER.debug("Filtering detection records to export dates.")

    filtered_detection_records: list[list[str]] = []
    for line in response:
        if not line.startswith("S"):
            continue

        try:
            parts = _split_detection_record(line, format_info)
        except ValueError:
            LOGGER.error(f"Error: Encountered malformed detection record during filtering. Skipping record: {line}")
            continue

        record_date_str = parts[arr_idx].split()[0]
        if record_date_str in target_dates:
            filtered_detection_records.append(parts)

    LOGGER.debug("Detection records filtered successfully.")
    return filtered_detection_records


def _organize_detection_records(
    filtered_detection_records: list[list[str]],
    arr_idx: int,
    tag_idx: int,
) -> tuple[dict[date, list[str]], dict[date, set[str]], set[str]]:
    LOGGER.debug("Organizing detection records by date.")
    detection_records_by_date: defaultdict[date, list[str]] = defaultdict(list)
    unique_tags_by_date: defaultdict[date, set[str]] = defaultdict(set)
    unique_tags: set[str] = set()

    for detection_record in filtered_detection_records:
        record_date = datetime.strptime(detection_record[arr_idx].split()[0], "%Y-%m-%d").date()
        record_tag = detection_record[tag_idx]
        output_line = SEPARATOR.join(detection_record)

        detection_records_by_date[record_date].append(output_line)
        unique_tags_by_date[record_date].add(record_tag)
        unique_tags.add(record_tag)

    LOGGER.debug("Detection records organized by date successfully.")
    return detection_records_by_date, unique_tags_by_date, unique_tags


def _create_summary_message(
    filtered_detection_records: list[list[str]],
    detection_records_by_date: dict[date, list[str]],
    unique_tags: set[str],
    num_dates: int
) -> str:
    max_summary_width = max(
        len(str(len(filtered_detection_records))),
        len(str(len(detection_records_by_date))),
        len(str(num_dates - len(detection_records_by_date)))
    )

    return (f"Detection Records Summary:\n"
        f"    Total detection records in date range: {str(len(filtered_detection_records)).rjust(max_summary_width)}\n"
        f"    Number of dates with records:          {str(len(detection_records_by_date)).rjust(max_summary_width)}\n"
        f"    Number of dates without records:       {str(num_dates - len(detection_records_by_date)).rjust(max_summary_width)}\n"
        f"    Number of unique tags detected:        {str(len(unique_tags)).rjust(max_summary_width)}"
    )


def _write_detection_record_exports(
    output_dir: Path,
    device_status: DeviceStatus,
    all_dates: list[datetime],
    detection_records_by_date: dict[date, list[str]],
    unique_tags_by_date: dict[date, set[str]],
    format_info: FormatInfo
) -> int:
    num_dates = len(all_dates)
    max_counter_width = len(f"({num_dates}/{num_dates})")
    max_record_count = max((len(recs) for recs in detection_records_by_date.values()), default=0)
    max_count_width = len(str(max_record_count))
    max_unique_tags = max((len(tags) for tags in unique_tags_by_date.values()), default=0)
    max_unique_tags_width = len(str(max_unique_tags))
    format_columns_str = SEPARATOR.join(format_info.columns)

    num_failed_exports = 0
    LOGGER.info("Exporting detection records to files.")
    for date_num, current_date in enumerate(all_dates):
        output_filepath = f"{output_dir}/{device_status.serial_number}_detection_records_{current_date.strftime('%Y_%m_%d')}.txt"
        counter = f"({date_num + 1}/{num_dates})"
        spacing = " " * (max_counter_width - len(counter))

        if current_date not in detection_records_by_date:
            count_str = "0".rjust(max_count_width)
            unique_tags_str = "0".rjust(max_unique_tags_width)
        else:
            count_str = str(len(detection_records_by_date[current_date])).rjust(max_count_width)
            unique_tags_str = str(len(unique_tags_by_date[current_date])).rjust(max_unique_tags_width)

        LOGGER.info(f"{spacing}Export {counter}. Exporting data from {current_date}. Number of detection records: {count_str}. Unique tags: {unique_tags_str}.")

        try:
            with open(output_filepath, 'w') as f:
                f.write("Oregon RFID Detection Records\n")
                f.write(f"Device Serial Number: {device_status.serial_number}\n")
                f.write(f"Device Type: {device_status.device_type}\n")
                f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("Date of Record: " + current_date.strftime("%Y-%m-%d") + "\n")
                f.write("Number of Records: " + count_str.strip() + "\n")
                f.write("Number of unique tags: " + unique_tags_str.strip() + "\n")
                f.write("=========================\n\n")
                f.write("Field Names:\n")
                for col, field_name in format_info.field_names.items():
                    f.write(f"{col}: {field_name}\n")
                f.write("=========================\n\n")
                f.write("#RECORDS START HERE\n")
                f.write(f"{format_columns_str.replace(' ', SEPARATOR)}\n")
                if current_date in detection_records_by_date:
                    f.write('\n'.join(detection_records_by_date[current_date]))
        except Exception as e:
            LOGGER.error(f"Failed to write detection records for {current_date} to file: {e}")
            num_failed_exports += 1

    return num_failed_exports


def _log_export_completion(num_failed_exports: int, summary_message: str) -> None:
    if num_failed_exports == 0:
        LOGGER.info("All detection record exports completed successfully.")
    else:
        LOGGER.warning(f"{num_failed_exports} detection record exports failed. Please check the logs for details.")
    LOGGER.info(summary_message)


def _restore_mode(session: ConnectionSession, device_status_checker: DeviceStatusChecker, old_mode: str) -> None:
    change_mode(session, device_status_checker, old_mode)
    LOGGER.info(f"Returned device mode to {old_mode} after export.")

def _split_detection_record(record_line: str, format_info: FormatInfo) -> list[str]:
    """
    Split a detection record line into parts, handling the ARR field which contains spaces.

    The ARR (arrival datetime) field has the format "YYYY-MM-DD HH:MM:SS.ddd" which contains
    a space between the date and time. When splitting by spaces, this creates two tokens
    instead of one, so we need to merge them back together.

    Note: Some records may be missing trailing fields (e.g., HDP) that FM reports.

    Parameters
    ----------
    record_line : str
        The detection record line to split
    format_info : FormatInfo
        Parsed format metadata containing column order and index lookups.

    Returns
    -------
    list[str]
        List of field values with ARR properly merged if present

    Raises
    ------
    ValueError
        If the record has an unexpected number of parts
    """
    # Split by spaces
    parts = record_line.split()

    column_indices = format_info.column_indices
    arr_index = column_indices.get('ARR')

    if arr_index is None:
        raise ValueError(
            "ARR index not found in format info. ARR field is required for proper splitting of detection records. "
            f"From format info: {format_info}"
        )

    # If ARR is in the format, we expect one extra part (because ARR contains a space)
    # Check if we have enough parts to merge ARR
    if len(parts) < arr_index + 2:
        raise ValueError(
            f"Not enough parts to merge ARR at index {arr_index}, got {len(parts)} parts. Record line: '{record_line}'"
        )

    # Merge the two ARR parts (date and time) back together
    # The date part is at arr_index, time part is at arr_index+1
    arr_date = parts[arr_index]
    arr_time = parts[arr_index + 1]
    parts[arr_index] = f"{arr_date} {arr_time}"

    # Remove the time part (which is now merged into arr_index)
    parts.pop(arr_index + 1)

    # After merging, we might have fewer parts than columns if trailing fields are missing
    # This is acceptable - some records may not have all fields (e.g., HDP)

    return parts
