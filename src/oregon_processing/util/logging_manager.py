import inspect
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re
from typing import Any



@dataclass(frozen=True)
class LogEvent:
    """
    Represents a single log event with level, timestamp, process, and message.
    Used for in-memory storage of warnings and errors.
    """
    level: str
    levelno: int
    timestamp: str
    process_name: str
    message: str

class WarningMemoryHandler(logging.Handler):
    """
    Custom logging handler that stores WARNING, ERROR, and CRITICAL log events in memory.
    Useful for generating summaries or programmatic access to important log messages.
    """
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self._events: dict[str, list[LogEvent]] = {
            "WARNING": [],
            "ERROR": [],
            "CRITICAL": [],
        }

    @property
    def events(self) -> dict[str, list[LogEvent]]:
        """Returns all stored log events by level."""
        return self._events

    def emit(self, record: logging.LogRecord) -> None:
        # Ignore summary-generated records to avoid recursion
        if getattr(record, "_from_summary", False):
            return

        if record.levelno < logging.WARNING:
            return

        level_name = record.levelname if record.levelname in self._events else "CRITICAL"
        process_name = getattr(record, "source_process", record.name)
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        self._events[level_name].append(
            LogEvent(
                level=record.levelname,
                levelno=record.levelno,
                timestamp=timestamp,
                process_name=process_name,
                message=record.getMessage(),
            )
        )

class SourceProcessAutoFilter(logging.Filter):
    """
    Logging filter that automatically injects the calling function or method name as 'source_process' into log records.
    Works for both functions and class methods.
    """
    def __init__(self, logger_module_name: str = None):
        super().__init__()
        self._logger_module_name = logger_module_name

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "source_process"):
            # Determine the module name to search for
            module_name = self._logger_module_name
            if module_name is None:
                # Try to infer from the logger name
                module_name = getattr(record, "name", None)
            # Walk up the stack to find the first frame matching the logger's module name
            frame = inspect.currentframe()
            found = False
            while frame:
                code = frame.f_code
                frame_module = frame.f_globals.get("__name__", "")
                # Exclude frames from this filter class itself
                if frame_module == __name__ and code.co_name == "filter":
                    frame = frame.f_back
                    continue
                # Stop at the first frame matching the logger's module
                if module_name and frame_module == module_name:
                    func_name = code.co_name
                    if "self" in frame.f_locals:
                        cls_name = type(frame.f_locals["self"]).__name__
                        record.source_process = f"{cls_name}.{func_name}"
                    elif "cls" in frame.f_locals:
                        cls_name = frame.f_locals["cls"].__name__
                        record.source_process = f"{cls_name}.{func_name}"
                    else:
                        record.source_process = func_name
                    found = True
                    break
                frame = frame.f_back
            if not found:
                # Fallback: use the function name of the first non-logging frame
                frame = inspect.currentframe()
                while frame:
                    code = frame.f_code
                    frame_module = frame.f_globals.get("__name__", "")
                    if not frame_module.startswith("logging") and not (frame_module == __name__ and code.co_name == "filter"):
                        func_name = code.co_name
                        if "self" in frame.f_locals:
                            cls_name = type(frame.f_locals["self"]).__name__
                            record.source_process = f"{cls_name}.{func_name}"
                        elif "cls" in frame.f_locals:
                            cls_name = frame.f_locals["cls"].__name__
                            record.source_process = f"{cls_name}.{func_name}"
                        else:
                            record.source_process = func_name
                        break
                    frame = frame.f_back
        return True

class RelativePathMessageFilter(logging.Filter):
    """
    Shortens absolute path strings in log messages by replacing known base paths with aliases.
    Useful for making logs more readable and portable.
    """
    def __init__(self, relative_base_paths: dict[str, Path]) -> None:
        super().__init__()
        self._compiled_patterns: list[tuple[re.Pattern[str], str]] = []

        for alias, base_path in relative_base_paths.items():
            resolved_base = str(Path(base_path).resolve())
            normalized_alias = alias.rstrip("/\\")

            if not normalized_alias:
                continue

            for candidate in {resolved_base, resolved_base.replace("\\", "/")}:
                pattern = re.compile(re.escape(candidate), flags=re.IGNORECASE)
                self._compiled_patterns.append((pattern, normalized_alias))

    def filter(self, record: logging.LogRecord) -> bool:
        # Optionally skip this filter for certain records
        if getattr(record, "_skip_path_alias_filter", False):
            return True

        if not self._compiled_patterns:
            return True

        message = record.getMessage()
        shortened_message = message

        for pattern, alias in self._compiled_patterns:
            shortened_message = pattern.sub(f"<{alias}>", shortened_message)

        if shortened_message != message:
            record.msg = shortened_message
            record.args = ()

        return True

