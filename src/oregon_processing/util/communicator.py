from contextlib import ExitStack

from pathlib import Path

from oregon_processing.util.connector import ConnectionResult, connect
from oregon_processing.util.communication import ConnectionSession
from oregon_processing.util.clock_manager import ClockCheckResult, control_device_datetime
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.format_manager import FormatManager
from oregon_processing.util.data_exporter import DataExporter
from oregon_processing.util.device_health_checker import DeviceHealthReport, check_device_health as get_device_health_report
from oregon_processing.util.system_status import SystemStatusChecker, SystemStatus
from oregon_processing.exceptions import CommandTransmissionError, ConnectionFailedError, UnexpectedResponseError, UserCancelledError
from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)


class Communicator:
    """Class to communicate with Oregon device via serial port."""

    def __init__(self):

        self._exit_stack = None

        self._session: ConnectionSession = None

        self._system_status_checker: SystemStatusChecker = None
        self._format_manager: FormatManager = None
        self._data_exporter: DataExporter = None

        self._last_upload_date = None
        self._reader_name = None
        self._serial_number = None
        self._device_type = None
        self._mode = None


    def __enter__(self):

        self._exit_stack = ExitStack()

        connection_result = None
        try:
            connection_result: ConnectionResult = connect()

            if connection_result and connection_result.success:

                self._session = self._exit_stack.enter_context(connection_result.session)

                self._system_status_checker = SystemStatusChecker(self._session)
                self._post_connect_handshake()

                self._format_manager = self._exit_stack.enter_context(FormatManager(self._session, self._system_status_checker))
                self._data_exporter = DataExporter(self._session, self._format_manager, self._system_status_checker)

            else:
                error_message = f"Failed to connect to Oregon device."
                LOGGER.error(error_message)
                raise ConnectionFailedError(error_message)

        # catch exceptions where logging is already made and reraise after closing exit stack
        except (ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError) as e:
            if self._exit_stack:
                self._exit_stack.close()
            raise
        except Exception as e:
            LOGGER.exception("Failed to initialize Communicator")
            if self._exit_stack:
                self._exit_stack.close()
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensure all managers and connection are properly cleaned up."""
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)
        if self._session:
            self._session.close()

    @property
    def is_connected(self):
        """Check if there is an active connection."""
        return self._session is not None and self._session.is_connected

    def check_device_health(self):
        health_report: DeviceHealthReport = get_device_health_report(self._session, self._system_status_checker)
        return health_report

    def start_interactive_terminal(self):
        """
        Start an interactive terminal session for sending commands to the device.

        Opens a command-line interface where commands can be entered, validated,
        sent to the device, and responses displayed. Type 'exit' or 'quit' to exit.
        """


        if not self._session:
            error_message = "Not connected to device. Cannot start interactive terminal."
            LOGGER.error(error_message)
            raise ConnectionError(error_message)

        terminal = InteractiveTerminal(self._session)
        terminal.run()

        LOGGER.info("Interactive terminal session ended.")
        LOGGER.info("As a safety measure, reconnecting to device to refresh state.")
        self._post_connect_handshake()

    def get_system_status(self) -> SystemStatus:
        return self._system_status_checker.get_system_status()

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:
        clock_check_result: ClockCheckResult = control_device_datetime(
            session=self._session,
            tolerance_time_diff=tolerance_seconds,
            attempt_sync=attempt_sync,
        )
        return clock_check_result

    def export_event_records(self, dates: list, output_dir: Path = Path("")) -> bool:
        success: bool = self._data_exporter.export_event_records(dates, output_dir)
        return success

    def export_detection_records(self, dates: list, output_dir: Path = Path(""), sep=',') -> bool:
        success: bool = self._data_exporter.export_detection_records(dates, output_dir, sep)
        return success

    def _post_connect_handshake(self):
        LOGGER.debug("Starting post-connection handshake.")
        system_status: SystemStatus = self._system_status_checker.get_system_status()
        LOGGER.info(f"Connected to device '{system_status.reader_name}' of type '{system_status.device_type}' with serial number '{system_status.serial_number}'.")
