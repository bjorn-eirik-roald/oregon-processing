from pathlib import Path
import json

import oregon_processing
from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.exceptions import UserCancelledError, NoFileSelectedError, InvalidProjectDirectoryError
from oregon_processing.util.config import OregonConfig

from oregon_processing.gui.popups.browse import browse_directory
from oregon_processing.gui.popups.name_popup import name_prompt
from oregon_processing.gui.popups.multi_choice_popup import confirm_prompt
from oregon_processing.gui.popups.warning_popup import show_warning_popup
from oregon_processing.util.directory_names import directory_names
from oregon_processing.util.file_names import file_names


class Project:
    def __init__(self, project_dir: Path = None):

        self._project_json_file = None

        # parameters loaded from project JSON file
        self._software_version: str = None # software version of Oregon used to create the project
        self._project_name: str = None

        if project_dir is None:
            try:
                project_dir = browse_directory(title="Select Oregon project directory")
            except NoFileSelectedError:
                    error_message = "Project loading cancelled by user during directory selection."
                    LOGGER.info(error_message)
                    raise NoFileSelectedError(error_message)

        # directories
        self._project_dir: Path = project_dir
        self._archive_dir: Path = project_dir / directory_names.archive_dir_name
        self._logs_dir: Path = project_dir / directory_names.logs_dir_name
        self._crash_logs_dir: Path = self._logs_dir / directory_names.crash_log_dir_name
        self._export_dir: Path = project_dir / directory_names.export_dir_name
        self._detection_record_export_dir: Path = self._export_dir / directory_names.detection_record_export_dir_name

        self._project_json_file: Path = project_dir / file_names.oregon_project_json_file_name

        self._validate_project_directory()
        self._load_project_parameters()

        if self._software_version != oregon_processing.__version__:
            LOGGER.warning(f"Project was created with a different version of Oregon (project software version: {self._software_version}, current software version: {oregon_processing.__version__}).")

    @property
    def project_dir(self) -> Path:
        return self._project_dir

    @property
    def software_version(self) -> str:
        return self._software_version

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def archive_dir(self) -> Path:
        return self._archive_dir

    @property
    def logs_dir(self) -> Path:
        return self._logs_dir

    @property
    def crash_logs_dir(self) -> Path:
        return self._crash_logs_dir

    @property
    def export_dir(self) -> Path:
        return self._export_dir

    @property
    def detection_record_export_dir(self) -> Path:
        return self._detection_record_export_dir

    @classmethod
    def create_new_project(cls):


        try:
            answer = confirm_prompt(message="Do you want to create a new Oregon project?")
            if not answer:
                raise UserCancelledError
        except UserCancelledError:
            raise UserCancelledError("Project creation cancelled by user during initial confirmation prompt.")


        # prompt user to select dir to save project file
        while True:
            try:
                project_parent_dir = browse_directory(title="Select directory to save new Oregon project")
            except NoFileSelectedError:
                raise UserCancelledError("Project creation cancelled by user during directory selection.")

            project_parameters = cls.prompt_project_parameters()
            message = "Creating new Oregon project with the following parameters:"
            for key, value in project_parameters.items():
                message += f"\n\t- {key}: {value}"
            LOGGER.info(message)

            # Create new directory for project files
            project_name_safe = "".join(c for c in project_parameters["project_name"] if c.isalnum() or c in (' ', '_', '-')).rstrip()
            project_dir = project_parent_dir / project_name_safe

            # if project JSON file already exists in selected directory, exit with an error to avoid overwriting existing project
            if project_dir.exists():
                warning_message = f"A directory for the project already exists at:\n{project_dir}\n\nPlease select a different directory."
                show_warning_popup(warning_message, title="Project Directory Already Exists")
                LOGGER.warning(warning_message)
                continue

            break

        cls._create_project_structure(project_dir, project_parameters)

        LOGGER.info("Project creation complete.")

    @classmethod
    def prompt_project_parameters(cls):

        project_name = name_prompt(message="Project name:", title="Enter a name for this Oregon project", allow_numbers=True)

        # get version from current Oregon installation
        software_version = oregon_processing.__version__

        return {
            "project_name": project_name,
            "software_version": software_version
        }

    @classmethod
    def _create_project_structure(cls, project_dir: Path, project_parameters: dict) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Created project directory at: {project_dir}")

        project_json_file = project_dir / file_names.oregon_project_json_file_name
        project_json_file.touch(exist_ok=True)

        with open(project_json_file, 'w') as f:
            json.dump(project_parameters, f, indent=4)
        LOGGER.info(f"Created project JSON file at: {project_json_file}")

        archive_dir = project_dir / directory_names.archive_dir_name
        logs_dir = project_dir / directory_names.logs_dir_name
        export_dir = project_dir / directory_names.export_dir_name
        detection_record_export_dir = export_dir / directory_names.detection_record_export_dir_name

        create_dirs = [archive_dir, logs_dir, export_dir, detection_record_export_dir]
        for dir in create_dirs:
            dir.mkdir(exist_ok=True)
            LOGGER.info(f"Created directory at: {dir}")

    def _validate_project_directory(self) -> bool:
        """
        Validates that the given directory contains the expected structure for an Oregon project.
        Checks for the presence of the project JSON file and the required subdirectories.
        """
        expected_json_file = self._project_json_file
        expected_dirs = [
            self._archive_dir,
            self._logs_dir,
            self._export_dir,
            self._detection_record_export_dir,
        ]

        if not expected_json_file.is_file():
            error_message = f"Project JSON file not found at expected location: {expected_json_file}"
            LOGGER.error(error_message)
            raise InvalidProjectDirectoryError(error_message)

        for dir in expected_dirs:
            if not dir.is_dir():
                error_message = f"Expected directory not found: {dir}"
                LOGGER.error(error_message)
                raise InvalidProjectDirectoryError(error_message)

        LOGGER.debug("Project directory validation complete.")
        return True

    def _load_project_parameters(self):
        """
        Loads project parameters from the project JSON file and stores them in instance variables.
        Raises an error if the file cannot be read or if required parameters are missing.
        """
        try:
            with open(self._project_json_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            LOGGER.error(f"Failed to read project JSON file: {e}")
            raise RuntimeError(f"Failed to read project JSON file: {e}")

        self._software_version = self._load_project_parameter(data, "software_version", str)
        self._project_name = self._load_project_parameter(data, "project_name", str)

    def _load_project_parameter(self, data, parameter_name, expected_type):
        """
        Helper method to load a single parameter from the project JSON data with type checking.
        Raises an error if the parameter is missing or if it has the wrong type.
        """
        if parameter_name not in data:
            LOGGER.error(f"Missing required parameter in project JSON file: {parameter_name}")
            raise InvalidProjectDirectoryError(f"Missing required parameter in project JSON file: {parameter_name}")

        value = data[parameter_name]
        try:
            value = expected_type(value)
        except (ValueError, TypeError) as e:
            error_message = f"Invalid type for parameter '{parameter_name}' in project JSON file. Cannot convert value '{value}' to {expected_type.__name__}: {e}"
            LOGGER.error(error_message)
            raise InvalidProjectDirectoryError(error_message)

        return value

CACHED_PROJECT: Project = None
def get_project() -> Project:
    global CACHED_PROJECT
    if CACHED_PROJECT is None:
        error_msg = "Project has not been initialized. Run set_project() first."
        LOGGER.error(error_msg)
        raise RuntimeError(error_msg)
    return CACHED_PROJECT

def set_project(project: Project):
    global CACHED_PROJECT
    CACHED_PROJECT = project
    LOGGER.debug(f"Project set: {project._project_name}")


def open_previous_project() -> Project:
    """
    Initialize, cache, and persist the active project using OregonConfig.

    If a last-used project path exists, prompts whether to reuse it.
    """
    config = OregonConfig()

    last_project_dir = config.last_project_dir
    if last_project_dir:
        try:
            answer = confirm_prompt(
                message=f"Last project directory found: {last_project_dir}\n\nDo you want to reuse this project (Confirm) or select a different project (Cancel)?",
                window_height=200,
                window_width=450
            )
        except (UserCancelledError, NoFileSelectedError):
            message = "Project directory selection cancelled by user. Aborting export protocol."
            LOGGER.info(message)
            print(f"\n\n{message}\n\n")
            raise UserCancelledError(message)

        if not answer:
            last_project_dir = None

    project = Project(project_dir=last_project_dir)
    set_project(project)
    config.last_project_dir = project.project_dir
    return project