class ClearFormatAwareFormatter(logging.Formatter):
    """
    Formatter that can output a log message with no formatting if the '_clear_format' attribute is set.
    Used for summary blocks or blank lines in logs.
    """
    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "_clear_format", False):
            # If message is empty, output a blank line; else output message as-is, no formatting
            msg = record.getMessage()
            return msg if msg.strip() else ""
        return super().format(record)

class LoggingManager:
    """
    Context manager for setting up and tearing down logging for an application or process.
    Handles console and file logging, in-memory warning/error storage, and log formatting.
    Provides a summary of warnings and errors at exit.
    """
    def __init__(
        self,
        write_to_console: bool = True,
        write_to_report_file: bool = True,
        report_file: Path | str | None = None,
        relative_base_paths: dict[str, Path | str] | None = None,
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
    ):
        """
        Initialize the LoggingManager.

        Args:
            write_to_console: If True, log to console.
            write_to_report_file: If True, log to a file.
            report_file: Path to the log file (required if write_to_report_file is True).
            relative_base_paths: Mapping of path aliases for shortening paths in log messages.
            console_level: Logging level for the console handler.
            file_level: Logging level for the file handler.
        """
        self._write_to_console = write_to_console
        self._write_to_report_file = write_to_report_file
        self._report_file = Path(report_file) if report_file is not None else None
        self._relative_base_paths = {alias: Path(base_path).resolve()for alias, base_path in (relative_base_paths or {}).items()}
        self._console_level = console_level
        self._file_level = file_level

        if self._write_to_report_file and self._report_file is None:
            raise ValueError("report_file must be provided when write_to_report_file is True.")

        self._console_handler: logging.Handler | None = None
        self._file_handler: logging.Handler | None = None
        self._memory_handler = WarningMemoryHandler()
        self._relative_path_filter = RelativePathMessageFilter(self._relative_base_paths)

        self._console_formatter = ClearFormatAwareFormatter("%(levelname)s[%(source_process)s]: %(message)s")
        self._file_formatter = ClearFormatAwareFormatter("%(levelname)s[%(asctime)s][%(source_process)s]: %(message)s",datefmt="%Y-%m-%d %H:%M:%S")


        self._root_logger = None

    def __enter__(self) -> logging.Logger:
        """
        Set up logging handlers and return the logger for use in a with-statement.
        """
        try:
            self._setup_handlers()
            LOGGER.debug("LoggingManager initialized with console_level=%s, file_level=%s, report_file=%s", self._console_level, self._file_level, self._report_file)
        except Exception as e:
            self._write_summary()
            self._teardown_handlers()
            raise RuntimeError(f"Failed to set up logging handlers: {e}")

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Write a summary of warnings/errors and clean up all handlers on exit.
        """
        self._write_summary()
        self._teardown_handlers()

    @property
    def warning_and_above_logs(self) -> dict[str, list[LogEvent]]:
        """Returns all WARNING, ERROR, and CRITICAL log events captured in memory."""
        return self._memory_handler.events

    @property
    def report_file(self) -> Path:
        """Get the current report file path. Raises if file logging is not enabled."""
        if not self._write_to_report_file:
            error_message = f"File logging is not enabled, no report file available."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        return self._report_file

    def transfer_log_file(self, new_report_file: Path | str) -> None:
        """
        Transfer the current log file to a new location. Useful for moving logs after creation.
        If the new_report_file already exists, it will be overwritten.
        """
        if not self._write_to_report_file:
            error_message = f"File logging is not enabled, cannot transfer log file."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if self._report_file is None:
            error_message = f"Current report file path is not set, cannot transfer log file."
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if self._file_handler:
            self._file_handler.flush()
            self._file_handler.close()
            self._file_handler = None
            self._root_logger.removeHandler(self._file_handler)

        try:
            # Use rename for atomic move if on the same filesystem
            self._report_file.rename(new_report_file)

            # Recreate the file handler with the new report file path
            self._setup_file_handler(new_report_file)

            # Update the internal report file reference to the new location
            self._report_file = new_report_file

            LOGGER.debug(f"Log file transferred to {new_report_file}", extra={"_skip_path_alias_filter": True})

        except Exception as e:
            error_message = f"Failed to transfer log file to {new_report_file}: {e}"
            LOGGER.error(error_message)
            raise RuntimeError(error_message) from e

    def _setup_handlers(self) -> None:
        """
        Set up all logging handlers (console, file, memory) and filters/formatters on the root logger.
        """
        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(logging.NOTSET) # Pass all logs to handlers and let handlers filter by level
        self._root_logger.filters.clear()
        self._root_logger.handlers.clear()

        # Add console handler if enabled
        if self._write_to_console:
            self._setup_console_handler()

        # Add file handler if enabled
        if self._write_to_report_file:
            if self._report_file is None:
                error_message = "Report_file must be provided when write_to_report_file is True."
                LOGGER.error(error_message)
                raise ValueError(error_message)

            self._report_file.parent.mkdir(parents=True, exist_ok=True)

            self._setup_file_handler(self._report_file)

        # Memory handler is always set up to capture warnings and above for summary generation
        self._setup_memory_handler()

    def _teardown_handlers(self) -> None:
        """
        Remove and close all handlers and clear filters from the root logger.
        """

        if not self._root_logger:
            return

        for handler in list(self._root_logger.handlers):
            handler.flush()
            handler.close()
            self._root_logger.removeHandler(handler)

        self._console_handler = None
        self._file_handler = None
        self._memory_handler = None

    def _write_summary(self) -> None:
        """
        Write a summary of all WARNING, ERROR, and CRITICAL log events at the end of logging.
        Outputs a count and indented list of all such events.
        """
        if not self._memory_handler:
            return

        warning_count = len(self._memory_handler.events["WARNING"])
        error_count = len(self._memory_handler.events["ERROR"])
        critical_count = len(self._memory_handler.events["CRITICAL"])
        total = warning_count + error_count + critical_count

        # Write a clear, unformatted separator line before the summary block
        LOGGER.info("", extra={"_clear_format": True})

        if total == 0:
            LOGGER.info(
                "No WARNING, ERROR, or CRITICAL logs recorded.",
                extra={"_from_summary": True},
            )
            # add two empty lines after the summary for better separation in the logs
            LOGGER.info("", extra={"_clear_format": True})
            return

        LOGGER.info(
            f"WARNING={warning_count}, ERROR={error_count}, CRITICAL={critical_count}",
            extra={"_from_summary": True},
        )

        # Indent the entire summary block as a sub-list, including level and source_process
        indent = "        "
        bullet_point = "• "
        original_console_formatter = self._console_handler.formatter if self._console_handler else None
        original_file_formatter = self._file_handler.formatter if self._file_handler else None
        indented_console_formatter = ClearFormatAwareFormatter(indent + bullet_point + "%(levelname)s[%(source_process)s]: %(message)s")
        indented_file_formatter = ClearFormatAwareFormatter(indent + bullet_point + "%(levelname)s[%(asctime)s][%(source_process)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        # Temporarily set indented formatters
        if self._console_handler:
            self._console_handler.setFormatter(indented_console_formatter)
        if self._file_handler:
            self._file_handler.setFormatter(indented_file_formatter)

        try:
            for level in ("WARNING", "ERROR", "CRITICAL"):
                for event in self._memory_handler.events[level]:
                    summary_message = event.message.replace("\n", f"\n{indent}")
                    LOGGER.log(
                        event.levelno,
                        summary_message,
                        extra={"_from_summary": True},
                    )

            # add two empty lines after the summary for better separation in the logs
            LOGGER.info("", extra={"_clear_format": True})

        finally:
            # Restore original formatters
            if self._console_handler and original_console_formatter:
                self._console_handler.setFormatter(original_console_formatter)
            if self._file_handler and original_file_formatter:
                self._file_handler.setFormatter(original_file_formatter)

    def _setup_file_handler(self, report_file: Path | str) -> None:
        self._file_handler = logging.FileHandler(report_file, encoding="utf-8")
        self._file_handler.setLevel(self._file_level)
        self._file_handler.setFormatter(self._file_formatter)
        self._file_handler.addFilter(self._relative_path_filter)
        self._root_logger.addHandler(self._file_handler)

    def _setup_console_handler(self) -> None:
        self._console_handler = logging.StreamHandler()
        self._console_handler.setLevel(self._console_level)
        self._console_handler.setFormatter(self._console_formatter)
        self._console_handler.addFilter(self._relative_path_filter)
        self._root_logger.addHandler(self._console_handler)

    def _setup_memory_handler(self) -> None:
        self._memory_handler.setLevel(logging.WARNING)
        self._memory_handler.addFilter(self._relative_path_filter)
        self._root_logger.addHandler(self._memory_handler)

        self._root_logger.filters.clear()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger by name and ensure SourceProcessAutoFilter is attached.
    name is typically __name__ of the module requesting the logger, but can be any string to identify the logger's context.
    """

    logger = logging.getLogger(name)

    # Attach SourceProcessAutoFilter with the logger's module name if not already present
    has_filter = any(isinstance(f, SourceProcessAutoFilter) for f in getattr(logger, 'filters', []))
    if not has_filter:
        logger.addFilter(SourceProcessAutoFilter(logger_module_name=name))
    return logger


LOGGER = get_logger(__name__)
