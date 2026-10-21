from serial import Serial
from serial.tools import list_ports

from oregon_processing.core.communication import ConnectionSession
from oregon_processing.util.logging_manager import get_logger
from oregon_processing.core.device_status import DeviceStatusChecker

LOGGER = get_logger(__name__)
BAUD_RATE = 115200

class NotApplicableObject:
    """Class to represent a not applicable object for optional fields."""

    def __repr__(self):
        return "<NotApplicableObject>"

    def __bool__(self):
        return False

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

    first_attempt = True
    while True:

        selected_ports = _select_ports(first_attempt=first_attempt)
        first_attempt = False

        result: ConnectionResult = _attempt_connection(selected_ports)
        if result.success:
            return result

        LOGGER.info("Connection failed on all attempted port/baud combinations.")

        while True:
            retry = input("\nWould you like to retry connection? (y/n): ").strip().lower()
            if retry in ["y", "yes", "n", "no"]:
                break

        if retry not in ["y", "yes"]:
            LOGGER.debug("User has chosen not to retry connection. Exiting connection process.")
            return result

        LOGGER.debug("User has chosen to retry connection.")


def _select_ports(first_attempt: bool = False) -> list[str]:
    LOGGER.debug("Prompting user to select port(s) for connection attempt.")

    if first_attempt:
        LOGGER.debug("First attempt: default port search flow with fixed baud rate.")
        return _handle_prolific_port_search()

    selection_options = "\nPort selection options:"
    selection_options += "\n  1. Select a specific port to attempt"
    selection_options += "\n  2. Attempt all available ports"
    selection_options += "\n  3. Search for Prolific USB serial adapter ports"
    selection_options += "\n  4. Cancel port selection"

    LOGGER.info(selection_options)
    while True:

        choice = input("\nEnter your choice (1, 2, 3, or 4): ").strip()
        print()


        if choice == "1":
            LOGGER.debug("User selected option to manually select a port.")
            selected_port: str | None = _handle_manual_port_selection()
            selected_ports: list[str] = [selected_port] if selected_port else []
        elif choice == "2":
            LOGGER.debug("User selected option to attempt all available ports.")
            selected_ports: list[str] = _handle_all_ports_selection()
        elif choice == "3":
            LOGGER.debug("User selected option to search for Prolific USB serial adapter ports.")
            selected_ports: list[str] = _handle_prolific_port_search()
        elif choice == "4":
            LOGGER.debug("User cancelled port selection.")
            selected_ports = []
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
            continue

        return selected_ports


def _attempt_connection(ports: list[str]) -> ConnectionResult:
    """Attempt connection on a list of ports using the fixed baud rate."""
    if not ports:
        return ConnectionResult(success=False, error_message="No ports provided for connection attempt.")

    for port in ports:
        LOGGER.info(f"Attempting connection to {port} at {BAUD_RATE} baud.")

        ser = None
        try:
            ser = Serial(port, baudrate=BAUD_RATE, timeout=0.2, write_timeout=0.2)
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            ser.write(b"SY\r\n")
            ser.flush()

            response = ser.readline().decode(errors="ignore").strip()

            if response:
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

    selection_options = "Available ports:\n"
    for i, port in enumerate(ports, 1):
        selection_options += f"  {i}. {port.device} - {port.description}\n"
    selection_options += f"  {len(ports) + 1}. Cancel and return to previous menu\n"
    LOGGER.info(selection_options)

    while True:
        port_choice = input("\nSelect a port (enter number): ").strip()
        try:
            port_index = int(port_choice) - 1
        except ValueError:
            print("Invalid input. Please enter a number from the list.")
            continue

        if 0 <= port_index < len(ports):
            LOGGER.debug(f"User selected port: {ports[port_index].device} - {ports[port_index].description}")
            return ports[port_index].device
        if port_index == len(ports):
            LOGGER.debug("User cancelled manual port selection.")
            return None

        print("Invalid selection. Please enter a number from the list.")


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
