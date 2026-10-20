# -*- coding: utf-8 -*-
"""
Interactive Terminal for Oregon RFID Device

Provides a command-line interface for sending commands to the Oregon device
and receiving responses.
"""

from oregon_processing.util.logging_manager import get_logger

LOGGER = get_logger(__name__)

# Support for history of readline on Windows via pyreadline3
try:
    import readline  # Linux / macOS
except ImportError:
    import pyreadline3 as readline  # Windows

class InteractiveTerminal:
    """Interactive terminal for sending commands to Oregon RFID device."""

    def __init__(self, command_manager):
        """
        Initialize the interactive terminal.

        Parameters
        ----------
        command_manager : CommandManager
            CommandManager instance for sending commands to device.
        """
        self._command_manager = command_manager

    def run(self):
        """
        Start the interactive terminal session.

        Allows user to enter commands, validates them, sends them to the device,
        and displays responses. Type 'exit' or 'quit' to exit the terminal.
        """


        LOGGER.info("Entering interactive terminal. Type 'exit' to quit.")

        try:
            while True:
                prompt = f"\n{self._command_manager.prompt_signature or ''}>> "
                cmd = input(prompt).strip()
                if not cmd:
                    continue

                # Exit on 'exit' or 'quit'
                if cmd.lower() in ("exit", "quit"):
                    LOGGER.info("Exiting terminal.")
                    break

                # Validate command format
                if not self._command_manager.validate_command(cmd):
                    LOGGER.warning("Invalid command. Use a two-letter code followed by a space (e.g., 'SY ').")
                    LOGGER.info(f"Valid codes: {sorted(self._command_manager.VALID_MAIN_COMMANDS)}")
                    continue

                # send command and get cleaned response
                lines = self._command_manager.send_command(cmd)
                if lines:
                    LOGGER.info("Response:\n"+"\n".join(lines))
                else:
                    LOGGER.info("Command received without error")

        except KeyboardInterrupt:
            LOGGER.info("Terminal interrupted by user.")
