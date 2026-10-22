import time
from enum import Enum
from typing import Optional, Tuple
from serial import Serial


class DeviceCommand(str, Enum):
    # Reader power / operation
    ON = "ON"
    ST = "ST"
    OF = "OF"

    # Bluetooth
    BT0 = "BT0"
    BT1 = "BT1"

    # Status / diagnostics
    SY = "SY"
    NO = "NO"
    AB = "AB"
    QU = "QU"
    HE = "HE"

    # Beeper / LEDs / display
    BP0 = "BP0"
    BP1 = "BP1"
    BP2 = "BP2"
    BR1 = "BR1"
    BR2 = "BR2"
    BR3 = "BR3"
    DK = "DK"

    # Antenna / tuning
    TU = "TU"
    TO = "TO"
    AP = "AP"
    AS = "AS"
    MQ = "MQ"
    SM = "SM"
    SMA = "SMA"
    MX = "MX"
    MV = "MV"

    # Timing / scheduling
    TM = "TM"
    DT = "DT"
    TZ = "TZ"
    TZ0 = "TZ0"
    TZ_NEG1 = "TZ-1"
    OVG = "OVG"
    OVN = "OVN"

    # Scan / detection behavior
    DM = "DM"
    FS = "FS"
    TF = "TF"
    TC = "TC"
    RE = "RE"
    MP = "MP"
    PH0 = "PH0"
    PH1 = "PH1"
    HD = "HD"
    HDR = "HDR"
    HDC = "HDC"
    HDL = "HDL"
    MC = "MC"

    # Configuration / identity
    RN = "RN"
    SC = "SC"
    BC = "BC"
    BCR = "BCR"

    # Datalogger / records
    UH = "UH"
    UP = "UP"
    UP_ALL = "UP*"
    UPS = "UPS"
    UD = "UD"
    UT = "UT"
    ER = "ER"
    CO = "CO"
    TL = "TL"
    FM = "FM"
    FN = "FN"
    WE0 = "WE0"
    WE1 = "WE1"
    LA = "LA"
    CS = "CS"
    MG = "MG"

    # Network / multi-reader
    NL = "NL"
    SL = "SL"

    # GNSS / location / sensors
    GNS0 = "GNS0"
    GNS1 = "GNS1"
    LO = "LO"
    TS = "TS"

    # Utilities
    CV = "CV"

    # Firmware / maintenance
    FW = "FW"
    RD = "RD"
    RB = "RB"
    FR = "FR"
    FRD = "FRD"
    FRR = "FRR"
    FRA = "FRA"

    def __str__(self) -> str:
        return self.value


SPACE_ARGUMENT_COMMANDS = frozenset(
    {
        DeviceCommand.DT,
        DeviceCommand.ER,
        DeviceCommand.FM,
    }
)


PROMPT_PREFIX_SETS = (
    {"0", "H", "N"},  # operating mode
    {"R", "S", "Z"},  # run state
    {"G", "N", "U", "E"},  # time sync state
    {"B", "*"},  # beeper
)


class ConnectionSession:
    """Stateful session for sending commands and managing one serial connection."""

    def __init__(self, connection: Serial):
        if not isinstance(connection, Serial):
            raise ValueError("Connection must be a valid Serial instance.")
        if not connection.is_open:
            raise ValueError("Connection must be open.")

        self._connection = connection
        self._last_prompt_prefix: Optional[str] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_open

    @property
    def prompt_prefix(self) -> Optional[str]:
        """Get the last received prompt prefix by refreshing from SY."""
        self.send_command(DeviceCommand.SY)
        return self._last_prompt_prefix

    def send_command(self, command: DeviceCommand, argument: Optional[str] = None, timeout: float = 5) -> list[str]:

        if not isinstance(command, DeviceCommand):
            raise ValueError("Command must be a valid DeviceCommand instance.")

        if not isinstance(argument, (str, type(None))):
            raise ValueError("Argument must be a string or None.")

        if argument and command not in SPACE_ARGUMENT_COMMANDS:
            raise ValueError(
                f"Command '{command}' does not support space-separated arguments. "
                "Define and use an explicit DeviceCommand enum value for compact command forms."
            )

        command = str(command)

        if argument:
            command = f"{command} {argument}"

        transmit_command(self._connection, command)
        lines, prompt_prefix = receive_response(command, self._connection, timeout)
        self._last_prompt_prefix = prompt_prefix or self._last_prompt_prefix
        return lines

    def send_raw_command(self, command_text: str, timeout: float = 5) -> list[str]:
        """Parse raw command text into enum + optional argument and send it."""

        if not isinstance(command_text, str):
            raise ValueError("Command text must be a string.")

        if not command_text.strip():
            raise ValueError("Command text must be a non-empty string.")

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Timeout must be a positive number.")

        transmit_command(self._connection, command_text)
        lines, prompt_prefix = receive_response(command_text, self._connection, timeout)
        self._last_prompt_prefix = prompt_prefix or self._last_prompt_prefix
        return lines

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()

