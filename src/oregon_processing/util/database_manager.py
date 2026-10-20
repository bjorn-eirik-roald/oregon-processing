from dataclasses import dataclass

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.communicator import Communicator
from oregon_processing.util.project import Project
from oregon_processing.util.util_functions import extract_filename_date

from datetime import date, datetime, timedelta
from pathlib import Path

from oregon_processing.util.system_status import SystemStatus

@dataclass
class ExportDates:
    detection_record_dates: list
    event_record_dates: list

class DatabaseManager:
    """Manages database directories and date range tracking for exports."""

    DEFAULT_FIRST_DATE = date(2018, 1, 1)

    def __init__(self, project: Project):
        """
        Initialize DatabaseManager.

        Parameters
        ----------
        project : Project
            Project instance for data directory
        """

        self._project = project

        # Root directories
        self._project_dir = project.project_dir
        self._log_dir = project.logs_dir
        self._crash_log_dir = project.crash_logs_dir
        self._export_dir = project.export_dir

        # Export data subdirectories
        self._detection_records_dir = None
        self._event_records_dir = None

    @property
    def logs_dir(self):
        return self._log_dir

    @property
    def detection_records_dir(self):
        return self._detection_records_dir

    @property
    def event_records_dir(self):
        return self._event_records_dir

    def prepare_directories(self, serial_number: str) -> None:
        """Prepare and create necessary directories for export."""

        LOGGER.debug("Preparing output directories.")

        # Define directories based on project directories and device serial number
        self._define_serial_number_directories(serial_number)

        LOGGER.info(f"Project directory: {self._project.project_dir}", extra={"_skip_path_alias_filter": True})
        LOGGER.debug(f"Root Export data directory: {self._project.export_dir}")
        LOGGER.debug(f"Detection records directory: {self._project.detection_record_export_dir}")
        LOGGER.debug(f"Event records directory: {self._project.event_record_export_dir}")
        LOGGER.debug(f"Export logs directory: {self._project.logs_dir}")
        LOGGER.debug(f"Crash logs directory: {self._project.crash_logs_dir}")


        # Create all directories
        directories = [
            (self._log_dir, "Export logs directory"),
            (self._crash_log_dir, "Crash logs directory"),
            (self._export_dir, "Root export data directory"),
            (self._detection_records_dir, "Detection records directory"),
            (self._event_records_dir, "Event records directory"),
        ]

        for dir_path, dir_name in directories:
            if not dir_path.exists():
                warning_message = f"{dir_name} directory was missing from: {dir_path}\nCreating directory..."
                LOGGER.warning(warning_message)
                dir_path.mkdir(parents=True, exist_ok=True)

    def get_export_dates(self) -> dict:
        """
        Determine missing dates by comparing present dates with expected date range.

        Includes the last available date as missing to account for potential incomplete
        exports (if exported mid-day, the last date's files may be incomplete).

        Returns
        -------
        ExportDates
            Object containing lists of missing/incomplete dates for detection records and event records
        """

        if self._detection_records_dir is None or self._event_records_dir is None:
            error_message = f"Directories not prepared yet. Call prepare_directories() first."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        LOGGER.debug("Scanning for existing detection record files...")
        detection_record_files = list(self._detection_records_dir.glob("*.txt"))
        LOGGER.debug(f"Found {len(detection_record_files)} detection record file(s) from current RFID reader.")

        LOGGER.debug("Scanning for existing event record files...")
        event_record_files = list(self._event_records_dir.glob("*.txt"))
        LOGGER.debug(f"Found {len(event_record_files)} event record file(s) from current RFID reader.")

        LOGGER.debug("Extracting dates from filenames...")

        detection_record_dates = set(extract_filename_date(f.name, logger=LOGGER) for f in detection_record_files)
        event_record_dates = set(extract_filename_date(f.name, logger=LOGGER) for f in event_record_files)

        # Generate expected date range from DEFAULT_FIRST_DATE to today
        today = date.today()
        current_date = self.DEFAULT_FIRST_DATE
        expected_dates = []
        while current_date <= today:
            expected_dates.append(current_date)
            current_date += timedelta(days=1)

        # Find missing dates for each file type
        missing_detection_file_dates = sorted([d for d in expected_dates if d not in detection_record_dates])
        missing_event_file_dates = sorted([d for d in expected_dates if d not in event_record_dates])

        # Get last available dates
        last_detection_file_date = max(detection_record_dates) if detection_record_dates else None
        last_event_file_date = max(event_record_dates) if event_record_dates else None

        # Add last available dates to missing list to account for potential incomplete exports
        if last_detection_file_date and last_detection_file_date not in missing_detection_file_dates:
            missing_detection_file_dates = sorted(missing_detection_file_dates + [last_detection_file_date])
        if last_event_file_date and last_event_file_date not in missing_event_file_dates:
            missing_event_file_dates = sorted(missing_event_file_dates + [last_event_file_date])

        # logging summary of missing dates
        LOGGER.debug(f"Detection records: {len(missing_detection_file_dates)} missing/incomplete date(s) out of {len(expected_dates)}")
        if missing_detection_file_dates:
            LOGGER.debug(f"Missing detection dates: {self._format_date_intervals(missing_detection_file_dates)}")

        # logging summary of missing dates
        LOGGER.debug(f"Event records: {len(missing_event_file_dates)} missing/incomplete date(s) out of {len(expected_dates)}")
        if missing_event_file_dates:
            LOGGER.debug(f"Missing event dates: {self._format_date_intervals(missing_event_file_dates)}")

        export_dates: ExportDates = ExportDates(
            detection_record_dates=missing_detection_file_dates,
            event_record_dates=missing_event_file_dates
        )

        return export_dates

    def get_last_exported_detection_record_dates(self) -> dict[str, date]:
        """
        Get the date of last exported detection record of all serial numbers in database.

        Returns
        -------
        dict[str, date]
            Dictionary mapping serial numbers to their last exported detection record date.
        """

        self._define_root_directories()

        root_detection_records_dir = self._project.detection_record_export_dir
        detection_record_dirs = list(root_detection_records_dir.glob("*")) # Get all subdirectories (serial numbers) in detection records directory

        last_exported_dates: dict[str, date] = {}
        for detection_record_dir in detection_record_dirs:
            serial = detection_record_dir.name
            LOGGER.debug(f"Checking detection record files for serial number: {serial}")


            detection_record_files = list(detection_record_dir.glob("*.txt"))
            if not detection_record_files:
                LOGGER.debug("No existing detection record files found.")
                last_exported_dates[serial] = None
                continue

            detection_record_dates = set(extract_filename_date(f.name, logger=LOGGER) for f in detection_record_files)

            last_exported_date = max(detection_record_dates)
            LOGGER.debug(f"Last exported date based on existing detection record files: {last_exported_date}")
            last_exported_dates[serial] = last_exported_date

        return last_exported_dates

    @classmethod
    def prepare_crash_log_file(cls, project: Project) -> Path:
        """Prepare and return the crash logs directory path."""
        crash_logs_dir = project.crash_logs_dir
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        crash_log_file = crash_logs_dir / f"crash_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        return crash_log_file

    def _define_serial_number_directories(self, serial_number: str) -> None:
        # Add serial number subdirectory to export logs, detection records, and event records
        self._log_dir = self._project.logs_dir / serial_number
        self._detection_records_dir = self._project.detection_record_export_dir / serial_number
        self._event_records_dir = self._project.event_record_export_dir / serial_number

    def _format_date_intervals(self, dates: list) -> str:
        """
        Convert a list of dates into formatted intervals.

        Parameters
        ----------
        dates : list
            Sorted list of date objects

        Returns
        -------
        str
            Formatted string of date intervals (e.g., "2021-01-01 to 2021-01-15, 2021-02-01 to 2021-02-10")
        """
        if not dates:
            return "None"

        intervals = []
        interval_start = dates[0]
        interval_end = dates[0]

        for date_obj in dates[1:]:
            if (date_obj - interval_end).days == 1:
                # Consecutive date, extend interval
                interval_end = date_obj
            else:
                # Gap found, save interval and start new one
                if interval_start == interval_end:
                    intervals.append(str(interval_start))
                else:
                    intervals.append(f"{interval_start} to {interval_end}")
                interval_start = date_obj
                interval_end = date_obj

        # Add final interval
        if interval_start == interval_end:
            intervals.append(str(interval_start))
        else:
            intervals.append(f"{interval_start} to {interval_end}")

        return ", ".join(intervals)

