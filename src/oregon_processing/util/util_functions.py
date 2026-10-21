import re
from datetime import date

from oregon_processing.util.logging_manager import get_logger

LOGGER = get_logger(__name__)

def extract_filename_date(filename: str) -> date:
    """
    Extract date from filename in format: *_YYYY_MM_DD.ext

    Parameters
    ----------
    filename : str
        The filename to extract date from

    Returns
    -------
    date
        The extracted date object
    """
    # Pattern to match _YYYY_MM_DD before file extension
    pattern = r'_(\d{4})_(\d{2})_(\d{2})\.\w+$'

    match = re.search(pattern, filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        try:
            return date(year, month, day)
        except ValueError:
            error_message = f"Date components extracted from filename are not valid: {year}-{month}-{day}"
            LOGGER.error(error_message)
            raise ValueError(error_message)
    else:
        error_message = f"Filename does not contain a valid date in the expected format: {filename}"
        LOGGER.error(error_message)
        raise ValueError(error_message)