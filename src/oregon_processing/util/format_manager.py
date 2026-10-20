# -*- coding: utf-8 -*-
"""
Format Manager for Oregon RFID device record format operations
"""

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.command_manager import CommandManager
from oregon_processing.util.device_mode_manager import DeviceModeManager
from oregon_processing.exceptions import UnexpectedResponseError


class FormatManager:
    """Manages device detection record format configuration and state."""

    FIELD_NAMES = {
        'DTY': 'Detection type',
        'TCH': 'Tag technology',
        'TTY': 'Tag type',
        'PFG': 'Phantom flag',
        'TAG': 'Tag ID number',
        'ANT': 'Antenna number',
        'ARR': 'Arrival date and time',
        'TRF': 'Time reference',
        'DEP': 'Departure date and time',
        'NCD': 'Number of consecutive detections',
        'EMP': 'Number of empty scans preceding detection',
        'LAT': 'Latitude',
        'LON': 'Longitude',
        'ALT': 'Altitude in meters',
        'SIV': 'Satellites in view',
        'HDP': 'Location horizontal accuracy',
        'TSS': 'Tag signal strength',
        'SPV': 'Power supply voltage',
        'CPA': 'Power supply amperage during charge pulse',
        'LSA': 'Power supply amperage with charge pulse off',
        'EFA': 'Effective amps',
        'CPT': 'Charge pulse time in milliseconds',
        'LST': 'Listen time in milliseconds',
        'ANV': 'Antenna voltage',
        'ANA': 'Antenna amperage',
        'NOI': 'Noise',
        'DUR': 'Duration of tag detection event',
        'CLS': 'Tag size class',
        'SCD': 'Site code',
        'SPC': 'Output one space character',
        }

    def __init__(self, command_manager: CommandManager, mode_manager: DeviceModeManager):
        """
        Initialize FormatManager.

        Parameters
        ----------
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        mode_manager : DeviceModeManager
            DeviceModeManager instance for managing device modes.
        """

        self._command_manager = command_manager
        self._mode_manager = mode_manager

        self._detection_record_format = None
        self._startup_format = None

        # Store startup format when initialized
        self._startup_format = self._fetch_detection_record_format()

    def __enter__(self):
        """Enter context manager."""

        try:
            self._startup_format = self._fetch_detection_record_format()
        except Exception as e:
            error_message = "Failed to fetch detection record format on context enter."
            LOGGER.exception(error_message)
            raise

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; restore startup format."""
        self._restore_startup_format()

    def get_format_info(self) -> dict:
        """
        Get the current detection record format information.

        Returns
        -------
        dict
            Format information with 'columns_raw', 'columns', and 'column_indices'
        """
        return self._fetch_detection_record_format()

    def set_detection_record_format(self, format_string: str) -> bool:
        """
        Set the detection record format on the device using the FM command.

        Parameters
        ----------
        format_string : str
            The format string to set (e.g., "DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA")

        Returns
        -------
        bool
            True if format was set successfully, False otherwise.
        """

        try:
            fm_command = f"FM {format_string}"
            self._command_manager.send_command(fm_command)

            # Verify the format was set and update cache
            self._detection_record_format = self._fetch_detection_record_format()

            if self._detection_record_format['columns_raw'] == format_string:
                return True
            else:
                LOGGER.warning(f"WARNING: Format mismatch. Expected '{format_string}', got '{self._detection_record_format['columns_raw']}'")
                return False

        except Exception:
            LOGGER.exception(f"Error setting detection record format.")
            return False

    def _fetch_detection_record_format(self) -> dict:
        """
        Fetch and parse the detection record format from the device using the FM command.

        Returns
        -------
        dict
            {
              'columns_raw': raw string from FM command response,
              'columns': list of data columns excluding 'SPC',
              'column_indices': dict mapping column names to their indices
            }
        """

        old_mode = None
        mode = self._mode_manager.get_current_mode()
        if mode.lower() != 'standby':
            old_mode = mode
            self._mode_manager.change_mode('Standby')

        response_lines = self._command_manager.send_command("FM")

        if old_mode:
            self._mode_manager.change_mode(old_mode)

        if len(response_lines) != 1:
            error_message = f"Unexpected number of lines in FM response: {len(response_lines)}. Response: {response_lines}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        columns_raw = response_lines[0].strip()
        tokens = columns_raw.split()
        columns = [t for t in tokens if t != 'SPC']

        # Create a dictionary mapping column names to their indices
        column_indices = {col: idx for idx, col in enumerate(columns)}

        # Create a subset of FIELD_NAMES for only the columns in the format

        if any(col not in self.FIELD_NAMES for col in columns):
            unknown_cols = [col for col in columns if col not in self.FIELD_NAMES]
            LOGGER.warning(f"WARNING: Unknown columns in detection record format: {unknown_cols}")

        field_names = {col: self.FIELD_NAMES.get(col, "Unknown") for col in columns}

        return {
            'columns_raw': columns_raw,
            'columns': columns,
            'column_indices': column_indices,
            'field_names': field_names,
        }

    def _restore_startup_format(self) -> bool:
        """
        Restore the device to its startup detection record format.

        Returns
        -------
        bool
            True if format was restored or no change was needed, False if restoration failed.
        """

        if self._startup_format is None:
            # No startup format stored, nothing to restore
            LOGGER.warning("No startup format stored. Cannot restore format.")
            return True

        current_format = self._fetch_detection_record_format()

        # Compare formats - if they're the same, no need to restore
        if current_format['columns_raw'] == self._startup_format['columns_raw']:
            return True


        success = self.set_detection_record_format(self._startup_format['columns_raw'])
        if not success:
            LOGGER.warning("WARNING: Failed to restore original detection record format.")
        else:
            LOGGER.info("Original detection record format restored.")

        return success

