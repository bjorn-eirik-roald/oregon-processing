from oregon_processing.util.project import Project
from oregon_processing.util.logging_manager import LoggingManager, get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.exceptions import NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError

def create_project():

    try:
        with LoggingManager(write_to_report_file=False, write_to_console=True):
            Project.create_new_project()
            LOGGER.info("Project created successfully.")
    except (FileExistsError, NoFileSelectedError, InvalidProjectDirectoryError, UserCancelledError) as e:
        print(f"\n\nProject creation failed due to an error. Please see the error message below for more details:\n\n{str(e)}")

if __name__ == "__main__":
    create_project()
