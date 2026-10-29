from typing import Optional

from oregon_processing.core.communication import is_valid_command
from oregon_processing.core.connection import ConnectionSession
from oregon_processing.util.logging_manager import get_logger

LOGGER = get_logger(__name__)

# Support for history of readline on Windows via pyreadline3
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows

class InteractiveTerminal:
    """Interactive terminal for sending commands to Oregon RFID device."""

    def __init__(self, session: ConnectionSession):
        """
        Initialize the interactive terminal.

        Parameters
        ----------
        session : ConnectionSession
            Connection session instance for sending commands to device.
        """
        self._session: ConnectionSession = session

    def run(self):
        """
        Start the interactive terminal session.

        Allows user to enter commands, validates them, sends them to the device,
        and displays responses. Type 'exit' or 'quit' to exit the terminal.
        """


        LOGGER.info("Entering interactive terminal. Type 'exit' to quit.")

        try:
            while True:
                prompt = f"\n{self._session.prompt_prefix or ''}>> "
                cmd = input(prompt).strip()
                if not cmd:
                    continue

                # Exit on 'exit' or 'quit'
                if cmd.lower() in ("exit", "quit"):
                    LOGGER.info("Exiting terminal.")
                    break

                # Validate command format
                if not is_valid_command(cmd):
                    LOGGER.warning("Invalid command. Use a two-letter code followed by a space (e.g., 'SY ').")
                    LOGGER.info(f"Valid codes: {sorted(self._session.VALID_COMMANDS)}")
                    continue

                # send command and get cleaned response
                lines: list[str]
                lines, _ = self._session.send_raw_command(cmd)
                if lines:
                    LOGGER.info("Response:\n"+"\n".join(lines))
                else:
                    LOGGER.info("Command received without error")

        except KeyboardInterrupt:
            LOGGER.info("Terminal interrupted by user.")
