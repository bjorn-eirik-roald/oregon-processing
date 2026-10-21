"""
Execute the export protocol to retrieve data from a Oregon RFID and store in database define by project
"""

from oregon_processing.core.export_protocol import ExportProtocol
from oregon_processing.exceptions import (ConfigNotFoundError, InvalidConfigError, ConnectionFailedError, UnexpectedResponseError,
                                    CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError)


def run_export_protocol():

    try:
        with ExportProtocol() as export_protocol:
            export_protocol.run_export_protocol()
    except (ConfigNotFoundError, InvalidConfigError) as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is present and valid, then try again.")
    except (ConnectionFailedError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError) as e:
        print(f"\n\nAn error occurred during the export protocol\nPlease check the log file for details and try again.\n\n")

if __name__ == "__main__":
    run_export_protocol()