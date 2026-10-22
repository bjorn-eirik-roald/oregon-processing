from datetime import datetime, date
from pathlib import Path

from oregon_processing.core.communicator import Communicator
from oregon_processing.core.database_manager import (
    DatabasePaths,
    get_export_dates,
    prepare_crash_log_file,
    prepare_directories,
    )

from oregon_processing.core.device_clock import ClockCheckResult
from oregon_processing.core.device_health import DeviceHealth
from oregon_processing.core.device_status import DeviceStatus
from oregon_processing.core.project import open_previous_project

from oregon_processing.exceptions import DeviceHealthError
from oregon_processing.util.logging_manager import LoggingManager, get_logger
LOGGER = get_logger(__name__)


def run_export_protocol() -> None:
    LOGGER.info("Oregon RFID Export Protocol Initiated")

    open_previous_project()
    crash_log_file: Path = prepare_crash_log_file()

    with LoggingManager(
        write_to_console=True,
        write_to_report_file=True,
        report_file=crash_log_file
    ) as logging_manager, Communicator() as communicator:
        communicator.connect()

        device_serial: DeviceStatus = communicator.get_device_status().serial_number
        database_paths: DatabasePaths = prepare_directories(device_serial)

        report_file_dir = database_paths.logs_dir
        report_file = report_file_dir / f"export_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging_manager.transfer_log_file(report_file)

        if not communicator.is_connected:
            LOGGER.error("Oregon RFID device is not connected. Aborting.")
            return

        health_report: DeviceHealth = communicator.check_device_health()
        if len(health_report.critical_warnings) > 0:
            error_message = "Device health check failed. Please address the following critical issues before proceeding: \n  -" + "\n  -".join(health_report.critical_warnings)
            LOGGER.error(error_message)
            raise DeviceHealthError(error_message)

        clock_check_result: ClockCheckResult = communicator.control_device_datetime(tolerance_seconds=10)
        if not clock_check_result.synchronized:
            error_message = "Device clock is not in sync and could not be automatically updated. Please address the issue before proceeding."
            LOGGER.error(error_message)
            raise DeviceHealthError(error_message)

        export_dates: list[date] = get_export_dates(database_paths)

        communicator.export_detection_records(
            dates=export_dates,
            output_dir=database_paths.detection_records_dir
        )
        LOGGER.info("Export protocol completed successfully.")
