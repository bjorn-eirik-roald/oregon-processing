from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum

from oregon_processing.exceptions import ModeChangeError
from oregon_processing.util.logging_manager import get_logger
from oregon_processing.core.communication import DeviceCommand

LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from oregon_processing.core.communication import ConnectionSession
    from oregon_processing.core.device_status import DeviceStatusChecker


class DeviceMode(str, Enum):
    """Device operating mode with display name and command."""

    STANDBY = ("Standby", DeviceCommand.ST)
    RUN = ("Run", DeviceCommand.ON)
    SLEEP = ("Sleep", DeviceCommand.OF)

    def __new__(cls, display_name: str, command: DeviceCommand):
        obj = str.__new__(cls, display_name)
        obj._value_ = display_name
        obj.command = command
        return obj

    @classmethod
    def from_value(cls, mode: str | "DeviceMode") -> "DeviceMode":
        if isinstance(mode, cls):
            return mode
        if not isinstance(mode, str):
            raise ValueError(f"Invalid mode type '{type(mode)}'.")

        normalized = mode.strip().lower()
        for member in cls:
            if member.value.lower() == normalized:
                return member

        raise ValueError(f"Invalid mode: {mode}. Can only set modes to: Standby, Run, Sleep")

def is_valid_mode(mode_name: str) -> bool:
    """Check if the provided mode name is valid."""
    try:
        DeviceMode.from_value(mode_name)
    except ValueError:
        return False
    return True


def get_current_mode(status_checker: DeviceStatusChecker) -> str:
    """Get current operating mode from SY status parsing."""
    status = status_checker.get_device_status()
    return status.mode


def change_mode(
    session: ConnectionSession,
    status_checker: DeviceStatusChecker,
    mode_name: str | DeviceMode,
) -> bool:
    """Change device operating mode and verify transition."""
    target_mode = DeviceMode.from_value(mode_name)
    current_mode = DeviceMode.from_value(get_current_mode(status_checker))

    LOGGER.debug(f"Initiating mode change from '{current_mode}' to '{target_mode}'.")
    if current_mode == target_mode:
        LOGGER.debug(f"Device is already in the target mode '{target_mode}'. No change needed.")
        return True

    LOGGER.debug(f"Sending command '{target_mode.command}' to change device mode.")
    session.send_command(target_mode.command)

    actual_mode = DeviceMode.from_value(get_current_mode(status_checker))
    if actual_mode == target_mode:
        LOGGER.debug(f"Device mode changed from '{current_mode}' to '{target_mode}'.")
        return True

    error_message = f"Device mode change failed! Expected mode: '{target_mode}', Actual mode: '{actual_mode}'"
    LOGGER.error(error_message)
    raise ModeChangeError(error_message)

