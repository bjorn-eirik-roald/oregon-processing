from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from oregon_processing.util.logging_manager import get_logger
from oregon_processing.core.project import get_project
from oregon_processing.util.util_functions import extract_filename_date

LOGGER = get_logger(__name__)

DEFAULT_FIRST_DATE = date(2018, 1, 1)


@dataclass
class DatabasePaths:
    project_dir: Path
    logs_dir: Path
    crash_logs_dir: Path
    export_dir: Path
    detection_records_dir: Path


def prepare_directories(serial_number: str) -> DatabasePaths:
    """Prepare and create necessary directories for export."""
    LOGGER.debug("Preparing output directories.")

    project = get_project()
    database_paths = _define_serial_number_directories(serial_number)

    LOGGER.info(f"Project directory: {project.project_dir}", extra={"_skip_path_alias_filter": True})
    LOGGER.debug(f"Root Export data directory: {project.export_dir}")
    LOGGER.debug(f"Detection records directory: {project.detection_record_export_dir}")
    LOGGER.debug(f"Export logs directory: {project.logs_dir}")
    LOGGER.debug(f"Crash logs directory: {project.crash_logs_dir}")

    directories = [
        (database_paths.logs_dir, "Export logs directory"),
        (database_paths.crash_logs_dir, "Crash logs directory"),
        (database_paths.export_dir, "Root export data directory"),
        (database_paths.detection_records_dir, "Detection records directory"),
    ]

    for dir_path, dir_name in directories:
        if not dir_path.exists():
            warning_message = f"{dir_name} directory was missing from: {dir_path}\nCreating directory..."
            LOGGER.warning(warning_message)
            dir_path.mkdir(parents=True, exist_ok=True)
            LOGGER.info(f"Created missing directory: {dir_path}")

    return database_paths


def get_export_dates(database_paths: DatabasePaths) -> list[date]:
    """
    Determine missing dates by comparing present dates with expected date range.

    Includes the last available date as missing to account for potential incomplete
    exports (if exported mid-day, the last date's files may be incomplete).
    """
    LOGGER.debug("Scanning for existing detection record files...")
    detection_record_files = list(database_paths.detection_records_dir.glob("*.txt"))
    LOGGER.debug(f"Found {len(detection_record_files)} detection record file(s) from current RFID reader.")

    LOGGER.debug("Extracting dates from filenames...")
    detection_record_dates = set(extract_filename_date(f.name) for f in detection_record_files)

    expected_dates = _build_expected_dates(DEFAULT_FIRST_DATE, date.today())

    missing_detection_file_dates = sorted([d for d in expected_dates if d not in detection_record_dates])

    last_detection_file_date = max(detection_record_dates) if detection_record_dates else None

    if last_detection_file_date and last_detection_file_date not in missing_detection_file_dates:
        missing_detection_file_dates = sorted(missing_detection_file_dates + [last_detection_file_date])

    LOGGER.debug(f"Detection records: {len(missing_detection_file_dates)} missing/incomplete date(s) out of {len(expected_dates)}")
    if missing_detection_file_dates:
        LOGGER.debug(f"Missing detection dates: {_format_date_intervals(missing_detection_file_dates)}")

    return missing_detection_file_dates


def get_last_exported_detection_record_dates() -> dict[str, date | None]:
    """
    Get the date of last exported detection record of all serial numbers in database.

    Returns
    -------
    dict[str, date | None]
        Dictionary mapping serial numbers to their last exported detection record date.
    """
    project = get_project()
    root_detection_records_dir = project.detection_record_export_dir
    detection_record_dirs = [path for path in root_detection_records_dir.glob("*") if path.is_dir()]

    last_exported_dates: dict[str, date | None] = {}
    for detection_record_dir in detection_record_dirs:
        serial = detection_record_dir.name
        LOGGER.debug(f"Checking detection record files for serial number: {serial}")

        detection_record_files = list(detection_record_dir.glob("*.txt"))
        if not detection_record_files:
            LOGGER.debug("No existing detection record files found.")
            last_exported_dates[serial] = None
            continue

        detection_record_dates = set(extract_filename_date(f.name) for f in detection_record_files)
        last_exported_date = max(detection_record_dates)
        LOGGER.debug(f"Last exported date based on existing detection record files: {last_exported_date}")
        last_exported_dates[serial] = last_exported_date

    return last_exported_dates


def print_last_exported_detection_record_dates() -> None:
    """Print an overview of most recent detection record dates by serial number."""
    latest_record_dates = get_last_exported_detection_record_dates()

    # sort from least recent to most recent
    latest_record_dates = dict(sorted(latest_record_dates.items(), key=lambda item: (item[1] is not None, item[1])))

    if not latest_record_dates:
        print("No detection record files found for any serial number.")
        return

    print("\nMost Recent Detection Record Dates by Serial Number:")
    for serial, record_date in latest_record_dates.items():
        if record_date:
            print(f"Serial Number: {serial} - Last Exported Detection Record Date: {record_date}")
        else:
            print(f"Serial Number: {serial} - No detection record files found.")


def prepare_crash_log_file() -> Path:
    """Prepare and return the crash logs directory path."""
    project = get_project()
    crash_logs_dir = project.crash_logs_dir
    crash_logs_dir.mkdir(parents=True, exist_ok=True)
    return crash_logs_dir / f"crash_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def _define_serial_number_directories(serial_number: str) -> DatabasePaths:
    project = get_project()
    return DatabasePaths(
        project_dir=project.project_dir,
        logs_dir=project.logs_dir / serial_number,
        crash_logs_dir=project.crash_logs_dir,
        export_dir=project.export_dir,
        detection_records_dir=project.detection_record_export_dir / serial_number,
    )


def _build_expected_dates(start_date: date, end_date: date) -> list[date]:
    expected_dates: list[date] = []
    current_date = start_date
    while current_date <= end_date:
        expected_dates.append(current_date)
        current_date += timedelta(days=1)
    return expected_dates


def _format_date_intervals(dates: list[date]) -> str:
    """Convert a list of dates into formatted intervals."""
    if not dates:
        return "None"

    intervals: list[str] = []
    interval_start = dates[0]
    interval_end = dates[0]

    for date_obj in dates[1:]:
        if (date_obj - interval_end).days == 1:
            interval_end = date_obj
        else:
            if interval_start == interval_end:
                intervals.append(str(interval_start))
            else:
                intervals.append(f"{interval_start} to {interval_end}")
            interval_start = date_obj
            interval_end = date_obj

    if interval_start == interval_end:
        intervals.append(str(interval_start))
    else:
        intervals.append(f"{interval_start} to {interval_end}")

    return ", ".join(intervals)
