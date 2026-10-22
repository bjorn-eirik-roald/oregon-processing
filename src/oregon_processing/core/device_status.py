from oregon_processing.core.communication import ConnectionSession, DeviceCommand
from oregon_processing.util.logging_manager import get_logger

LOGGER = get_logger(__name__)

from oregon_processing.exceptions import NoFileSelectedError, UnexpectedResponseError, UserCancelledError
from oregon_processing.core.device_mode import is_valid_mode

from dataclasses import dataclass, field
from typing import Optional, ClassVar

import re

class FirmwareVersion:
    """Class to represent the firmware version of the Oregon RFID device."""

    def __init__(self, version_str: str):
        """
        Initialize FirmwareVersion by parsing version string.

        Parameters
        ----------
        version_str : str
            Version string in format like 'V2.74N' or 'V2.74'.
        """
        self._original_str = version_str

        self._version_number = None
        self._major = None
        self._minor = None
        self._suffix = None

        self._parse_version_string(version_str)

    @property
    def version_number(self) -> Optional[float]:
        """Get the version number as a float (e.g., 2.74)."""
        return self._version_number

    @property
    def major(self) -> Optional[int]:
        """Get the major version number (e.g., 2 in V2.74)."""
        return self._major

    @property
    def minor(self) -> Optional[int]:
        """Get the minor version number (e.g., 74 in V2.74)."""
        return self._minor

    @property
    def suffix(self) -> Optional[str]:
        """Get the suffix of the version (e.g., 'N' or 'M'), or None if no suffix."""
        return self._suffix

    @property
    def original_str(self) -> str:
        """Get the original version string."""
        return self._original_str

    def _parse_version_string(self, version_str: str):
        """
        Parse the version string and set major, minor, and suffix attributes.

        Parameters
        ----------
        version_str : str
            Version string in format like 'V2.74N' or 'V2.74' or 'V1.998'.
        """
        # Starts with 'V' followed by unknown number of digits for major, then a dot, then unknown number of digits for minor, then optional single letter suffix

        version_str = version_str.strip().upper()  # normalize to uppercase and strip whitespace
        match = re.match(r"V([0-9]+)\.([0-9]+)([A-Z]*)", version_str)
        if match:
            self._major = int(match.group(1))
            self._minor = int(match.group(2))
            self._suffix = match.group(3) if match.group(3) else None
            self._version_number = float(f"{self._major}.{self._minor}")
        else:
            raise UnexpectedResponseError(f"Invalid version string format: {version_str}")

@dataclass
class DeviceStatus:
    """Class to represent the device status and prerequisites for Oregon RFID processing."""

    # --- Class constants (NOT dataclass fields) ---
    MUST_HAVE_FIELDS: ClassVar[list[str]] = ['device_type', 'version', 'serial_number', 'reader_name', 'mode']
    ACCEPTED_DEVICE_TYPES: ClassVar[list[str]] = ['orsr', 'ormr']

    # --- Data fields ---
    device_type: Optional[str] = None
    version: Optional[FirmwareVersion] = None
    serial_number: Optional[str] = None
    reader_name: Optional[str] = None
    mode: Optional[str] = None
    supply_voltage: Optional[float] = None
    charge_pulse_amps: Optional[float] = None
    listen_amps: Optional[float] = None
    effective_amps: Optional[float] = None
    standby_amps: Optional[float] = None
    sleep_amps: Optional[float] = None
    noise: Optional[float] = None
    antenna_1: Optional[str] = None
    antenna_2: Optional[str] = None
    antenna_3: Optional[str] = None
    antenna_4: Optional[str] = None
    shutdown_supercap: Optional[str] = None
    sleep_battery: Optional[str] = None
    tags_in_archive: Optional[int] = None
    bluetooth_status: Optional[str] = None
    gnss_log_interval_minutes: Optional[int] = None
    raw_output: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    # --- Logic ---
    def check_prerequisites(self):
        if self.device_type.lower() not in self.ACCEPTED_DEVICE_TYPES:
            raise UnexpectedResponseError(
                f"Unsupported device type '{self.device_type}'. "
                f"Only {self.ACCEPTED_DEVICE_TYPES} are supported."
            )

        if not is_valid_mode(self.mode):
            raise UnexpectedResponseError(f"Unsupported device mode '{self.mode}'.")

        for field_name in self.MUST_HAVE_FIELDS:
            value = getattr(self, field_name)
            if not value:
                raise UnexpectedResponseError(
                    f"Missing expected field '{field_name}' in device status. "
                    f"Value: '{value}'"
                )

