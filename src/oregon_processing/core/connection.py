from serial import Serial
from serial.tools import list_ports

from oregon_processing.core.communication import ConnectionSession, receive_response, transmit_command
from oregon_processing.core.device_status import clear_approved_unrecognized_status_lines
from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.multi_choice_popup import confirm_prompt, multi_choice_prompt, vertical_multi_choice_prompt
from oregon_processing.util.logging_manager import get_logger

from oregon_processing.core.communication import DeviceCommand

LOGGER = get_logger(__name__)
BAUD_RATE = 115200

class NotApplicableObject:
    """Class to represent a not applicable object for optional fields."""

    def __repr__(self):
        return "<NotApplicableObject>"

NOT_APPLICABLE = NotApplicableObject()

class ConnectionResult:
    def __init__(self, success: bool, session:
                 ConnectionSession | NotApplicableObject = NOT_APPLICABLE,
                 port: str | NotApplicableObject = NOT_APPLICABLE,
                 error_message: str = ""):
        self.success: bool = success
        self.session: ConnectionSession | NotApplicableObject = session
        self.port: str | NotApplicableObject = port
        self.error_message: str | None = error_message


def connect() -> ConnectionResult:
    LOGGER.info("Initializing connection attempt")

    # new connection --> clear previously approved unrecognized status lines
    clear_approved_unrecognized_status_lines()

    first_attempt = True
    while True:

        selected_ports = _select_ports(first_attempt=first_attempt)
        first_attempt = False

        result: ConnectionResult = _attempt_connection(selected_ports)
        if result.success:
            return result

        LOGGER.info("Connection failed on all attempted port/baud combinations.")

        retry = confirm_prompt(
            message="Would you like to retry connection?",
            title="Connection retry",
            confirm_button_text="Retry",
            cancel_button_text="Stop",
            window_height=125,
            window_width=400
        )

        if not retry:
            LOGGER.debug("User has chosen not to retry connection. Exiting connection process.")
            return result

        LOGGER.debug("User has chosen to retry connection.")


def _select_ports(first_attempt: bool = False) -> list[str]:
    LOGGER.debug("Prompting user to select port(s) for connection attempt.")

    if first_attempt:
        LOGGER.debug("First attempt: default port search flow with fixed baud rate.")
        return _handle_prolific_port_search()

    selection_options = "\nPort selection options:"
    selection_options += "\n  - Port: select a specific port to attempt"
    selection_options += "\n  - All: attempt all available ports"
    selection_options += "\n  - Prolific: search for Prolific USB serial adapter ports"
    selection_options += "\n  - Cancel: stop port selection"
    LOGGER.info(selection_options)

    try:
        choice = multi_choice_prompt(
            choices=["Port", "All", "Prolific", "Cancel"],
            title="Select port mode",
            prompt_section_1_prompt_text=(
                "Choose how to select the serial port:\n\n"
                "• Port: pick a single port from the list of available COM ports\n"
                "• All: try every available port until connection succeeds\n"
                "• Prolific: search for Prolific USB serial adapter ports only\n"
                "• Cancel: stop the connection attempt"
            ),
            prompt_section_1_prompt_anchor="center",
            prompt_section_1_prompt_justify="left",
            window_height=225,
            window_width=450,
        )
    except UserCancelledError:
        LOGGER.debug("User cancelled port selection from popup.")
        return []

    if choice == "Port":
        LOGGER.debug("User selected option to manually select a port.")
        selected_port: str | None = _handle_manual_port_selection()
        return [selected_port] if selected_port else []
    if choice == "All":
        LOGGER.debug("User selected option to attempt all available ports.")
        return _handle_all_ports_selection()
    if choice == "Prolific":
        LOGGER.debug("User selected option to search for Prolific USB serial adapter ports.")
        return _handle_prolific_port_search()

    LOGGER.debug("User cancelled port selection.")
    return []


def _attempt_connection(ports: list[str]) -> ConnectionResult:
    """Attempt connection on a list of ports using the fixed baud rate."""
    if not ports:
        return ConnectionResult(success=False, error_message="No ports provided for connection attempt.")

    for port in ports:
        LOGGER.info(f"Attempting connection to {port} at {BAUD_RATE} baud.")

        ser = None
        try:
            ser = Serial(port, baudrate=BAUD_RATE, timeout=0.5, write_timeout=0.5)

            transmit_command(connection=ser, command=DeviceCommand.SY)
            _, prompt_prefix = receive_response(connection=ser, command=DeviceCommand.SY, timeout=2.0)
            if prompt_prefix:
                LOGGER.info(f"Successfully connected to {port} at {BAUD_RATE} baud.")
                return ConnectionResult(success=True, session=ConnectionSession(ser), port=port)

            ser.close()
            LOGGER.info("No response when attempting connection.")
        except Exception as e:
            if ser and ser.is_open:
                ser.close()

            error_message = f"Error when connecting to {port} at {BAUD_RATE} baud: {e}"
            LOGGER.error(error_message)

    return ConnectionResult(success=False, error_message="Failed to connect on all attempted port/baud combinations.")


def _handle_manual_port_selection() -> str | None:
    """Handle user selecting a specific port. Returns selected port device or None."""
    LOGGER.debug("Prompting user to manually select a port from the list of available ports.")

    ports = _get_all_ports()
    if not ports:
        LOGGER.info("No ports available.")
        return None

    port_choices = [port.device for port in ports]
    LOGGER.info("Available ports: %s", port_choices)

    try:
        choice = vertical_multi_choice_prompt(
            choices=port_choices + ["Cancel"],
            title="Select port",
            prompt_section_1_prompt_text="Choose the serial port to attempt.",
            prompt_section_1_prompt_anchor="center",
            prompt_section_1_prompt_justify="center",
            window_width=400,
            base_window_height=70
        )
    except UserCancelledError:
        LOGGER.debug("User cancelled manual port selection.")
        return None

    if choice == "Cancel":
        LOGGER.debug("User cancelled manual port selection.")
        return None

    LOGGER.debug(f"User selected port: {choice}")
    return choice


def _handle_prolific_port_search() -> list[str]:
    """Return list of Prolific ports (if any) for later connection attempt."""
    LOGGER.debug("Searching for Prolific USB serial adapter ports among available ports.")

    ports = _get_all_ports()
    prolific_ports = [p.device for p in ports if "prolific" in p.description.lower()]
    if prolific_ports:
        LOGGER.info(f"Found Prolific USB serial adapter port(s): {prolific_ports}")
        return prolific_ports

    LOGGER.info("No Prolific USB serial adapter ports found.")
    return []


def _handle_all_ports_selection() -> list[str]:
    """Return list of all available port devices for later connection attempt."""
    LOGGER.debug("Creating list of all available ports for connection attempt.")

    ports = _get_all_ports()
    if not ports:
        LOGGER.info("No ports available.")
        return []

    port_devices = [p.device for p in ports]
    LOGGER.info(f"Each available port will be attempted: {port_devices}")
    return port_devices


def _get_all_ports():
    """
    Get list of all available ports.

    Returns
    -------
    list
        List of available port objects.
    """
    return [p for p in list_ports.comports()]
