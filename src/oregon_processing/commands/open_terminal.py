# -*- coding: utf-8 -*-
"""
Open Terminal connection to Oregon RFID Device
"""

from oregon_processing.exceptions import (ConfigNotFoundError, InvalidConfigError, ConnectionFailedError, UnexpectedResponseError,
                                    CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError)
from oregon_processing.util.logging_manager import LoggingManager, get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.communicator import Communicator

def open_terminal():

    try:
        with LoggingManager(write_to_console=True, write_to_report_file=False):
            with Communicator() as communicator:
                communicator.start_interactive_terminal()
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is present and valid, then try again.")
        return
    except (ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError) as e:
        print(f"\n\n"+"An error occurred while opening the terminal connection\nPlease check the log file for details and try again.\n\n")
        return

    print("\n\nTerminal session ended.\n\n")

if __name__ == "__main__":
    open_terminal()
