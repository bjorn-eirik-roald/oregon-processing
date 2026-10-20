from __future__ import annotations
from typing import TYPE_CHECKING

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.exceptions import ClockSyncError, CommandTransmissionError, UnexpectedResponseError
from oregon_processing.util.communication import DeviceCommand

if TYPE_CHECKING:
    from oregon_processing.util.communication import ConnectionSession


@dataclass
class ClockStatus:
    """"
    Represents the clock status of the device, including datetime, elapsed time, synchronization status, and timezone.
     - datetime: The current date and time on the device (if available).
    - elapsed_time: The elapsed time since power-up (if absolute datetime is not available).
    - sync_status: The synchronization status of the device clock (e.g., 'G', 'N', 'U', 'E').
    - timezone: The timezone of the device clock (if available).
    """
    datetime: datetime | None = None
    elapsed_time: timedelta | None = None
    sync_status: str | None = None
    timezone: timezone | None = None

@dataclass
class ClockCheckResult:
    """
    Represents the result of checking the device clock synchronization status, including whether it is synchronized
    with the computer time, the device datetime or elapsed time, the computer datetime, and the time difference if applicable.
        - synchronized: Whether the device clock is synchronized with the computer time.
        - device_datetime: The current date and time on the device (if available).
        - device_elapsed_time: The elapsed time since power-up (if absolute datetime is not available).
        - computer_datetime: The current date and time on the computer.
        - time_difference: The difference in seconds between the device and computer time (if absolute datetime is available).
    """
    synchronized: bool
    device_datetime: datetime | None
    device_elapsed_time: timedelta | None
    computer_datetime: datetime
    time_difference: float | None

