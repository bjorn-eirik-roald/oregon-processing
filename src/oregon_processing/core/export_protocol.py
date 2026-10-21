from contextlib import ExitStack
from datetime import datetime

from oregon_processing.core.communicator import Communicator
from oregon_processing.util.config import OregonConfig
from oregon_processing.core.database_manager import DatabaseManager, ExportDates
from oregon_processing.util.logging_manager import LoggingManager, get_logger
LOGGER = get_logger(__name__)

from oregon_processing.core.device_clock import ClockCheckResult
from oregon_processing.core.device_health import DeviceHealth
from oregon_processing.exceptions import CommandTransmissionError, ConfigNotFoundError, ConnectionFailedError, DeviceHealthError, InvalidConfigError, NoFileSelectedError, UnexpectedResponseError, UserCancelledError
from oregon_processing.core.popups.yes_no_popup import prompt_yes_no
from oregon_processing.core.project import Project
from oregon_processing.core.device_status import DeviceStatus

class ExportProtocol:

    EXPORT_EVENT_RECORD_FLAG = False

    def __init__(self):
        self._exit_stack = None
        self._project: Project = None
        self._communicator: Communicator = None
        self._database_manager: DatabaseManager = None
        self._logging_manager: LoggingManager = None

    def __enter__(self):
        self._exit_stack = ExitStack()

        try:
            try:
                config = OregonConfig()
            except ConfigNotFoundError:
                OregonConfig.create_default_config()
                config = OregonConfig()

            last_project_dir = config.last_project_dir

            if last_project_dir:
                # prompt user if they want to reuse the last project directory or select a new one

                try:
                    answer = prompt_yes_no(f"Last project directory found: {last_project_dir}\n\nDo you want to reuse this directory for the export?",
                                       window_height=250, window_width=600)
                except (UserCancelledError, NoFileSelectedError):
                    print("\n\nProject directory selection cancelled by user. Aborting export protocol.\n\n")
                    raise UserCancelledError

                if answer != "Yes":
                    last_project_dir = None

            self._project = Project(project_dir=last_project_dir)

            # update config with last used project directory
            config.last_project_dir = self._project.project_dir


            # Set up logging with crash logs directory
            crash_log_file = DatabaseManager.prepare_crash_log_file(self._project)
            self._logging_manager = self._exit_stack.enter_context(
                LoggingManager(
                    write_to_console = True,
                    write_to_report_file = True,
                    report_file = crash_log_file,
                    relative_base_paths = {"output_dir": self._project.project_dir}
                    )
            )

            self._communicator = self._exit_stack.enter_context(Communicator())

            devicestatus: DeviceStatus = self._communicator.get_devicestatus()
            self._database_manager = DatabaseManager(self._project)
            self._database_manager.prepare_directories(devicestatus.serial_number)

            # Update log file to final location
            report_file_dir = self._database_manager.logs_dir
            report_file = report_file_dir / f"export_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            self._logging_manager.transfer_log_file(report_file)
        except (ConfigNotFoundError, InvalidConfigError, ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError) as e:
            self._exit_stack.close()
            raise
        except Exception as e:
            LOGGER.exception("Failed to initialize export protocol:\n\n {}".format(e))

            self._exit_stack.close()
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return False

    def run_export_protocol(self):

        LOGGER.info("Oregon RFID Export Protocol Initiated")

        if not self._communicator.is_connected:
            LOGGER.error("Oregon RFID device is not connected. Aborting.")
            return

        # Execute device health check on device
        health_report: DeviceHealth = self._communicator.check_device_health()
        if len(health_report.critical_warnings) > 0:
            error_message = "Device health check failed. Please address the following critical issues before proceeding: \n  -" + "\n  -".join(health_report.critical_warnings)
            LOGGER.error(error_message)
            raise DeviceHealthError(error_message)

        # Execute device clock sync check on device
        clock_check_result: ClockCheckResult = self._communicator.control_device_datetime(tolerance_seconds=10)
        if not clock_check_result.synchronized:
            error_message = "Device clock is not in sync and could not be automatically updated. Please address the issue before proceeding."
            LOGGER.error(error_message)
            raise DeviceHealthError(error_message)

        # get dates where exports are needed based on what is already in the database
        export_dates: ExportDates = self._database_manager.get_export_dates()


        if self.EXPORT_EVENT_RECORD_FLAG:
            self._communicator.export_event_records(
                dates=export_dates.event_record_dates,
                output_dir=self._database_manager.event_records_dir
            )
        else:
            LOGGER.info("Skipping event record export as currently configured.")

        self._communicator.export_detection_records(
            dates=export_dates.detection_record_dates,
            output_dir=self._database_manager.detection_records_dir
        )
