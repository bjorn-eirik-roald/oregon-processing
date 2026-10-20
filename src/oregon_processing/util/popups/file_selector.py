
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

from oregon_processing.exceptions import NoFileSelectedError

def browse_file(title="Select Excel file", accepted_file_types=[("Excel files", "*.xlsx *.xls")]) -> Path:
    """
    Open a file dialog for the user to select an Excel file.
    Returns the selected file path as a Path object, or raises if cancelled or error occurs.
    """
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=accepted_file_types
        )
        root.attributes('-topmost', False)
        if not file_path:
            raise NoFileSelectedError("No input file selected.")

        root.destroy()
        return Path(file_path)
    except NoFileSelectedError:
        raise
    except Exception as e:
        if root is not None:
            root.destroy()
        raise NoFileSelectedError(f"Error opening file dialog: {e}")

def browse_directory(title="Select Directory") -> Path:
    """
    Open a directory dialog for the user to select a directory.
    Returns the selected directory path as a Path object, or raises if cancelled or error occurs.
    """
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.lift()
        root.attributes('-topmost', True)
        dir_path = filedialog.askdirectory(title=title)
        root.attributes('-topmost', False)
        if not dir_path:
            root.destroy()
            raise NoFileSelectedError("No directory selected.")
        root.destroy()
        return Path(dir_path)
    except NoFileSelectedError:
        raise
    except Exception as e:
        if root is not None:
            root.destroy()
        raise NoFileSelectedError(f"Error opening directory dialog: {e}")


if __name__ == "__main__":
    try:
        file_path = browse_file()
        print(f"Selected file: {file_path}")
    except NoFileSelectedError as e:
        print(e)

    try:
        dir_path = browse_directory()
        print(f"Selected directory: {dir_path}")
    except NoFileSelectedError as e:
        print(e)