# =============================================================================================================================================
# Public functions
# =============================================================================================================================================
def is_valid_command(command_text: str) -> bool:
    """Validate a full command string."""

    if not command_text or not command_text.strip():
        return False

    # try to parse the command text as a DeviceCommand. If it fails then the command is invalid.
    try:
        parts = command_text.strip().split(None, 1)
        main_code = parts[0].upper()
        argument = parts[1].strip() if len(parts) == 2 else None
        if argument == "":
            argument = None

        try:
            command = DeviceCommand(main_code)
        except ValueError as exc:
            raise ValueError(f"Invalid command '{main_code}'.") from exc

        if argument and command not in SPACE_ARGUMENT_COMMANDS:
            raise ValueError(
                f"Command '{command}' does not support space-separated arguments. "
                "Use a compact command enum value instead."
            )

    except ValueError:
        return False

    return True


def transmit_command(connection: Serial, command: str):
    """Transmit command after clearing and draining input buffer."""

    if not isinstance(connection, Serial):
        raise ValueError("Connection must be a valid Serial instance.")

    if not connection.is_open:
        raise ValueError("Connection must be open.")

    if not command or not command.strip() or not isinstance(command, str):
        raise ValueError("Command must be a non-empty string.")

    # drain any remaining data from the connection buffer before transmitting
    _drain_connection_buffer(connection)

    connection.write((command + "\r\n").encode())
    connection.flush()


def receive_response(
    command: str,
    connection: Serial,
    timeout: float = 5,
    ) -> Tuple[list[str], Optional[str]]:
    """
    Receive response lines until ready prompt or idle timeout.

    Returns
    -------
    tuple[list[str], Optional[str]]
        Tuple of collected response lines and the last valid prompt signature seen.
    """

    if command is None or not command.strip():
        raise ValueError("Command must be a non-empty string.")

    if not isinstance(connection, Serial):
        raise ValueError("Connection must be a valid Serial instance.")

    if not connection.is_open:
        raise ValueError("Connection must be open.")

    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Timeout must be a positive number.")

    lines: list[str] = []
    last_prompt_prefix: Optional[str] = None
    last_data_time = time.time()

    while True:
        line: str = connection.readline().decode(errors="ignore").strip()

        if line:
            prompt_prefix, prompt_remainder = _split_prompt_prefix(line)
            if prompt_prefix is not None:
                last_prompt_prefix = prompt_prefix
                if not prompt_remainder:
                    break
                if prompt_remainder:
                    lines.append(prompt_remainder)
                    last_data_time = time.time()
                continue

            lines.append(line)
            last_data_time = time.time()

        if time.time() - last_data_time > timeout:
            break

    if command is not None:
        lines = _clean_response_lines(lines, command)

    return lines, last_prompt_prefix


def _split_prompt_prefix(line: str) -> Tuple[str|None, str]:
    """
    Split a line into prompt signature and remainder.

    Returns (signature, remainder_without_optional_arrow). When no valid prompt
    prefix exists, returns (None, original_line).
    """
    if not isinstance(line, str) or len(line) < 4:
        return None, line

    signature = line[:4]
    if not _is_valid_prompt_prefix(signature):
        return None, line

    remainder = line[4:].lstrip(">").strip()
    return signature, remainder


def _is_valid_prompt_prefix(signature: str) -> bool:
    """Return True when signature matches the 4-character prompt format."""
    if not isinstance(signature, str) or len(signature) != 4:
        return False
    return all(char in valid for char, valid in zip(signature, PROMPT_PREFIX_SETS))


def _clean_response_lines(lines: list[str], command: str) -> list[str]:
    """Clean response lines by removing echoed command and known extraneous lines."""
    cleaned = lines
    cleaned = [line for line in cleaned if line != "Database file open"]
    cleaned = [line for line in cleaned if "ORMR ready" not in line]
    cleaned = [line for line in cleaned if line != "Bluetooth is off"]
    cleaned = [line for line in cleaned if line != "Bluetooth is on"]
    cleaned = [line for line in cleaned if line != "COMM ready"]
    cleaned = [line for line in cleaned if line and line != command]
    return cleaned


def _drain_connection_buffer(connection: Serial) -> None:
    """Drain any remaining data from the connection buffer."""
    if not isinstance(connection, Serial):
        raise ValueError("Connection must be a valid Serial instance.")

    if not connection.is_open:
        raise ValueError("Connection must be open.")

    connection.reset_input_buffer()
    time.sleep(0.05)

    previous_timeout = connection.timeout
    try:
        connection.timeout = 0.1
        while connection.in_waiting > 0:
            connection.read(connection.in_waiting)
            time.sleep(0.01)
    finally:
        connection.timeout = previous_timeout