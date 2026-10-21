from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.exceptions import ClockSyncError, CommandTransmissionError, UnexpectedResponseError
from oregon_processing.core.communication import DeviceCommand

if TYPE_CHECKING:
    from oregon_processing.core.communication import ConnectionSession


TIME_STATUSES = {
    'G': "GNSS Time",
    'N': "Network time using CAT5 cable",
    'U': "Uncalibrated (entered with DT command)",
    'E': "Elapsed time since power-up",
    'g': "GNSS Time",
    'n': "Network time using CAT5 cable",
    'u': "Uncalibrated (entered with DT command)",
    'e': "Elapsed time since power-up",
}


@dataclass
class ClockStatus:
    """Clock status payload parsed from DT/TZ responses."""

    datetime: datetime | None = None
    elapsed_time: timedelta | None = None
    sync_status: str | None = None
    timezone: timezone | None = None


@dataclass
class ClockCheckResult:
    """Result of checking device clock synchronization against local computer time."""

    synchronized: bool
    device_datetime: datetime | None
    device_elapsed_time: timedelta | None
    device_sync_status: str | None
    device_timezone: timezone | None
    computer_datetime: datetime
    time_difference: float | None


def control_device_datetime(
    session: ConnectionSession,
    tolerance_time_diff: int = 15,
    attempt_sync: bool = True,
) -> ClockCheckResult:
    """
    Check if device datetime is synchronized with computer time and optionally update it.

    If device time is out of sync or uses elapsed time, prompts user to update device time
    to match computer time. If user agrees, updates device time and re-checks status.
    """
    clock_check_result: ClockCheckResult = _check_if_synched(
        session=session,
        tolerance_time_diff=tolerance_time_diff,
    )

    _print_clock_status(clock_check_result)

    if not clock_check_result.synchronized and attempt_sync:
        clock_check_result = _attempt_clock_sync(
            session=session,
            current_result=clock_check_result,
            tolerance_time_diff=tolerance_time_diff,
        )

    return clock_check_result


