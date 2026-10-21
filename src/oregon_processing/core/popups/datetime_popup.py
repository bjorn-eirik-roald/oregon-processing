import tkinter as tk
import datetime
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class DatetimeManualPopup(Popup):

    def __init__(self, parent, message, title="Enter datetime manually", window_width=500, window_height=100, date_only=False):
        super().__init__(parent, title=title, window_width=window_width, window_height=window_height)
        self._message = message
        self._date_only = date_only
        self._build()

    def _build(self):
        """
        Build the manual datetime entry popup UI by delegating to section helpers.
        """

        font = NMBUPromptFont.get(size=12)

        self.prompt_frame = self._build_prompt_section(
            row=0,
            text=self._message,
            text_font=font,
            pady=(20, 10),
            anchor="center",
            justify="center"
        )

        _, self._entry = self._build_entry_section(row=1, entry_width=30)
        _, self._error_label = self._build_entry_error_section(row=2)
        self._build_button_section(row=3, button_defs=[
            ("OK", self._on_ok),
            ("Cancel", self._on_close)
            ]
        )

        # Bind pressing enter to OK action and escape to cancel action
        self.bind('<Return>', lambda event: self._on_ok())
        self.bind('<Escape>', lambda event: self._on_close())

    def _on_ok(self):
        val = self._entry.get().strip()
        try:
            if self._date_only:
                dt = datetime.datetime.strptime(val, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                dt = datetime.datetime.strptime(val, "%Y-%m-%d %H:%M").replace(second=0, microsecond=0)
            self.result = dt
            self.destroy()
        except Exception:
            if self._date_only:
                self._error_label.config(text="Invalid format. Use YYYY-MM-DD.")
            else:
                self._error_label.config(text="Invalid format. Use YYYY-MM-DD HH:MM.")

class DatetimePopup(Popup):

    def __init__(self, parent, message, title="Enter datetime", window_width=500, window_height=100, date_only=False):
        """
        Build the main export datetime popup UI by delegating to section helpers.
        Uses centralized NMBU styles for all widgets.
        """
        super().__init__(parent, title=title, window_width=window_width, window_height=window_height)
        self._message = message
        self._date_only = date_only
        self._build()

    def _build(self):

        font = NMBUPromptFont.get(size=12)


        self.prompt_frame = self._build_prompt_section(
            row=0,
            text=self._message,
            text_font=font,
            pady=(20, 0),
            anchor="center",
            justify="center"
        )

        self._build_button_section(row=1, button_width=15, button_defs=[
            ("Use Current", self._on_use_current),
            ("Define Manually", self._on_define),
            ("Cancel", self._on_close)],
            pady=(20, 15)
        )

    def _on_use_current(self):
        self.result = "use_current"
        self.destroy()

    def _on_define(self):
        self.result = "define"
        self.destroy()

def prompt_file_export_datetime(input_filename: Path, title: str = "Enter export datetime", window_width: int = 500, window_height: int = 200, date_only=False) -> datetime.datetime:
    root = tk.Tk()
    root.withdraw()              # Hides the root window
    while True:


        if date_only:
            message = (f"Set export date for file.\n File: {input_filename}\n\n"
                       "Choose 'Use Current' to use current date, "
                       "or 'Define' to enter manually.")
        else:
            message = (f"Set export date and time for file.\n File: {input_filename}\n\n"
                       "Choose 'Use Current' to use current date and time, "
                       "or 'Define' to enter manually.")

        main_prompt = DatetimePopup(root, message=message, title=title, window_width=window_width, window_height=window_height, date_only=date_only)

        main_prompt.wait_window()
        choice = main_prompt.result

        if choice == "use_current":
            root.destroy()
            if date_only:
                return datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                return datetime.datetime.now()
        elif choice == "define":

            if date_only:
                message = f"Please enter the export date for the file ({input_filename}):\nFormat: YYYY-MM-DD"
            else:
                message = f"Please enter the export datetime for the file ({input_filename}):\nFormat: YYYY-MM-DD HH:MM"

            main_prompt.destroy()  # Close the main prompt before opening the manual entry
            manual_prompt = DatetimeManualPopup(root, message=message, title=title, window_width=window_width, window_height=window_height+50, date_only=date_only)
            manual_prompt.wait_window()
            if manual_prompt.result is not None:
                root.destroy()
                return manual_prompt.result
        elif choice is None:
            root.destroy()
            raise UserCancelledError("User cancelled export datetime selection.")
        else:
            root.destroy()
            raise ValueError("Invalid choice from datetime prompt.")

def prompt_datetime(message: str, title: str = "Enter datetime", window_width: int = 500, window_height: int = 200, date_only=False) -> datetime.datetime:
    root = tk.Tk()
    root.withdraw()              # Hides the root window

    while True:
        main_prompt = DatetimeManualPopup(root, message=message, title=title, window_width=window_width, window_height=window_height, date_only=date_only)

        main_prompt.wait_window()
        choice = main_prompt.result


        if choice is None:
            root.destroy()
            raise UserCancelledError("User cancelled export datetime selection.")
        else:
            root.destroy()
            return choice

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        dt = prompt_file_export_datetime(file_to_test, title="Select export datetime", window_width=500, window_height=200, date_only=True)
        print(f"User selected export datetime: {dt}")
    except UserCancelledError as e:
        print(f"User cancelled export datetime selection")

    try:
        dt = prompt_datetime(message="Please enter a datetime (YYYY-MM-DD)", title="Select datetime", window_width=500, window_height=200, date_only=True)
        print(f"User selected datetime: {dt}")
    except UserCancelledError as e:
        print(f"User cancelled datetime selection")