class DeviceStatusChecker:
    """Class to check device status and prerequisites for Oregon RFID processing."""

    def __init__(self, session: ConnectionSession):
        self._session: ConnectionSession = session

        self._ignored_lines: list[str] = []

    def get_device_status(self) -> DeviceStatus:

        status_lines = self._session.send_command(DeviceCommand.SY)

        status = DeviceStatus()  # create empty DeviceStatus

        # Validate we have at least 3 lines to parse the row 1-3, which are always in the same rows.
        if len(status_lines) < 3:
            error_message = f"Expected at least 3 lines in SY response, got {len(status_lines)}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        for line_num, line in enumerate(status_lines):
            line = line.strip()

            if not line:
                error_message = f"Empty line encountered in SY response at row {line_num + 1} of SY response."
                LOGGER.error(error_message)
                raise UnexpectedResponseError(error_message)

            if line in self._ignored_lines:
                LOGGER.debug(f"Ignoring previously approved unrecognized line in SY response at row {line_num + 1}: '{line}'")
                continue

            # Use specific parsing for the first 3 lines, then auto-parse the rest
            if line_num == 0:
                self._parse_line_1(line=line, status=status)
            elif line_num == 1:
                self._parse_line_2(line=line, status=status)
            elif line_num == 2:
                self._parse_line_3(line=line, status=status)
            else:
                self._auto_parse_line(line=line, line_num=line_num, status=status)

        try:
            status.check_prerequisites()  # validate prerequisites
        except UnexpectedResponseError as e:
            error_message = f"Device status prerequisites check failed: {str(e)}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        return status

    def _parse_line_1(self, line: str, status: DeviceStatus):
        match = re.search(r"^Oregon RFID\s+(.*)$", line, re.IGNORECASE)
        if not match:
            error_message = f"Unexpected device type line format at row 1 of SY response: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        device_type_str = match.group(1).strip()

        if 'single antenna' in device_type_str.lower():
            status.device_type = 'ORSR'
        elif 'multiple antenna' in device_type_str.lower():
            status.device_type = 'ORMR'
        else:
            error_message = f"Could not determine device type from line 1 of SY response: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _parse_line_2(self, line: str, status: DeviceStatus):
        match = re.search(r"^(V[0-9]+\.[0-9]+[A-Z]*)\s+([0-9A-Fa-f\-]+)$", line)
        if not match:
            error_message = f"Unexpected version/serial line format at row 2 of SY response: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        firmware_version_str = match.group(1).strip()
        serial_number_str = match.group(2).strip()


        try:
            version = FirmwareVersion(firmware_version_str)
        except UnexpectedResponseError as e:
            error_message = f"Unexpected version format in row 2 of SY response: '{line}' - {str(e)}"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        status.version = version
        status.serial_number = serial_number_str

    def _parse_line_3(self, line: str, status: DeviceStatus):
        status.reader_name = line

    def _auto_parse_line(self, line: str, line_num: int, status: DeviceStatus):

        match = False
        if not match: match: bool = self._attempt_parse_mode_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_supply_voltage_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_charge_pulse_amps_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_standby_amps_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_sleep_amps_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_listen_amps_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_effective_amps_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_noise_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_antenna_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_shutdown_supercap_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_shutdown_supply_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_sleep_battery_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_tags_in_archive_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_bluetooth_line(line=line, line_num=line_num, status=status)
        if not match: match = self._attempt_parse_gnss_log_line(line=line, line_num=line_num, status=status)

        if not match:
            self._handle_unrecognized_line(line=line, line_num=line_num)

    def _attempt_parse_mode_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:

        match = re.search(r"^(.*?)\s+mode\s*", line, re.IGNORECASE)
        if not match:
            return False
        else:
            mode = match.group(1).strip()

        # validate mode is one of expected values
        if not is_valid_mode(mode):
            error_message = f"Unexpected mode value parsed from SY response: '{mode}' in line {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

        status.mode = mode
        return True

    def _attempt_parse_supply_voltage_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^supply voltage\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            voltage = match.group(1).strip()

        try:
            status.supply_voltage = float(voltage)
            return True
        except ValueError:
            error_message = f"Could not parse supply voltage as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_charge_pulse_amps_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^charge pulse amps\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            charge_pulse_amps = match.group(1).strip()

        try:
            status.charge_pulse_amps = float(charge_pulse_amps)
            return True
        except ValueError:
            error_message = f"Could not parse charge pulse amps as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_listen_amps_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^listen amps\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            listen_amps = match.group(1).strip()

        try:
            status.listen_amps = float(listen_amps)
            return True
        except ValueError:
            error_message = f"Could not parse listen amps as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_effective_amps_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^effective amps\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            effective_amps = match.group(1).strip()

        try:
            status.effective_amps = float(effective_amps)
            return True
        except ValueError:
            error_message = f"Could not parse effective amps as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_standby_amps_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^standby amps\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            standby_amps = match.group(1).strip()

        try:
            status.standby_amps = float(standby_amps)
            return True
        except ValueError:
            error_message = f"Could not parse standby amps as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_sleep_amps_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^sleep amps\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            sleep_amps = match.group(1).strip()

        try:
            status.sleep_amps = float(sleep_amps)
            return True
        except ValueError:
            error_message = f"Could not parse sleep amps as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_noise_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^noise\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            noise = match.group(1).strip()

        try:
            status.noise = float(noise)
            return True
        except ValueError:
            error_message = f"Could not parse noise as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_antenna_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^antenna\s+#([0-9]+)\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)

        if not match:
            return False
        else:
            antenna_num = match.group(1).strip()
            antenna_value = match.group(2).strip()


        try:
            antenna_num = int(antenna_num)
            antenna_value = float(antenna_value)
            if antenna_num == 1:
                status.antenna_1 = antenna_value
            elif antenna_num == 2:
                status.antenna_2 = antenna_value
            elif antenna_num == 3:
                status.antenna_3 = antenna_value
            elif antenna_num == 4:
                status.antenna_4 = antenna_value
            else:
                raise ValueError(f"Unexpected antenna number: {antenna_num}")

            return True
        except ValueError as e:
            error_message = f"Unexpected antenna line format in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_shutdown_supercap_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^shutdown supercap\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            shutdown_supercap = match.group(1).strip()

        try:
            status.shutdown_supercap = float(shutdown_supercap)
            return True
        except ValueError:
            error_message = f"Could not parse shutdown supercap as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_shutdown_supply_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^shutdown supply\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            shutdown_supply = match.group(1).strip()

        try:
            status.shutdown_supply = float(shutdown_supply)
            return True
        except ValueError:
            error_message = f"Could not parse shutdown supply as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_sleep_battery_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^sleep battery\s+([0-9]+(?:\.[0-9]+)?)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            sleep_battery = match.group(1).strip()

        try:
            status.sleep_battery = float(sleep_battery)
            return True
        except ValueError:
            error_message = f"Could not parse sleep battery as float in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_tags_in_archive_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^tags in archive\s+([0-9]+)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            tags_in_archive = match.group(1).strip()

        try:
            status.tags_in_archive = int(tags_in_archive)
            return True
        except ValueError:
            error_message = f"Could not parse tags in archive as int in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _attempt_parse_bluetooth_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^bluetooth\s+is\s+(on|off)$", line, re.IGNORECASE)
        if not match:
            return False
        else:
            bluetooth_status = match.group(1).strip()

        status.bluetooth_status = bluetooth_status
        return True

    def _attempt_parse_gnss_log_line(self, line: str, line_num: int, status: DeviceStatus) -> bool:
        match = re.search(r"^gnss logged every\s+([0-9]+)\s+minutes$|^gnss log is off$", line, re.IGNORECASE)

        if not match:
            return False
        else:
            gnss_log_match = match.group(1)

        try:
            # If we have a match for the interval, parse it as int. If not, it means the log is off, so we set it to False
            if gnss_log_match:
                _ = int(gnss_log_match.strip()) # we parse it just to validate it's an int
                status.gnss_log_interval_minutes = True
            else:
                status.gnss_log_interval_minutes = False

            return True
        except ValueError:
            error_message = f"Could not parse GNSS log interval as int in SY response at row {line_num + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    def _handle_unrecognized_line(self, line: str, line_num: int):
        """

        Handle an unrecognized line in the device status response.


        Will prompt the user with a popup to confirm that the unrecognized line is not a problem for processing. This allows us to continue with processing
        even if there are some unexpected lines in the SY response, which may occur with different firmware versions or device models.

        Returns True if the user approves the unrecognized line, False if the user does not approve and wants to treat it as an error.
        """

        from oregon_processing.gui.popups.multi_choice_popup import confirm_prompt

        try:
            answer = confirm_prompt(message=f"Unrecognized line in device status response: '{line}'\n\nDo you want to ignore this line and continue with processing?",
                                   window_height=200, window_width=800)
        except (UserCancelledError, NoFileSelectedError):
            print("\n\nUnrecognized line approval cancelled by user. Aborting export protocol.\n\n")
            raise UserCancelledError

        if answer:
            LOGGER.warning(f"Unrecognized line in device status at row {line_num + 1} of SY response: '{line}' - User approved to ignore.")
            self._ignored_lines.append(line)
        else:
            error_message = f"Unrecognized line format in device status at row {line_num + 1} of SY response: '{line}'. User did not approve to ignore."
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)