def _attempt_clock_sync(
    session: ConnectionSession,
    current_result: ClockCheckResult,
    tolerance_time_diff: int,
) -> ClockCheckResult:
    """Prompt and optionally synchronize device clock, returning updated check result."""
    confirm = None
    while confirm not in ['y', 'yes', 'n', 'no']:
        confirm = input("\nUpdate device time to match computer time? (yes/no): ").strip().lower()
        print()

    if confirm in ['n', 'no']:
        LOGGER.debug("User selected not to sync device time.")
        return current_result

    LOGGER.debug("User selected to synch computer/device times.")
    try:
        LOGGER.debug("Setting device timezone to UTC.")
        session.send_command(DeviceCommand.TZ0)
        LOGGER.info("Device timezone set to UTC.")

        LOGGER.debug(f"Setting device time to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        computer_datetime_utc = datetime.now().astimezone(timezone.utc)
        dt_argument = computer_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
        response_lines = session.send_command(DeviceCommand.DT, dt_argument)

        if len(response_lines) == 0:
            error_message = "No response received after sending DT command."
            LOGGER.error(error_message)
            raise CommandTransmissionError(error_message)

        LOGGER.info(f"Device time was updated to {computer_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC.")

        # check if the device time is now synchronized with the computer time
        updated_result: ClockCheckResult = _check_if_synched(
            session=session,
            tolerance_time_diff=tolerance_time_diff,
        )
        _print_clock_status(updated_result)
        return updated_result
    except Exception as e:
        error_message = f"Failed to synchronize device time: {e}"
        LOGGER.error(error_message)
        raise ClockSyncError(error_message)


def _check_if_synched(
    session: ConnectionSession,
    tolerance_time_diff: int,
) -> ClockCheckResult:
    """Compare device and local clock and return synchronization result."""
    device_clock_status = _get_device_datetime(session)
    computer_datetime = datetime.now()

    sync_status = device_clock_status.sync_status

    if sync_status == 'E':
        time_diff = None
        is_synchronized = False
    else:
        device_datetime_utc = device_clock_status.datetime.astimezone(timezone.utc)
        computer_datetime_utc = computer_datetime.astimezone(timezone.utc)
        time_diff = abs(device_datetime_utc - computer_datetime_utc).total_seconds()
        is_synchronized = time_diff <= tolerance_time_diff

    return ClockCheckResult(
        synchronized=is_synchronized,
        device_datetime=device_clock_status.datetime,
        device_elapsed_time=device_clock_status.elapsed_time,
        device_sync_status=device_clock_status.sync_status,
        device_timezone=device_clock_status.timezone,
        computer_datetime=computer_datetime,
        time_difference=time_diff,
    )


def _get_device_datetime(session: ConnectionSession) -> ClockStatus:
    """Retrieve device datetime/timezone using DT and TZ commands."""
    clock_status = ClockStatus()

    dt_line = _send_dt_command(session)
    _parse_dt_response(dt_line, clock_status)

    tz_line = _send_tz_command(session)
    _parse_tz_response(tz_line, clock_status)

    return clock_status


def _print_clock_status(clock_check_result: ClockCheckResult) -> None:
    """Log a human-readable summary of device/computer clock status."""
    sync_status_name = TIME_STATUSES[clock_check_result.device_sync_status]

    device_tz = clock_check_result.device_timezone
    device_dt = clock_check_result.device_datetime
    device_elapsed_time = clock_check_result.device_elapsed_time
    computer_dt = clock_check_result.computer_datetime
    time_diff = clock_check_result.time_difference

    device_tz_str = f"(UT{device_tz.utcoffset(None).total_seconds() / 3600:+.1f})" if device_tz else "(unknown)"
    computer_offset_hours = computer_dt.astimezone().utcoffset().total_seconds() / 3600
    computer_tz_str = f"(UT{computer_offset_hours:+.1f})"

    status_message = (
        f"Device Clock Status:\n    "
        f"{'✓ IN SYNC' if clock_check_result.synchronized else '⚠ OUT OF SYNC'}\n"
        f"    Device Clock Source: {sync_status_name}\n"
    )

    if device_dt:
        status_message += f"    Device Time: {device_dt.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str}\n"
    else:
        total_seconds = int(device_elapsed_time.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = device_elapsed_time.microseconds // 1000
        status_message += (
            f"    Device Time: elapsed-only (no absolute time): "
            f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}\n"
        )

    status_message += f"    Computer Time: {computer_dt.strftime('%Y-%m-%d %H:%M:%S')} {computer_tz_str}"

    if time_diff is not None and not clock_check_result.synchronized:
        status_message += (
            f"\n    Computer/Device Time Difference: {time_diff:+.1f}s "
            f"({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})"
        )

    LOGGER.info(status_message)


def _send_dt_command(session: ConnectionSession) -> str:
    try:
        lines = session.send_command(DeviceCommand.DT)
    except Exception as e:
        error_message = f"Failed to send DT command: {e}"
        LOGGER.error(error_message)
        raise CommandTransmissionError(error_message)

    if len(lines) != 1:
        error_message = f"Unexpected number of lines in DT response: {len(lines)}. Response: {lines}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    return lines[0].strip()


def _parse_dt_response(dt_line: str, clock_status: ClockStatus) -> None:
    """Parse DT response into elapsed or absolute clock status fields."""
    parts = dt_line.split()

    if len(parts) < 2:
        error_message = f"Unrecognized DT response format: {dt_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    if parts[-1] == 'E':
        _parse_elapsed_time_dt_response(dt_line, clock_status)
        return

    if parts[-2] in 'GNU':
        _parse_absolute_dt_response(dt_line, clock_status)
        return

    error_message = f"Unrecognized DT response format: {dt_line}"
    LOGGER.error(error_message)
    raise UnexpectedResponseError(error_message)


def _parse_elapsed_time_dt_response(dt_line: str, clock_status: ClockStatus) -> None:
    """Parse elapsed-time DT response: HH:MM:SS(.mmm) E."""
    parts = dt_line.split()
    if len(parts) != 2:
        error_message = f"Unrecognized DT response format: {dt_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    sync_status = parts[-1]
    time_str = parts[0]
    if '.' in time_str:
        time_part, milliseconds_str = time_str.split('.')
        milliseconds = int(milliseconds_str)
    else:
        time_part = time_str
        milliseconds = 0

    try:
        hours, minutes, seconds = [int(part) for part in time_part.split(':')]
    except ValueError:
        error_message = f"Failed to parse hours, minutes, and seconds from DT response: {dt_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    clock_status.elapsed_time = timedelta(
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds,
    )
    clock_status.sync_status = sync_status


