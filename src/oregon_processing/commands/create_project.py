from oregon_processing.core.project import Project
from oregon_processing.util.logging_manager import LoggingManager, get_logger
LOGGER = get_logger(__name__)

from oregon_processing.exceptions import NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError

def create_project():

    try:
        with LoggingManager(write_to_report_file=False, write_to_console=True):
            Project.create_new_project()
    except (FileExistsError, NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError) as e:
        print(f"\n\nProject creation failed due to an error. Please see the log for more details:\n\n{str(e)}")
        return
    except Exception as e:
        print(f"\n\nAn unexpected error occurred during project creation:\n\n{str(e)}")
        return

    print("\n\nProject created successfully.\n\n")

if __name__ == "__main__":
    create_project()
