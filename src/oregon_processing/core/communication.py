import re
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

        transmit_command(connection=self._connection, command=command, argument=argument)
        lines, prompt_prefix = receive_response(command=command, connection=self._connection, timeout=timeout, argument=argument)
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

        parts = command_text.strip().split(None, 1)
        main_code = parts[0].upper()
        argument = parts[1].strip() if len(parts) == 2 else None
        if argument == "":
            argument = None

        command = DeviceCommand(main_code)
        if argument and command not in SPACE_ARGUMENT_COMMANDS:
            raise ValueError(
                f"Command '{command}' does not support space-separated arguments. "
                "Use a compact command enum value instead."
            )

        transmit_command(connection=self._connection, command=command, argument=argument)
        lines, prompt_prefix = receive_response(command=command, connection=self._connection, timeout=timeout, argument=argument)
        self._last_prompt_prefix = prompt_prefix or self._last_prompt_prefix
        return lines

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()

# =============================================================================================================================================
# Public functions
# =============================================================================================================================================
def _serialize_command(command: DeviceCommand, argument: Optional[str] = None) -> str:
    """Serialize a DeviceCommand and optional argument into the exact wire format."""

    if not isinstance(command, DeviceCommand):
        raise ValueError("Command must be a valid DeviceCommand instance.")

    if not isinstance(argument, (str, type(None))):
        raise ValueError("Argument must be a string or None.")

    if argument is not None:
        argument = argument.strip()
        if argument == "":
            argument = None

    if argument and command not in SPACE_ARGUMENT_COMMANDS:
        raise ValueError(
            f"Command '{command}' does not support space-separated arguments. "
            "Define and use an explicit DeviceCommand enum value for compact command forms."
        )

    if argument:
        return f"{command.value} {argument}"

    return command.value


def is_valid_command(command_text: str) -> bool:
    """Validate a full command string."""

    if not command_text or not command_text.strip():
        return False

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


def transmit_command(connection: Serial, command: DeviceCommand, argument: Optional[str] = None):
    """Transmit a DeviceCommand after parsing and serializing any optional argument."""

    if not isinstance(connection, Serial):
        raise ValueError("Connection must be a valid Serial instance.")

    if not connection.is_open:
        raise ValueError("Connection must be open.")

    if not isinstance(command, DeviceCommand):
        raise ValueError("Command must be a valid DeviceCommand instance.")

    if not isinstance(argument, (str, type(None))):
        raise ValueError("Argument must be a string or None.")

    command_text = _serialize_command(command, argument)

    # drain any remaining data from the connection buffer before transmitting
    _drain_connection_buffer(connection)

    connection.write((command_text + "\r\n").encode())
    connection.flush()


def receive_response(
    command: DeviceCommand | str,
    connection: Serial,
    timeout: float = 5,
    argument: Optional[str] = None,
) -> Tuple[list[str], Optional[str]]:
    """
    Receive response lines until ready prompt or idle timeout.

    The command may be passed as a DeviceCommand plus optional argument, or as a
    raw command string. The normalized command text is used to strip echoed input.
    """

    if isinstance(command, str):
        command_text = command.strip()
        if not command_text:
            raise ValueError("Command must be a non-empty string.")
        parts = command_text.split(None, 1)
        main_code = parts[0].upper()
        try:
            command_enum = DeviceCommand(main_code)
        except ValueError as exc:
            raise ValueError(f"Invalid command '{main_code}'.") from exc
        argument = parts[1].strip() if len(parts) == 2 else None
        if argument == "":
            argument = None
        command_text = _serialize_command(command_enum, argument)
    elif isinstance(command, DeviceCommand):
        command_text = _serialize_command(command, argument)
    else:
        raise ValueError("Command must be a valid DeviceCommand or command string.")

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

    lines = _clean_response_lines(lines, command_text)
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
    ignored_patterns = (
        re.compile(r"^I\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?"), # I detection lines
        re.compile(r"Database file open"),
        re.compile(r"ORMR ready"),
        re.compile(r"Bluetooth is off"),
        re.compile(r"Bluetooth is on"),
        re.compile(r"COMM ready"),
    )

    cleaned = [line for line in lines if line] # Remove empty lines from the response to simplify further processing
    cleaned = [line for line in cleaned if line != command] # Remove the echoed command from the response lines

    # Remove lines that match any of the ignored patterns defined above
    cleaned = [
        line for line in cleaned
        if not any(pattern.search(line) for pattern in ignored_patterns)
    ]
    return cleaned


def _drain_connection_buffer(connection: Serial) -> None:
    """Discard stale bytes already waiting in the input buffer before sending a new command."""
    if not isinstance(connection, Serial):
        raise ValueError("Connection must be a valid Serial instance.")

    if not connection.is_open:
        raise ValueError("Connection must be open.")

    previous_timeout = connection.timeout
    try:
        connection.timeout = 0.05
        while True:
            chunk = connection.read(4096)
            if not chunk:
                break
            time.sleep(0.02)
    finally:
        connection.timeout = previous_timeout