from oregon_processing.core.export_protocol import run_export_protocol as execute_export_protocol
from oregon_processing.exceptions import (InvalidConfigError, ConnectionFailedError, NoPortsAvailableError, UnexpectedResponseError,
                                    CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError,
                                    FormatChangeError, NoFileSelectedError, InvalidProjectDirectoryError, ExportFailedError)


def run_export_protocol():
    try:
        execute_export_protocol()
    except InvalidConfigError as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is valid, then try again.")
        return
    except (ConnectionFailedError, NoPortsAvailableError, UnexpectedResponseError, CommandTransmissionError, UserCancelledError, DeviceHealthError,
            ClockSyncError, ModeChangeError, FormatChangeError, NoFileSelectedError, InvalidProjectDirectoryError,
            ExportFailedError) as e:
        print(f"\n\nExport protocol failed\nPlease check the log file for details.\n\n")
        return
    except Exception as e:
        print(f"\n\nExport protocol failed unexpectedly.\nAn unexpected error occurred: {str(e)}\n\n")
        return

    print(f"\n\nExport protocol completed successfully.\n\n")


if __name__ == "__main__":
    run_export_protocol()