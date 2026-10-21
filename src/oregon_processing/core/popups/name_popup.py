import tkinter as tk
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class NamePopup(Popup):

    def __init__(self, parent, title, message, window_width=500, window_height=100, allow_numbers=False, default=None):
        super().__init__(parent, title=f"{title}", window_height=window_height, window_width=window_width)
        self._message = message
        self._window_width = window_width
        self._allow_numbers = allow_numbers
        self._window_height = window_height
        self._default = default

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

        _, self._entry = self._build_entry_section(row=1, entry_width=30, pady=(0,0))
        if self._default is not None:
            self._entry.insert(0, self._default)
        _, self._error_label = self._build_entry_error_section(row=2)
        self._build_button_section(row=3, button_defs=[
            ("OK", self._on_ok),
            ("Cancel", self._on_cancel)],
            pady=(0,10)
        )

        # Bind the Return key to trigger the OK button and Escape key to trigger the Cancel button
        self.bind("<Return>", lambda event: self._on_ok())
        self.bind("<Escape>", lambda event: self._on_cancel())

    def _on_ok(self):
        val = self._entry.get().strip()

        try:
            if self._allow_numbers:
                # If numbers are allowed, just check that the input is not empty
                if not val:
                    raise ValueError("Input cannot be empty.")
            else:
                # expect Human name Check that its not empty and does not contain digits or special characters except space and hyphen and period
                if not val or any(char.isdigit() or not char.isalnum() and char not in " -." for char in val):
                    raise ValueError("Invalid name. No digits or special characters allowed.")

            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))

    def _on_cancel(self):
        self.result = None
        self.destroy()

def prompt_name(title: str, message: str, window_width=600, window_height=150, allow_numbers=False, default=None) -> str:
    root = tk.Tk()
    root.withdraw()              # Hides the root window

    while True:
        main_prompt = NamePopup(root, title=title, message=message, window_width=window_width, window_height=window_height, allow_numbers=allow_numbers, default=default)
        main_prompt.wait_window()
        choice = main_prompt.result
        if choice:
            root.destroy()
            return choice
        else:
            root.destroy()
            raise UserCancelledError("User cancelled the name entry prompt.")

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        name = prompt_name(title="Enter your name", message="Enter your name to be included in the label signature.", window_width=500, window_height=150, default="John Doe")
        print(f"User entered name: {name}")
    except UserCancelledError as e:
        print(f"User cancelled name entry")