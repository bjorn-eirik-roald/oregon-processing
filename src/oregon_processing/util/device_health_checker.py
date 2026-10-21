from __future__ import annotations
from typing import TYPE_CHECKING


from dataclasses import dataclass
from oregon_processing.util.logging_manager import get_logger


LOGGER = get_logger(__name__)

if TYPE_CHECKING:
    from oregon_processing.util.communication import ConnectionSession
    from oregon_processing.util.system_status import FirmwareVersion, SystemStatus, SystemStatusChecker


@dataclass
class DeviceHealth:
    """Data class representing the health report of the Oregon RFID device."""

    healthy: bool
    critical_warnings: list[str]
    warnings: list[str]

RECOMMENDED_VOLTAGE = 14.0
CRITICAL_VOLTAGE_THRESHOLD = 12.5
OLD_VERSION_THRESHOLD = 2.74


def check_device_health(session: ConnectionSession, system_status_checker: SystemStatusChecker) -> DeviceHealth:
    """
    Calls for system status and checks parsed system status for potential issues.

    Returns
    -------
    DeviceHealth
        Data class representing the health report of the Oregon RFID device.
    """

    LOGGER.debug("Initializing health check of Oregon RFID device.")
    LOGGER.debug("Retrieving System Status.")

    critical_warnings = []
    non_critical_warnings = []

    system_status: SystemStatus = system_status_checker.get_system_status()
    prompt_prefix = session.prompt_prefix

    # Check time synchronization status based on prompt signature (3rd character should be 'G' for GNSS sync)
    if prompt_prefix[2] != 'G':
        non_critical_warnings.append(
            f"Device time is not synchronized to GNSS signals (current state: '{prompt_prefix[2]}')"
        )

    # Check firmware version
    firmware_version: FirmwareVersion = system_status.version
    if firmware_version.version_number < OLD_VERSION_THRESHOLD:
        non_critical_warnings.append(
            f"Device firmware version V{firmware_version.major}.{firmware_version.minor}{firmware_version.suffix or ''} is outdated (should be >= {OLD_VERSION_THRESHOLD})"
        )

    # Check supply voltage
    voltage: float = system_status.supply_voltage

    if voltage < RECOMMENDED_VOLTAGE:
        non_critical_warnings.append(
            f"Low supply voltage: {voltage}V (recommended to be >= {RECOMMENDED_VOLTAGE}V)"
        )

    if voltage < CRITICAL_VOLTAGE_THRESHOLD:
        critical_warnings.append(
            f"Critical low supply voltage: {voltage}V (must be >= {CRITICAL_VOLTAGE_THRESHOLD}V)"
        )

    health_report = DeviceHealth(
        healthy=len(critical_warnings) == 0 and len(non_critical_warnings) == 0,
        critical_warnings=critical_warnings,
        warnings=non_critical_warnings
    )

    # Report health status
    if not health_report.healthy:
        total_issues = len(critical_warnings) + len(non_critical_warnings)
        warning_message = f"Device health check detected {total_issues} issue(s)."

        if critical_warnings:
            warning_message += "\n    Critical:"
            for warning in critical_warnings:
                warning_message += f"\n      - {warning}"

        if non_critical_warnings:
            warning_message += "\n    Non-critical:"
            for warning in non_critical_warnings:
                warning_message += f"\n      - {warning}"

        LOGGER.warning(warning_message)

    else:
        LOGGER.info("Device health check passed. All parameters within normal range.")

    return health_report