class ClockManager:
    """Manages device clock synchronization and datetime operations."""

    TIME_STATUSES = {
        'G': "GNSS Time",
        'N': "Network time using CAT5 cable",
        'U': "Uncalibrated (entered with DT command)",
        'E': "Elapsed time since power-up",
        'g': "GNSS Time",
        'n': "Network time using CAT5 cable",
        'u': "Uncalibrated (entered with DT command)",
        'e': "Elapsed time since power-up"
    }

    def __init__(self, session: ConnectionSession):
        """
        Initialize ClockManager.

        Parameters
        ----------
        session : ConnectionSession
            Connection session instance for sending commands to device.
        """

        self._session = session

    def control_device_datetime(self, tolerance_time_diff: int = 15, attempt_sync: bool = True) -> ClockCheckResult:
        """
        Check if device datetime is synchronized with computer time and optionally update it.

        If device time is out of sync or uses elapsed time, prompts user to update device time to match computer time.
        If user agrees, updates device time and re-checks synchronization status.
        Parameters
        ----------
        tolerance_time_diff : int
            Acceptable difference in seconds before device is considered out of sync. Default: 15
        attempt_sync : bool
            If True and out of sync, prompt user to update device time. Default: True

        Returns
        -------
        ClockCheckResult: Object containing result from clock check
        """

        is_synchronized, time_diff, device_clock_status, computer_datetime = self._check_if_synched(tolerance_time_diff=tolerance_time_diff)

        clock_check_result = ClockCheckResult(
            synchronized=is_synchronized,
            device_datetime=device_clock_status.datetime,
            device_elapsed_time=device_clock_status.elapsed_time,
            computer_datetime=computer_datetime,
            time_difference=time_diff,
            )

        self._print_clock_status(is_synchronized, device_clock_status, computer_datetime, time_diff)


        # Attempt sync if out of sync and requested
        if not is_synchronized and attempt_sync:

            # prompt user to confirm if they want to update device time to match computer time
            confirm = None
            while confirm not in ['y', 'yes', 'n', 'no']:
                confirm = input("\nUpdate device time to match computer time? (yes/no): ").strip().lower()
                print() # Add spacing after input for cleaner output

            # log if user selected not to sync
            if confirm in ['n', 'no']:
                LOGGER.debug("User selected not to sync device time.")

            # log if user selected to sync and attempt synchronization
            elif confirm in ['y', 'yes']:
                LOGGER.debug("User selected to synch computer/device times.")

                # attempt to synchronize device time and re-check synchronization status
                try:
                    self._sync_device_time()
                    is_synchronized, time_diff, device_clock_status, computer_datetime = self._check_if_synched(tolerance_time_diff=tolerance_time_diff)
                    self._print_clock_status(is_synchronized, device_clock_status, computer_datetime, time_diff)
                    clock_check_result.synchronized = is_synchronized
                    clock_check_result.device_datetime = device_clock_status.datetime
                    clock_check_result.device_elapsed_time = device_clock_status.elapsed_time
                    clock_check_result.computer_datetime = computer_datetime


                except Exception as e:
                    error_message = f"Failed to synchronize device time: {e}"
                    LOGGER.error(error_message)
                    raise ClockSyncError(error_message)

        # return either the original clock check result (if no sync attempted) or the updated clock check result (if sync attempted)
        return clock_check_result

    def _get_device_datetime(self) -> ClockStatus:
        """
        Retrieve the device's current date, time and timezone using the DT and TZ commands, as well as helper methods.

        Returns
        -------
        ClockStatus: Object containing device datetime, elapsed time, sync status, and timezone information.
        """

        # Initialize ClockStatus object to store results. Uses default values of None
        clock_status: ClockStatus = ClockStatus()

        # Send DT command and get response
        dt_line: str = self._send_dt_command()
        # Parse DT response to populate datetime, elapsed time, and sync status in ClockStatus object
        self._parse_dt_response(dt_line, clock_status)

        # Send TZ command and get response
        tz_line: str = self._send_tz_command()
        # Parse TZ response to populate timezone in ClockStatus object and update datetime with timezone if absolute datetime is available
        self._parse_tz_response(tz_line, clock_status)

        # return populated ClockStatus object with device datetime, elapsed time, sync status, and timezone information
        return clock_status

    def _check_if_synched(self, tolerance_time_diff: int) -> tuple[bool, float | None, ClockStatus, datetime]:
        """
        # Get device datetime and timezone, then compare device and computer datetimes and return whether they are in sync.

        Parameters
        ----------
        tolerance_time_diff : int
            Acceptable difference in seconds before device is considered out of sync.
        Returns
        -------
        is_synchronized : bool
            Whether device time is in sync with computer time.
        time_diff : float or None
            Time difference in seconds (None if elapsed time only).
        device_clock_status : ClockStatus
        computer_datetime : timezone-aware datetime of computer at time of check
        """

        # get device datetime, elapsed time, sync status, and timezone information encapsulated in ClockStatus object
        device_clock_status: ClockStatus = self._get_device_datetime()

        # get current computer datetime as timezone-aware datetime
        computer_datetime = datetime.now()

        # Determine synchronization status
        sync_status = device_clock_status.sync_status

        if sync_status == 'E':
            # No absolute datetime available
            time_diff = None
            is_synchronized = False
        else:
            device_datetime = device_clock_status.datetime
            device_datetime_utc = device_datetime.astimezone(timezone.utc)
            computer_datetime_utc = computer_datetime.astimezone(timezone.utc)
            time_diff = abs(device_datetime_utc - computer_datetime_utc).total_seconds()
            is_synchronized = time_diff <= tolerance_time_diff

        return is_synchronized, time_diff, device_clock_status, computer_datetime

    def _print_clock_status(self, is_synchronized: bool, device_clock_status: ClockStatus, computer_dt, time_diff) -> None:
        """
        Print clock status information.

        Parameters
        ----------
        is_synchronized : bool
            Whether device time is in sync with computer time.
        device_clock_status : ClockStatus
            Device clock status information.
        computer_dt : datetime
            Current computer timezone-aware datetime.
        time_diff : float or None
            Time difference in seconds between device and computer time (None if elapsed time only).
        """

        # Get human-readable sync status name from code
        sync_status_name = self.TIME_STATUSES[device_clock_status.sync_status]

        # Get device timezone, datetime, and elapsed time from ClockStatus object for printing
        device_tz = device_clock_status.timezone
        device_dt = device_clock_status.datetime
        device_elapsed_time = device_clock_status.elapsed_time

        # Format timezone offsets for printing
        device_tz_str = f"(UT{device_tz.utcoffset(None).total_seconds() / 3600:+.1f})" if device_tz else "(unknown)"
        computer_offset_hours = computer_dt.astimezone().utcoffset().total_seconds() / 3600
        computer_tz_str = f"(UT{computer_offset_hours:+.1f})"

        # Start building status message with synchronization status and device clock source
        status_message = f"Device Clock Status:\n    {'✓ IN SYNC' if is_synchronized else '⚠ OUT OF SYNC'}\n    Device Clock Source: {sync_status_name}\n"

        # If device datetime is available, print it with timezone. Otherwise, print elapsed time since power-up if available, or indicate that no time information is available.
        if device_dt:
            status_message += f"    Device Time: {device_dt.strftime('%Y-%m-%d %H:%M:%S')} {device_tz_str}\n"
        else:
            # Format timedelta as HH:MM:SS.mmm
            total_seconds = int(device_elapsed_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = device_elapsed_time.microseconds // 1000
            status_message += f"    Device Time: elapsed-only (no absolute time): {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}\n"

        # Print computer time with timezone information
        status_message += f"    Computer Time: {computer_dt.strftime('%Y-%m-%d %H:%M:%S')} {computer_tz_str}"

        # If time difference is available (i.e., absolute datetime is available) and device is out of sync,
        # print the time difference in seconds and whether the device is ahead or behind the computer time.
        if time_diff is not None and not is_synchronized:
            status_message += f"\n    Computer/Device Time Difference: {time_diff:+.1f}s ({abs(time_diff):.1f}s {'ahead' if time_diff > 0 else 'behind'})"

        LOGGER.info(status_message)

    def _sync_device_time(self) -> bool:
        """
        Synchronize device time with computer time.

        Parameters
        ----------
        computer_datetime : datetime
            Computer datetime (assumed to be timezone-aware).
        """


        LOGGER.debug("Setting device timezone to UTC.")
        self._session.send_command(DeviceCommand.TZ0)
        LOGGER.info(f"Device timezone set to UTC.")

        LOGGER.debug(f"Setting device time to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC.")
        computer_datetime_utc = datetime.now().astimezone(timezone.utc)
        dt_argument = computer_datetime_utc.strftime("%Y-%m-%d %H:%M:%S")
        response_lines = self._session.send_command(DeviceCommand.DT, dt_argument)

        if len(response_lines) == 0:
            error_message = "No response received after sending DT command."
            LOGGER.error(error_message)
            raise CommandTransmissionError(error_message)

        LOGGER.info(f"Device time was updated to {computer_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC.")

        return True

    def _send_dt_command(self) -> str:
        try:
            lines = self._session.send_command(DeviceCommand.DT)
        except Exception as e:
            error_message = f"Failed to send DT command: {e}"
            LOGGER.error(error_message)
            raise CommandTransmissionError(error_message)

        if len(lines) != 1:
            error_message = f"Unexpected number of lines in DT response: {len(lines)}. Response: {lines}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        dt_line = lines[0].strip()

        return dt_line

    def _parse_dt_response(self, dt_line: str, clock_status: ClockStatus) -> None:
        """
        Parse the DT command response line into its components.

        When sync_status is 'E' (elapsed time since power-up), the response contains only
        time (HH:MM:SS.milliseconds) instead of a full date.

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        None
        """


        parts = dt_line.split()

        if len(parts) < 2:
            error_message = f"Unrecognized DT response format: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        dt_line_format = None
        if parts[-1] == 'E': # Elapsed time --> last part is 'E' and time is in HH:MM:SS.milliseconds format without date
            dt_line_format = "elapsed"
        elif parts[-2] in 'GNU': # Absolute datetime --> last part is timezone but part before last is sync status (G, N, or U) and date is in YYYY-MM-DD format
            dt_line_format = "absolute"
        else:
            error_message = f"Unrecognized DT response format: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        if dt_line_format == "elapsed":
            self._parse_elapsed_time_dt_response(dt_line, clock_status)
        elif dt_line_format == "absolute":
            self._parse_absolute_dt_response(dt_line, clock_status)


    def _parse_elapsed_time_dt_response(self, dt_line: str, clock_status: ClockStatus) -> None:
        """
        Parse a DT response line that contains elapsed time since power-up.

        Expected format: "HH:MM:SS.milliseconds E"

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        None
        """


        parts = dt_line.split()

        if len(parts) != 2:
            error_message = f"Unrecognized DT response format: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        sync_status: str = parts[-1] # E for elapsed time
        time_str = parts[0]  # HH:MM:SS.milliseconds or HH:MM:SS if no milliseconds

        # Parse time and milliseconds
        milliseconds_used = '.' in time_str

        if milliseconds_used:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds: int = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds: int = 0

        # Parse time components
        try:
            hours, minutes, seconds = [int(part) for part in time_part.split(':')]
        except ValueError:
            error_message = f"Failed to parse hours, minutes, and seconds from DT response: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        # Create timedelta for elapsed time
        elapsed_time: timedelta = timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds)

        clock_status.elapsed_time = elapsed_time
        clock_status.sync_status = sync_status

    def _parse_absolute_dt_response(self, dt_line: str, clock_status: ClockStatus) -> ClockStatus:
        """
        Parse a DT response line that contains absolute datetime.

        Expected format: "YYYY-MM-DD HH:MM:SS.milliseconds [G|N|U] [optional timezone]"

        Parameters
        ----------
        dt_line : str
            The raw DT response line from the device.

        Returns
        -------
        ClockStatus
            Parsed DT response encapsulated in a ClockStatus object with datetime, sync_status, and timezone.
        """

        parts = dt_line.split()
        if len(parts) < 4: # Expect at least date, time, sync status, and timezone
            error_message = f"Unrecognized DT response format: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        date_str = parts[0]  # YYYY-MM-DD
        time_str = parts[1]  # HH:MM:SS.milliseconds
        sync_status: str = parts[2]  # G, N, or U (single character)

        # Validate sync status is a single recognized character
        if sync_status not in self.TIME_STATUSES:
            error_message = f"Unrecognized sync status '{sync_status}' in DT response: {dt_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        # Parse time and milliseconds
        milliseconds_used = '.' in time_str

        if milliseconds_used:
            time_part, milliseconds_str = time_str.split('.')
            milliseconds = int(milliseconds_str)
        else:
            time_part = time_str
            milliseconds = 0

        dt_temp = datetime.strptime(f"{date_str} {time_part}", "%Y-%m-%d %H:%M:%S")
        day, month, year, hour, minute, second = dt_temp.day, dt_temp.month, dt_temp.year, dt_temp.hour, dt_temp.minute, dt_temp.second

        dt = datetime(year, month, day, hour, minute, second, microsecond=milliseconds*1000)

        clock_status.datetime = dt
        clock_status.sync_status = sync_status

    def _send_tz_command(self) -> str:
        try:
            lines = self._session.send_command(DeviceCommand.TZ)
        except Exception as e:
            error_message = f"Failed to send TZ command: {e}"
            LOGGER.error(error_message)
            raise CommandTransmissionError(error_message)

        if len(lines) != 2: # TODO is it always two lines or does it vary based on sync status?
            error_message = f"Unexpected number of lines in TZ response: {len(lines)}. Response: {lines}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        tz_line = lines[0].strip()

        return tz_line

    def _parse_tz_response(self, tz_line: str, clock_status: ClockStatus) -> None:
        """
        Parse timezone response from TZ command.

        Parameters
        ----------
        tz_line : str
            The raw TZ response line from the device.

        Returns
        -------
        None
        """

        hours = 0
        minutes = 0
        sign = 1

        tz_line_format = None
        if tz_line.startswith("Hours:minutes to UT:"):
            tz_line_format = "hours_minutes"
        elif tz_line.startswith("Hours to UT:"):
            tz_line_format = "hours_only"
        else:
            error_message = f"Unrecognized timezone format: {tz_line}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        # FORMAT 1: "Hours:minutes to UT: +3h30m"
        if tz_line_format == "hours_minutes":
            offset_part = tz_line.split("Hours:minutes to UT:")[1].strip()

            # Determine sign of timezone offset
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

            # Parse hours and minutes
            try:
                hours = int(offset_part.split('h')[0].strip())
                minutes = int(offset_part.split('h')[1].strip().split('m')[0].strip())
            except (IndexError, ValueError) as e:
                error_message = f"Failed to parse hours and minutes from TZ response: {tz_line}"
                LOGGER.error(error_message)
                raise UnexpectedResponseError(error_message)


        #FORMAT 2: "Hours to UT: +0"
        elif tz_line_format == "hours_only":
            # Format 2: "Hours to UT: +0"
            offset_part = tz_line.split("Hours to UT:")[1].strip()

            # Determine sign
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

            # Parse hours only
            hours = int(offset_part)



        # Calculate total offset and return timezone object
        total_seconds = sign * (hours * 3600 + minutes * 60)

        tz = timezone(timedelta(seconds=total_seconds))
        clock_status.timezone = tz
        clock_status.datetime = clock_status.datetime.replace(tzinfo=tz) if clock_status.datetime else None
