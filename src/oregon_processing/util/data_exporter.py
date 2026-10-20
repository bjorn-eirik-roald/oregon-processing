# -*- coding: utf-8 -*-
"""
Data Exporter for Oregon RFID device data
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import time
from datetime import datetime
from pathlib import Path

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.device_mode_manager import DeviceModeManager
from oregon_processing.util.system_status import SystemStatus, SystemStatusChecker
from oregon_processing.util.upload_history import UploadHistory, UploadHistoryChecker

if TYPE_CHECKING:
    from oregon_processing.util.format_manager import FormatManager
    from oregon_processing.util.command_manager import CommandManager


class DataExporter:
    """Handles exporting data from the Oregon RFID communicator."""

    DEFAULT_DETECTION_RECORD_FORMAT = {'ORSR':'DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA LON LAT',
                                       'ORMR':'DTY ARR SPC TRF DUR SPC TTY SPC ANT TAG SCD NCD EFA LON LAT'}
    def __init__(self, command_manager: CommandManager, format_manager: FormatManager,
                 upload_history_checker: UploadHistoryChecker, mode_manager: DeviceModeManager,
                 system_status_checker: SystemStatusChecker):
        """
        Initialize DataExporter with communicator and manager instances.

        Parameters
        ----------
        format_manager : FormatManager
            Format manager instance for handling detection record format operations.
        command_manager : CommandManager
            Command manager instance for sending commands to device.
        upload_history_checker : UploadHistoryChecker
            Upload history checker instance for managing upload history.
        mode_manager : DeviceModeManager
            Mode manager instance for handling device mode operations.
        system_status_checker : SystemStatus
            System status checker instance for monitoring system status.
        """

        self._format_manager: FormatManager = format_manager
        self._command_manager: CommandManager = command_manager
        self._upload_history_checker: UploadHistoryChecker = upload_history_checker
        self._mode_manager: DeviceModeManager = mode_manager
        self._system_status_checker: SystemStatusChecker = system_status_checker

    def export_event_records(self, dates: list, output_dir: Path = Path("")) -> bool:
        """
        Export event records for specified dates.

        This method retrieves event records for each day in the specified date list
        using the ER command.

        Parameters
        ----------
        dates : list
            List of date objects to export
        output_dir : Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if not dates:
            LOGGER.warning("No dates provided for export. No event records will be exported.")
            return False

        system_status: SystemStatus = self._system_status_checker.get_system_status()

        old_mode = None
        mode = self._mode_manager.get_current_mode()
        if mode != 'Standby':
            old_mode = mode
            self._mode_manager.change_mode('Standby')
            LOGGER.info(f"Changed device mode to Standby for export. Will return to {old_mode} mode after export is complete.")

        # Header
        LOGGER.info("Initializing export of event records from {} date(s).".format(len(dates)))
        LOGGER.debug(f"Output directory: {output_dir}")

        # Prepare ranges and formatting
        num_dates = len(dates)
        all_dates = sorted(dates)
        max_counter_width = len(f"({num_dates}/{num_dates})")

        all_successful = True
        export_count = 0

        LOGGER.debug("Exporting event records to files.")
        for date_num, current_date in enumerate(all_dates):

            output_filepath = output_dir / f"{system_status.serial_number}_event_records_{current_date.strftime('%Y_%m_%d')}.txt"

            counter = f"({date_num + 1}/{num_dates})"
            spacing = " " * (max_counter_width - len(counter))
            message = f"{spacing}Export {counter}. Exporting event log from {current_date}."

            try:
                success = True
                # Send ER command with date
                command = f"ER {current_date.strftime('%Y-%m-%d')}"
                response = self._command_manager.send_command(command)
            except Exception as e:
                message += f" Failed to export. {e}"

                LOGGER.error(message)
                success = False
                all_successful = False
                response = []

            if success:
                # Generate output filename with date
                with open(output_filepath, 'w') as f:
                    f.write("Oregon RFID Event Records\n")
                    f.write(f"Device Serial Number: {system_status.serial_number}\n")
                    f.write(f"Device Type: {system_status.device_type}\n")
                    f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("Date of Records: " + current_date.strftime("%Y-%m-%d") + "\n")
                    f.write("=========================\n\n")

                    # Write event records
                    f.write("#RECORDS START HERE\n")
                    f.write('\n'.join(response))

                n_lines = max(len(response) - 3, 0) # correct for header lines in response and also account for completely empty responses
                message += f" Lines written: {n_lines}."
                LOGGER.info(message)
                export_count += 1
            else:
                message += "Failed to export event records for this date."
                LOGGER.error(message)

        failed_exports = num_dates - export_count



        if all_successful:
            LOGGER.info("Completed Event Record Export. Total dates processed: {}.".format(num_dates))
        if not all_successful:
            LOGGER.warning(f"Completed Event Record Export with {failed_exports} exports failed.")

        if old_mode:
            self._mode_manager.change_mode(old_mode)
            LOGGER.info(f"Returned device mode to {old_mode} after export.")

        return True if all_successful else False



    def export_detection_records(self, dates: list, output_dir: Path = Path(""), sep=',') -> bool:
        """
        Export detection records (S-type) for specified dates using the UP* command.

        The UP* command returns all record types (S: Detection, E: Event, G: GNSS),
        but this method filters and exports only detection records (S-type) for
        the specified dates.

        Parameters
        ----------
        dates : list
            List of date objects to export
        output_dir : str or Path
            Directory where output files will be written (default: current directory)
        sep : str, optional
            Separator to use in the output file (default: ',')

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """

        if not dates:
            LOGGER.warning("No dates provided for export. No detection records will be exported.")
            return False

        system_status: SystemStatus = self._system_status_checker.get_system_status()

        old_mode = None
        mode = self._mode_manager.get_current_mode()
        if mode != 'Standby':
            old_mode = mode
            self._mode_manager.change_mode('Standby')
            LOGGER.info(f"Changed device mode to Standby for export. Will return to {old_mode} mode after export is complete.")

        upload_history: UploadHistory = self._upload_history_checker.get_upload_history()
        total_number_of_records = upload_history.total_records

        LOGGER.info("Initializing export of detection records from {} date(s).".format(len(dates)))
        LOGGER.debug(f"Total records on device: {total_number_of_records}")
        LOGGER.debug(f"Output directory: {output_dir}")


        LOGGER.debug("Setting detection record format for export.")

        default_format = self.DEFAULT_DETECTION_RECORD_FORMAT[system_status.device_type]
        if not self._format_manager.set_detection_record_format(default_format):
            LOGGER.error("Failed to set detection record format. Cannot continue.")
            return False

        LOGGER.debug("Detection record format set successfully.")

        LOGGER.info(f"Requesting all ({total_number_of_records}) records from device. This may take a while if there are many records on the device. Please wait...")

        try:
            response = self._command_manager.send_command("UP*")
        except Exception as e:
            LOGGER.error(f"Failed to retrieve records from device: {e}")
            return False

        LOGGER.info("All records received.")

        # Retrieve detection record format to determine column order, tag index, and datetime index

        format_info = self._format_manager.get_format_info()
        format_columns_str = sep.join(format_info['columns'])
        column_indices = format_info['column_indices']
        arr_idx = column_indices.get('ARR')
        tag_idx = column_indices.get('TAG')

        if arr_idx is None:
            error_message = "ARR index not found in detection record format info. This is required for date filtering. Cannot continue."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if tag_idx is None:
            error_message = "TAG index not found in detection record format info. This is required for unique tag counting. Cannot continue."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        LOGGER.debug("Filtering detection records to export dates.")
        # Convert dates to strings for comparison (YYYY-MM-DD format sorts chronologically)
        target_dates_set = set(d.strftime("%Y-%m-%d") for d in dates)

        # Filter detection records (S-type) for specified dates
        filtered_detection_records = []
        for line in response:
            if not line.startswith("S"):
                continue

            # Split detection record properly handling ARR datetime field
            try:
                parts = self._split_detection_record(line, format_info)
            except ValueError:
                LOGGER.error(f"Error: Encountered malformed detection record during filtering. Skipping record: {line}")
                continue  # Skip malformed detection records

            # Extract date portion from ARR field (YYYY-MM-DD HH:MM:SS.ddd)
            record_date_str = parts[arr_idx].split()[0]  # Get YYYY-MM-DD part

            if record_date_str in target_dates_set:
                filtered_detection_records.append(parts)

        LOGGER.debug("Detection records filtered successfully.")

        LOGGER.debug("Organizing detection records by date.")
        detection_records_by_date = {}  # dict with date keys and list of detection records values
        unique_tags_by_date = {}        # dict with date keys and set of unique tags values
        all_dates = sorted(dates)
        num_dates = len(all_dates)

        unique_tags = set()

        current_date = None
        for detection_record in filtered_detection_records:

            record_date = datetime.strptime(detection_record[arr_idx].split()[0], "%Y-%m-%d").date()
            record_tag = detection_record[tag_idx]

            # first time seeing this date, initialize list and set for it
            if record_date != current_date:
                current_date = record_date
                detection_records_by_date[current_date] = []
                unique_tags_by_date[current_date] = set()

            output_line = sep.join(detection_record)
            detection_records_by_date[current_date].append(output_line)
            unique_tags_by_date[current_date].add(record_tag)
            unique_tags.add(record_tag)

        LOGGER.debug("Detection records organized by date successfully.")

        # Calculate max width for summary number alignment
        max_summary_width = max(
            len(str(len(filtered_detection_records))),
            len(str(len(detection_records_by_date))),
            len(str(num_dates - len(detection_records_by_date)))
        )

        summary_message = (f"Detection Records Summary:\n"
            f"    Total detection records in date range: {str(len(filtered_detection_records)).rjust(max_summary_width)}\n"
            f"    Number of dates with records:          {str(len(detection_records_by_date)).rjust(max_summary_width)}\n"
            f"    Number of dates without records:       {str(num_dates - len(detection_records_by_date)).rjust(max_summary_width)}\n"
            f"    Number of unique tags detected:        {str(len(unique_tags)).rjust(max_summary_width)}"
        )


        # Calculate max width for counter alignment
        max_counter_width = len(f"({num_dates}/{num_dates})")

        # Calculate max width for record count alignment
        max_record_count = max((len(recs) for recs in detection_records_by_date.values()), default=0)
        max_count_width = len(str(max_record_count))

        # Calculate max width for unique tags alignment
        max_unique_tags = max((len(tags) for tags in unique_tags_by_date.values()), default=0)
        max_unique_tags_width = len(str(max_unique_tags))

        all_successful = True
        num_failed_exports = 0
        LOGGER.info("Exporting detection records to files.")
        for date_num, current_date in enumerate(all_dates):
            output_filepath = f"{output_dir}/{system_status.serial_number}_detection_records_{current_date.strftime('%Y_%m_%d')}.txt"
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
                    f.write(f"Device Serial Number: {system_status.serial_number}\n")
                    f.write(f"Device Type: {system_status.device_type}\n")
                    f.write("Export Date/Time: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write("Date of Record: " + current_date.strftime("%Y-%m-%d") + "\n")
                    f.write("Number of Records: " + count_str.strip() + "\n")
                    f.write("Number of unique tags: " + unique_tags_str.strip() + "\n")
                    f.write("=========================\n\n")
                    f.write("Field Names:\n")
                    for col, field_name in format_info['field_names'].items():
                        f.write(f"{col}: {field_name}\n")
                    f.write("=========================\n\n")
                    f.write("#RECORDS START HERE\n")
                    f.write(f"{format_columns_str.replace(' ', sep)}\n")
                    # Write detection records for the date
                    if current_date in detection_records_by_date:
                        f.write('\n'.join(detection_records_by_date[current_date]))
            except Exception as e:
                LOGGER.error(f"Failed to write detection records for {current_date} to file: {e}")
                all_successful = False
                num_failed_exports += 1
                continue

        if all_successful:
            LOGGER.info("All detection record exports completed successfully.")
        else:
            LOGGER.warning(f"{num_failed_exports} detection record exports failed. Please check the logs for details.")

        LOGGER.info(summary_message)

        if old_mode:
            self._mode_manager.change_mode(old_mode)
            LOGGER.info(f"Returned device mode to {old_mode} after export.")

        return all_successful

    def _split_detection_record(self, record_line: str, format_info: dict) -> list:
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
        format_info : dict
            Format information containing 'columns' and 'column_indices'

        Returns
        -------
        list
            List of field values with ARR properly merged if present

        Raises
        ------
        ValueError
            If the record has an unexpected number of parts
        """
        # Split by spaces
        parts = record_line.split()

        column_indices = format_info['column_indices']
        arr_index = column_indices.get('ARR')

        if arr_index is None:
            raise ValueError("ARR index not found in format info. ARR field is required for proper splitting of detection records. From format info: {}".format(format_info))

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


