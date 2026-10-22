
from tkinter import filedialog
from pathlib import Path

from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.root import get_root

def browse_file(title="Select Excel file", accepted_file_types=[("Excel files", "*.xlsx *.xls")]) -> Path:
    """
    Open a file dialog for the user to select an Excel file.
    Returns the selected file path as a Path object, or raises if cancelled or error occurs.
    """
    root = get_root()
    try:
        root.withdraw()
        root.lift()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=accepted_file_types
        )
        if not file_path:
            raise UserCancelledError("No input file selected.")

        return Path(file_path)
    except UserCancelledError:
        raise
    except Exception as e:
        raise UserCancelledError(f"Error opening file dialog: {e}")

def browse_directory(title="Select Directory") -> Path:
    """
    Open a directory dialog for the user to select a directory.
    Returns the selected directory path as a Path object, or raises if cancelled or error occurs.
    """
    root = get_root()
    try:
        root.withdraw()
        root.lift()
        root.attributes('-topmost', True)
        dir_path = filedialog.askdirectory(title=title)

        if not dir_path:
            raise UserCancelledError("No directory selected.")

        return Path(dir_path)
    except UserCancelledError:
        raise
    except Exception as e:
        raise UserCancelledError(f"Error opening directory dialog: {e}")
