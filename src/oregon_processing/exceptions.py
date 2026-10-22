
class InvalidConfigError(Exception):
    """Raised when configuration file is invalid or cannot be parsed."""
    pass

class ConnectionFailedError(Exception):
    """Raised when a connection to a required service fails."""
    pass

class UnexpectedResponseError(Exception):
    """Raised when an unexpected response is received from a service."""
    pass

class CommandTransmissionError(Exception):
    """Raised when a command fails to be transmitted to a PIT reader."""
    pass

class UserCancelledError(Exception):
    """Raised when the user aborts an operation."""
    pass

class DeviceHealthError(Exception):
    """Error for when device health check fails or device clock is not in sync."""
    pass

class ClockSyncError(Exception):
    """Raised when device clock is not synchronized within acceptable tolerance."""
    pass

class ModeChangeError(Exception):
    """Raised when a device mode change fails."""
    pass

class FormatChangeError(Exception):
    """Raised when a detection record format change fails."""
    pass

class NoFileSelectedError(Exception):
    """Raised when no file is selected."""
    pass

class InvalidProjectDirectoryError(Exception):
    """Raised when the project directory is invalid."""
    pass

class ExportFailedError(Exception):
    """Raised when exporting detection records fails."""
    pass