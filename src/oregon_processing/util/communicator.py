from contextlib import ExitStack

from pathlib import Path

from oregon_processing.util.connector import ConnectionResult, connect
from oregon_processing.util.communication import ConnectionSession
from oregon_processing.util.clock_manager import ClockCheckResult, ClockManager
from oregon_processing.util.device_mode_manager import DeviceModeManager
from oregon_processing.util.interactive_terminal import InteractiveTerminal
from oregon_processing.util.format_manager import FormatManager
from oregon_processing.util.data_exporter import DataExporter
from oregon_processing.util.device_health_checker import DeviceHealthChecker, DeviceHealthReport
from oregon_processing.util.system_status import SystemStatusChecker, SystemStatus
from oregon_processing.util.upload_history import UploadHistoryChecker, UploadHistory
from oregon_processing.exceptions import CommandTransmissionError, ConnectionFailedError, UnexpectedResponseError, UserCancelledError
from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)


class Communicator:
    """Class to communicate with Oregon device via serial port."""

    def __init__(self):

        self._exit_stack = None

        self._session: ConnectionSession = None

        self._mode_manager: DeviceModeManager = None
        self._system_status_checker: SystemStatusChecker = None
        self._clock_manager: ClockManager = None
        self._format_manager: FormatManager = None
        self._data_exporter: DataExporter = None
        self._health_checker: DeviceHealthChecker = None
        self._upload_history_checker: UploadHistoryChecker = None

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

                self._mode_manager = self._exit_stack.enter_context(DeviceModeManager(self._session, self._system_status_checker))
                self._format_manager = self._exit_stack.enter_context(FormatManager(self._session, self._mode_manager))
                self._upload_history_checker = UploadHistoryChecker(self._session, self._mode_manager)
                self._data_exporter = DataExporter(self._session, self._format_manager, self._upload_history_checker, self._mode_manager, self._system_status_checker)
                self._clock_manager = ClockManager(self._session)
                self._health_checker = DeviceHealthChecker(self._session, self._system_status_checker)

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
        return self._session is not None

    def check_device_health(self):
        """
        Check system status and health.

        Delegates to DeviceHealthChecker.check_device_health().
        Returns
        -------
        dict
            Dictionary with 'healthy' (bool) and 'warnings' (list of str) keys.
        """


        if not self._health_checker:
            error_message = "Health checker not initialized. Cannot check device health."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        health_report: DeviceHealthReport = self._health_checker.check_device_health()
        return health_report

    def start_interactive_terminal(self):
        """
        Start an interactive terminal session for sending commands to the device.

        Opens a command-line interface where commands can be entered, validated,
        sent to the device, and responses displayed. Type 'exit' or 'quit' to exit.
        """


        if not self._session.is_connected:
            error_message = "Not connected to device. Cannot start interactive terminal."
            LOGGER.error(error_message)
            raise ConnectionError(error_message)

        terminal = InteractiveTerminal(self._session)
        terminal.run()

        LOGGER.info("Interactive terminal session ended.")
        LOGGER.info("As a safety measure, reconnecting to device to refresh state.")
        self._post_connect_handshake()

    def get_system_status(self) -> SystemStatus:

        if not self._system_status_checker:
            error_message = "System status checker not initialized. Cannot get system status."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        return self._system_status_checker.get_system_status()

    def get_upload_history(self) -> UploadHistory:
        """
        Parse upload history output from UH command.

        Returns
        -------
        UploadHistory
            Parsed upload history with upload records and metadata.
        """

        if not self._session:
            error_message = "Connection session not initialized. Cannot retrieve upload history."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if not self._session.is_connected:
            error_message = "Not connected to device. Cannot retrieve upload history."
            LOGGER.error(error_message)
            raise ConnectionError(error_message)

        if not self._mode_manager:
            error_message = "Mode manager not initialized. Cannot retrieve upload history."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        upload_history: UploadHistory = self._mode_manager.get_upload_history()
        return upload_history

    def control_device_datetime(self, tolerance_seconds: int = 15, attempt_sync: bool = True) -> dict:
        """
        Check if device datetime is synchronized with system time and optionally update it.

        Delegates to ClockManager. When device has elapsed time only (not synchronized),
        displays uptime and returns with error. When device has absolute datetime, compares
        with system time and prompts for sync if needed.

        Parameters
        ----------
        tolerance_seconds : int
            Acceptable difference in seconds before device is considered out of sync. Default: 15
        attempt_sync : bool
            If True and out of sync, prompt user to update device time. Default: True

        Returns
        -------
        clock_check_result : ClockCheckResult
            Result of clock check with fields:
            - synchronized (bool): Whether device time is synchronized within tolerance
            - device_datetime (datetime): Current device time (or None if not available)
            - device_elapsed_time (timedelta): Elapsed time since device boot (or None if not available)
            - computer_datetime (datetime): Current system time
            - time_difference (timedelta): Absolute difference between device and system time
        """
        if not self._connection:
            error_message = f"Not connected to device. Cannot check or control device datetime."
            LOGGER.error(error_message)
            raise ConnectionError(error_message)

        clock_check_result: ClockCheckResult = self._clock_manager.control_device_datetime(tolerance_seconds, attempt_sync)
        return clock_check_result

    def export_event_records(self, dates: list, output_dir: Path = Path("")) -> bool:
        """
        Export event records for specified dates.

        Delegates to DataExporter.export_event_records().

        Parameters
        ----------
        dates : list
            List of date objects to export
        output_dir : str or Path
            Directory where output files will be written (default: current directory)

        Returns
        -------
        bool
            True if all exports completed successfully, False if any failed.
        """
        success: bool = self._data_exporter.export_event_records(dates, output_dir)
        return success

    def export_detection_records(self, dates: list, output_dir: Path = Path(""), sep=',') -> bool:
        """
        Export detection records for specified dates.

        Delegates to DataExporter.export_detection_records().

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
        success: bool = self._data_exporter.export_detection_records(dates, output_dir, sep)
        return success

    def _post_connect_handshake(self):
        """Send a quick SY command to verify connection and capture prompt signature. Store reader name and FM format"""

        if not self._connection:
            return

        LOGGER.debug("Starting post-connection handshake.")

        system_status: SystemStatus = self.get_system_status()
        reader_name = system_status.reader_name
        serial_number = system_status.serial_number
        device_type = system_status.device_type

        LOGGER.info(f"Connected to device '{reader_name}' of type '{device_type}' with serial number '{serial_number}'.")
