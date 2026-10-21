from dataclasses import dataclass, field

from oregon_processing.util.communication import ConnectionSession, DeviceCommand
from oregon_processing.exceptions import UnexpectedResponseError
from oregon_processing.util.logging_manager import get_logger
from oregon_processing.util.system_status import SystemStatusChecker
LOGGER = get_logger(__name__)

from oregon_processing.util.device_mode_manager import DeviceMode, change_mode, get_current_mode


@dataclass
class UploadRecord:
    """Data class representing a single upload record."""
    num: int
    date: str
    time: str
    records: int


@dataclass
class UploadHistory:
    """Manages upload history for processed data."""

    reader_name: str = ""
    site: str = ""
    upload_count: int = 0
    uploads: list[UploadRecord] = field(default_factory=list)
    new_records: int = 0
    total_records: int = 0
    raw_output: str = ""

def get_upload_history(session: ConnectionSession, system_status_checker: SystemStatusChecker) -> UploadHistory:
    """
    Parse upload history output from UH command.

    Returns
    -------
    UploadHistory
    """
    old_mode = get_current_mode(system_status_checker)
    if old_mode.lower() != DeviceMode.STANDBY.value.lower():
        change_mode(session, system_status_checker, DeviceMode.STANDBY)

    try:
        upload_history_lines = session.send_command(DeviceCommand.UH)
    finally:
        if old_mode.lower() != DeviceMode.STANDBY.value.lower():
            change_mode(session, system_status_checker, old_mode)

    upload_history: UploadHistory = UploadHistory()
    upload_history.raw_output = "\n".join(upload_history_lines)

    for i, line in enumerate(upload_history_lines):
        line = line.strip()
        line_lower = line.lower()

        # Parse header line: "Reader: <name>  Site: <site>"
        if line_lower.startswith('reader:'):
            parts = line_lower.split('site:')
            if len(parts) == 2:
                reader_part = parts[0].replace('reader:', '').strip()
                site_part = parts[1].strip()
                upload_history.reader_name = reader_part
                upload_history.site = site_part

        # Parse upload histories count
        elif 'upload histories:' in line_lower:
            parts = line_lower.split('upload histories:')
            if len(parts) == 2:
                try:
                    upload_history.upload_count = int(parts[1].strip())
                except ValueError:
                    error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                    LOGGER.error(error_message)
                    raise UnexpectedResponseError(error_message)

        # Skip header row (Num   UP Date    Time    Records)
        elif line_lower.startswith('num') and 'date' in line_lower and 'time' in line_lower and 'records' in line_lower:
            continue

        # Parse upload record lines (numbered entries)
        # EXAMPLE: 1  2019-06-29 07:05:35      109
        elif line and line[0].isdigit():
            parts = line.split()
            if len(parts) >= 4:
                try:
                    upload_record = UploadRecord(
                        num=int(parts[0]),
                        date=parts[1],
                        time=parts[2],
                        records=int(parts[3])
                    )
                    upload_history.uploads.append(upload_record)
                except (ValueError, IndexError):
                    error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                    LOGGER.error(error_message)
                    raise UnexpectedResponseError(error_message)

        # Parse NEW records line
        # EXAMPLE: NEW 11
        elif line.startswith('NEW'):
            parts = line.split()
            try:
                if len(parts) != 2:
                    raise IndexError

                upload_history.new_records = int(parts[-1])
            except (ValueError, IndexError):
                error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                LOGGER.error(error_message)
                raise UnexpectedResponseError(error_message)

        # Parse Total line
        elif line.startswith('Total'):
            parts = line.split()
            try:
                if len(parts) != 2:
                    raise IndexError
                upload_history.total_records = int(parts[-1])
            except (ValueError, IndexError):
                error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
                LOGGER.error(error_message)
                raise UnexpectedResponseError(error_message)

        else:
            error_message = f"Unrecognized line format in upload history at row {i + 1}: '{line}'"
            LOGGER.error(error_message)
            raise UnexpectedResponseError(error_message)

    return upload_history