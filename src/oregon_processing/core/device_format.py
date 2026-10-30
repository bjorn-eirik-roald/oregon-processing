from oregon_processing.util.logging_manager import get_logger
LOGGER = get_logger(__name__)

from dataclasses import dataclass

from oregon_processing.core.communication import ConnectionSession, DeviceCommand
from oregon_processing.core.device_mode import DeviceMode, change_mode, get_current_mode
from oregon_processing.exceptions import FormatChangeError, UnexpectedResponseError

FORMAT_FIELD_NAMES = {
    'DTY': 'Detection type',
    'TCH': 'Tag technology',
    'TTY': 'Tag type',
    'PFG': 'Phantom flag',
    'TAG': 'Tag ID number',
    'ANT': 'Antenna number',
    'ARR': 'Arrival date and time',
    'TRF': 'Time reference',
    'DEP': 'Departure date and time',
    'NCD': 'Number of consecutive detections',
    'EMP': 'Number of empty scans preceding detection',
    'LAT': 'Latitude',
    'LON': 'Longitude',
    'ALT': 'Altitude in meters',
    'SIV': 'Satellites in view',
    'HDP': 'Location horizontal accuracy',
    'TSS': 'Tag signal strength',
    'SPV': 'Power supply voltage',
    'CPA': 'Power supply amperage during charge pulse',
    'LSA': 'Power supply amperage with charge pulse off',
    'EFA': 'Effective amps',
    'CPT': 'Charge pulse time in milliseconds',
    'LST': 'Listen time in milliseconds',
    'ANV': 'Antenna voltage',
    'ANA': 'Antenna amperage',
    'NOI': 'Noise',
    'DUR': 'Duration of tag detection event',
    'CLS': 'Tag size class',
    'SCD': 'Site code',
    'SPC': 'Output one space character',
    }

@dataclass(frozen=True)
class FormatInfo:
    """Parsed detection record format metadata returned from FM."""

    columns_raw: str
    columns: list[str]
    column_indices: dict[str, int]
    field_names: dict[str, str]



def get_format_info(session: ConnectionSession) -> FormatInfo:
    """
    Fetch and parse the detection record format from the device using the FM command.

    Returns
    -------
    FormatInfo
        Parsed format metadata including raw format, column list,
        and index lookup map.
    """

    old_mode = None
    mode = get_current_mode(session)
    if mode.lower() != 'standby':
        old_mode = mode
        change_mode(session, DeviceMode.STANDBY)

    response_lines = session.send_command(DeviceCommand.FM)

    if old_mode:
        change_mode(session, old_mode)

    if len(response_lines) != 1:
        error_message = f"Unexpected number of lines in FM response: {len(response_lines)}. Response: {response_lines}"
        LOGGER.error(error_message)
        raise UnexpectedResponseError(error_message)

    columns_raw = response_lines[0].strip()
    tokens = columns_raw.split()
    columns = [t for t in tokens if t != 'SPC']

    # Create a dictionary mapping column names to their indices
    column_indices = {col: idx for idx, col in enumerate(columns)}

    field_names = {col: FORMAT_FIELD_NAMES.get(col, "Unknown") for col in columns}

    return FormatInfo(
        columns_raw=columns_raw,
        columns=columns,
        column_indices=column_indices,
        field_names=field_names,
    )

def set_detection_record_format(session: ConnectionSession, format_string: str) -> bool:
    """
    Set the detection record format on the device using the FM command.

    Parameters
    ----------
    session : ConnectionSession
        The connection session to communicate with the device.
    format_string : str
        The format string to set (e.g., "DTY ARR SPC TRF DUR SPC TTY SPC TAG SCD NCD EFA")

    Returns
    -------
    bool
        True if format was set successfully, raises FormatChangeError otherwise.
    """
    try:
        if any(field_name not in FORMAT_FIELD_NAMES for field_name in format_string.split()):
            unknown_cols = [field_name for field_name in format_string.split() if field_name not in FORMAT_FIELD_NAMES]
            error_message = f"Unknown columns in detection record format: {unknown_cols}"
            raise FormatChangeError(f"Unknown columns in detection record format user is trying to set: {unknown_cols}")

        session.send_command(DeviceCommand.FM, format_string)

        # Verify the format was set and update cache
        detection_record_format: FormatInfo = get_format_info(session)

        if detection_record_format.columns_raw == format_string:
            LOGGER.info(f"Detection record format set successfully to '{format_string}'")
            return True
        else:
            raise FormatChangeError(f"Detection record format change failed. Expected '{format_string}', got '{detection_record_format.columns_raw}'")
    except FormatChangeError as e:
        LOGGER.error(str(e))
        raise
    except Exception:
        error_message = f"Error setting detection record format to '{format_string}'"
        LOGGER.error(error_message)
        raise
