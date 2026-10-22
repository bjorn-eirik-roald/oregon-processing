from contextlib import ExitStack

from pathlib import Path

from oregon_processing.core.connection import ConnectionResult, connect
from oregon_processing.core.communication import ConnectionSession
from oregon_processing.core.device_clock import ClockCheckResult, control_device_datetime
from oregon_processing.core.device_mode import DeviceMode, get_current_mode
from oregon_processing.core.interactive_terminal import InteractiveTerminal
from oregon_processing.core.device_health import DeviceHealth, check_device_health as get_device_health_report
from oregon_processing.core.device_status import DeviceStatusChecker, DeviceStatus
from oregon_processing.core.data_export import export_detection_records
from oregon_processing.exceptions import CommandTransmissionError, ConnectionFailedError, UnexpectedResponseError, UserCancelledError
from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)


class Communicator:
    """Class to communicate with Oregon device via serial port."""

    def __init__(self):

        self._exit_stack = None
        self._session: ConnectionSession = None
        self._device_status_checker: DeviceStatusChecker = None

    def __enter__(self):

        self._exit_stack = ExitStack()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Ensure all managers and connection are properly cleaned up."""
        if self._exit_stack:
            return self._exit_stack.__exit__(exc_type, exc_value, traceback)

    @property
    def is_connected(self):
        """Check if there is an active connection."""
        return self._session is not None and self._session.is_connected

    def connect(self) -> None:
        try:
            connection_result: ConnectionResult = connect()

            if connection_result.success:

                self._session: ConnectionSession = self._exit_stack.enter_context(connection_result.session)
                self._device_status_checker = DeviceStatusChecker(self._session)
                self._post_connect_handshake()

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

    def start_interactive_terminal(self) -> None:
        terminal = InteractiveTerminal(self._session)
        terminal.run()

        LOGGER.info("Interactive terminal session ended.")

    def get_device_status(self) -> DeviceStatus:
        return self._device_status_checker.get_device_status()

    def get_device_mode(self) -> DeviceMode:
        return get_current_mode(self._session, self._device_status_checker)

    def check_device_health(self) -> DeviceHealth:
        device_health: DeviceHealth = get_device_health_report(self._session, self._device_status_checker)
        return device_health

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> ClockCheckResult:
        clock_check_result: ClockCheckResult = control_device_datetime(
            session=self._session,
            tolerance_time_diff=tolerance_seconds,
            attempt_sync=attempt_sync,
        )
        return clock_check_result

    def export_detection_records(self, dates: list[str], output_dir: Path) -> None:
        export_detection_records(dates, output_dir, self._session, self._device_status_checker)

    def _post_connect_handshake(self):
        LOGGER.debug("Starting post-connection handshake.")
        device_status: DeviceStatus = self._device_status_checker.get_device_status()
        LOGGER.info(f"Connected to device '{device_status.reader_name}' of type '{device_status.device_type}' with serial number '{device_status.serial_number}'.")
