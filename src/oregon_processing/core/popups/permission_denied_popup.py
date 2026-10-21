import tkinter as tk
import time
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class PermissionDeniedMainPrompt(Popup):

    def __init__(self, parent, file_path: Path, window_width: int = 500, window_height: int = 250):
        super().__init__(parent, title=f"Access Denied - {file_path.name}", window_width=window_width, window_height=window_height)

        self._window_height = window_height
        self._window_width = window_width
        self.file_path = file_path

        self._build()

    def _build(self):

        font = NMBUPromptFont.get(size=12)
        message = (f"Access to the Excel file was denied, likely because it is open in another program. Please close the file and retry.\n\n"
                   f"File: {self.file_path.name}\n\n")
        self.prompt_frame = self._build_prompt_section(
            row=0,
            text=message,
            text_font=font,
            pady=(20, 0),
            anchor="center",
            justify="center"
        )

        self._build_button_section(row = 1, button_defs=[
            ("Retry", self._on_retry),
            ("Abort", self._on_abort)
            ],
            pady=(0,15)
            )

    def _on_retry(self):
        self.result = "retry"
        self.destroy()

    def _on_abort(self):
        self.result = "abort"
        self.destroy()

def handle_permission_denied(file_path: Path, window_width: int = 500, window_height: int = 250) -> str:
    root = tk.Tk()
    root.withdraw()
    while True:
        main_prompt = PermissionDeniedMainPrompt(root, file_path, window_width=window_width, window_height=window_height)
        main_prompt.wait_window()
        choice = main_prompt.result
        if choice == "retry":
            root.destroy()
            return "retry"
        elif choice == "abort":
            root.destroy()
            raise UserCancelledError("User aborted due to permission denied error.")
        elif choice is None:
            root.destroy()
            raise UserCancelledError("User closed the permission denied prompt without making a choice.")
        else:
            root.destroy()
            raise ValueError("Invalid choice from main dialog")

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        action = handle_permission_denied(file_to_test, window_width=500, window_height=200)
        print(f"User chose to: {action}")
    except UserCancelledError as e:
        print(f"User aborted action: {e}")