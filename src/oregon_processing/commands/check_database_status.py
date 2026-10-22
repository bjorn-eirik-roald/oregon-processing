from oregon_processing.core.database_manager import print_last_exported_detection_record_dates
from oregon_processing.core.project import open_previous_project
from oregon_processing.exceptions import (InvalidConfigError, ConnectionFailedError, UnexpectedResponseError,
                                    CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError,
                                    FormatChangeError, NoFileSelectedError, InvalidProjectDirectoryError, ExportFailedError)

def check_database_status():

    try:
        open_previous_project()
        print_last_exported_detection_record_dates()

    except InvalidConfigError as e:
        print(f"\n\n"+str(e) + "\n\nPlease ensure the configuration file is valid, then try again.")
        return
    except (ConnectionFailedError, UnexpectedResponseError,
            CommandTransmissionError, UserCancelledError, DeviceHealthError, ClockSyncError, ModeChangeError,
            FormatChangeError, NoFileSelectedError, InvalidProjectDirectoryError, ExportFailedError) as e:
        print(f"\n\nAn error occurred\nPlease check the log file for details.\n\n")
        return
    except Exception as e:
        print(f"\n\nUnexpected error occurred: {str(e)}\n\n")
        return



if __name__ == "__main__":
    check_database_status()
