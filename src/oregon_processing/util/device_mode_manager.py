# -*- coding: utf-8 -*-
"""
Device Mode Manager for Oregon RFID
"""


from __future__ import annotations
from typing import TYPE_CHECKING

from oregon_processing.exceptions import ModeChangeError
from oregon_processing.util.logging_manager import get_logger

LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from oregon_processing.util.command_manager import CommandManager
    from oregon_processing.util.system_status import SystemStatus, SystemStatusChecker


class DeviceModeManager:
    """Manages device operating modes (Standby, Run, Sleep)."""

    MODES = {
        'standby': {'display': 'Standby', 'command': 'ST'},
        'run': {'display': 'Run', 'command': 'ON'},
        'sleep': {'display': 'Sleep', 'command': 'OF'},
        'Standby': {'display': 'Standby', 'command': 'ST'},
        'Run': {'display': 'Run', 'command': 'ON'},
        'Sleep': {'display': 'Sleep', 'command': 'OF'}
    }
    def __init__(self, command_manager: CommandManager, status_checker: SystemStatusChecker):
        """
        Initialize DeviceModeManager with command manager and status checker.

        Parameters
        ----------
        command_manager : CommandManager
            Command manager instance for sending commands to device.
        status_checker : SystemStatusChecker
            Status checker instance for retrieving system status.
        """

        self._command_manager = command_manager
        self._status_checker = status_checker
        self._startup_mode = None

    def __enter__(self):
        """Enter context manager."""

        try:
            self._startup_mode = self.get_current_mode()
            LOGGER.debug(f"Device startup mode: {self._startup_mode}")
        except Exception as e:
            error_message = "Failed to get current device mode on context enter."
            LOGGER.exception(error_message)
            raise

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager; return to startup mode."""
        self._return_to_startup_mode()

    @property
    def startup_mode(self) -> str:
        """Get the stored startup mode."""
        return self._startup_mode

    @startup_mode.setter
    def startup_mode(self, mode: str):
        """Set the startup mode."""
        self._startup_mode = mode

    def change_mode(self, mode_name: str) -> bool:
        """
        Change the device operating mode.

        Parameters
        ----------
        mode_name : str
            Target mode: "Standby", "Run", or "Sleep"

        Returns
        -------
        bool
            True if mode change successful, False otherwise.
        """


        if mode_name not in self.MODES:
            error_message = f"Invalid mode: {mode_name}. Can only set modes to: Standby, Run, Sleep"
            LOGGER.error(error_message)
            raise ValueError(error_message)

        command = self.MODES[mode_name]['command']

        current_mode = self.get_current_mode()
        if current_mode != mode_name:
            LOGGER.debug(f"Changing device mode from '{current_mode}' to '{mode_name}' (sending {command} command).")
            self._command_manager.send_command(command)
            if self.get_current_mode().lower() == mode_name.lower():
                LOGGER.debug(f"Device mode changed from '{current_mode}' to '{mode_name}'.")
            else:
                error_message = f"Device mode change failed! Expected mode: '{mode_name}', Actual mode: '{self.get_current_mode()}'"
                LOGGER.error(error_message)
                raise ModeChangeError(error_message)

        return True

    @classmethod
    def is_valid_mode(cls, mode_name: str) -> bool:
        """Check if the provided mode name is valid."""
        return mode_name.lower() in cls.MODES

    def _return_to_startup_mode(self) -> None:
        """Return the Oregon RFID device to its start-up mode."""

        if not self._startup_mode:
            LOGGER.warning("Startup mode not set. Cannot return to startup mode.")
            return

        target_mode = self._startup_mode.lower()

        if target_mode is None:
            LOGGER.warning(f"WARNING: Start-up mode is None. Can not return to startup mode. Setting reader to Sleep mode to be safe.")
            target_mode = 'Sleep'

        self.change_mode(target_mode)

    def get_current_mode(self) -> str:
        """
        Get the current operating mode from the system status.

        Returns
        -------
        str
            Current mode: "Standby", "Run", or "Sleep"
        """
        status: SystemStatus = self._status_checker.get_system_status()
        return status.mode


