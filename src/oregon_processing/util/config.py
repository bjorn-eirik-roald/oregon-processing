
import json
import os
from pathlib import Path

from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from oregon_processing.util.exceptions import ConfigNotFoundError, InvalidConfigError

class OregonConfig:
    """
    Basic config for storing last used project directory and other potential settings in the future.
    """
    CONFIG_FILE_NAME = "oregon_config.json"
    APP_DIR_PARTS = ("oregon_processing",)


    def __init__(self):
        self._config_file_path = self.get_config_file_path()
        self._last_project_dir = None

        self._load_and_validate()

    @property
    def last_project_dir(self) -> Path:
        """Returns the last project directory used, or None if not set."""
        return self._last_project_dir

    @last_project_dir.setter
    def last_project_dir(self, value: Path):
        """Sets the last project directory used."""
        if not isinstance(value, Path):
            raise ValueError("last_project_dir can only be set to a Path object.")
        self._last_project_dir = value

        data = {"last_project_dir": str(value) if value is not None else None}
        with open(self._config_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def get_config_dir(cls) -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata).joinpath(*cls.APP_DIR_PARTS)
        fallback = Path.home() / "AppData" / "Roaming"
        return fallback.joinpath(*cls.APP_DIR_PARTS)

    @classmethod
    def get_config_file_path(cls) -> Path:
        return cls.get_config_dir() / cls.CONFIG_FILE_NAME

    @classmethod
    def create_default_config(cls):
        """Creates a default config file with None values."""
        config_file = cls.get_config_file_path()
        config_file.parent.mkdir(parents=True, exist_ok=True)

        default_data = {"last_project_dir": None}

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)

        return cls()

    def _load_and_validate(self) -> None:
        if not self._config_file_path.exists():
            raise ConfigNotFoundError(
                f"No config file found at '{self._config_file_path}'.\n"
                f"Run {self.__class__.__name__}.create_default_config() to create a config file before continuing."
            )

        with self._config_file_path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        self._validate_payload(payload)

        raw = payload.get("last_project_dir", None)
        if raw is not None:
            last_project_dir = Path(raw)
            if not last_project_dir.is_dir():
                LOGGER.warning(
                    f"Last project directory no longer exists: '{last_project_dir}'. Treating as unset."
                )
                last_project_dir = None
            self._last_project_dir = last_project_dir

    def _validate_payload(self, payload: dict) -> None:
        """Validate the config payload. Raises InvalidConfigError if the payload is malformed."""
        last_project_dir = payload.get("last_project_dir", None)

        if last_project_dir is not None:
            if not isinstance(last_project_dir, str):
                error_message = f"Invalid config: 'last_project_dir' must be a string or null, got {type(last_project_dir).__name__}."
                LOGGER.error(error_message)
                raise InvalidConfigError(error_message)