def _parse_absolute_dt_response(dt_line: str, clock_status: ClockStatus) -> None:
    """Parse absolute DT response: YYYY-MM-DD HH:MM:SS(.mmm) [G|N|U] ..."""
    parts = dt_line.split()
    if len(parts) < 4:
        error_message = f"Unrecognized DT response format: {dt_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    date_str = parts[0]
    time_str = parts[1]
    sync_status = parts[2]

    if sync_status not in TIME_STATUSES:
        error_message = f"Unrecognized sync status '{sync_status}' in DT response: {dt_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    if '.' in time_str:
        time_part, milliseconds_str = time_str.split('.')
        milliseconds = int(milliseconds_str)
    else:
        time_part = time_str
        milliseconds = 0

    dt_temp = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S")
    dt = datetime(
        dt_temp.year,
        dt_temp.month,
        dt_temp.day,
        dt_temp.hour,
        dt_temp.minute,
        dt_temp.second,
        microsecond=milliseconds * 1000,
    )

    clock_status.datetime = dt
    clock_status.sync_status = sync_status


def _send_tz_command(session: ConnectionSession) -> str:
    try:
        lines = session.send_command(DeviceCommand.TZ)
    except Exception as e:
        error_message = f"Failed to send TZ command: {e}"
        LOGGER.error(error_message)
        raise CommandTransmissionError(error_message)

    if len(lines) != 2:
        error_message = f"Unexpected number of lines in TZ response: {len(lines)}. Response: {lines}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    return lines[0].strip()


def _parse_tz_response(tz_line: str, clock_status: ClockStatus) -> None:
    """Parse TZ response into timezone and apply it to absolute datetime when present."""
    hours = 0
    minutes = 0
    sign = 1

    if tz_line.startswith("Hours:minutes to UT:"):
        offset_part = tz_line.split("Hours:minutes to UT:")[1].strip()
        if offset_part.startswith('-'):
            sign = -1
            offset_part = offset_part[1:]
        elif offset_part.startswith('+'):
            sign = 1
            offset_part = offset_part[1:]
        else:
            error_message = f"Unrecognized timezone format. No sign found: {tz_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        try:
            hours = int(offset_part.split('h')[0].strip())
            minutes = int(offset_part.split('h')[1].strip().split('m')[0].strip())
        except (IndexError, ValueError):
            error_message = f"Failed to parse hours and minutes from TZ response: {tz_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    elif tz_line.startswith("Hours to UT:"):
        offset_part = tz_line.split("Hours to UT:")[1].strip()
        if offset_part.startswith('-'):
            sign = -1
            offset_part = offset_part[1:]
        elif offset_part.startswith('+'):
            sign = 1
            offset_part = offset_part[1:]
        else:
            error_message = f"Unrecognized timezone format. No sign found: {tz_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        try:
            hours = int(offset_part)
        except ValueError:
            error_message = f"Failed to parse hours from TZ response: {tz_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)
    else:
        error_message = f"Unrecognized timezone format: {tz_line}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    total_seconds = sign * (hours * 3600 + minutes * 60)
    tz = timezone(timedelta(seconds=total_seconds))
    clock_status.timezone = tz
    clock_status.datetime = clock_status.datetime.replace(tzinfo=tz) if clock_status.datetime else None
