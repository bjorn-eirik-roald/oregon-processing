import tkinter as tk
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class UrlPopup(Popup):

    def __init__(self, parent, title, message, window_width=500, window_height=100, expected_url_prefix=None, default=None):
        super().__init__(parent, title=f"{title}", window_height=window_height, window_width=window_width)
        self._message = message
        self._window_width = window_width
        self._window_height = window_height
        self._expected_url_prefix = expected_url_prefix
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

        _, self._entry = self._build_entry_section(row=1, entry_width=100, default=self._default)
        _, self._error_label = self._build_entry_error_section(row=2)

        self._build_button_section(row=3, button_defs=[
            ("OK", self._on_ok),
            ("Cancel", self._on_cancel)
        ])

        # Bind the Return key to trigger the OK button and Escape key to trigger the Cancel button
        self.bind("<Return>", lambda event: self._on_ok())
        self.bind("<Escape>", lambda event: self._on_cancel())

    def _on_ok(self):
        val = self._entry.get().strip()

        try:
            # expect URL Check that it's not empty and follows a basic URL pattern
            if self._expected_url_prefix:
                if not val or not val.startswith(self._expected_url_prefix):
                    raise ValueError(f"Invalid URL. Must start with: {self._expected_url_prefix}")

            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))

    def _on_cancel(self):
        self.result = None
        self.destroy()

def prompt_url(title: str, message: str, window_width=600, window_height=100, expected_url_prefix=None, default=None) -> str:
    root = tk.Tk()
    root.withdraw()              # Hides the root window

    while True:
        main_prompt = UrlPopup(root, title=title, message=message, window_width=window_width, window_height=window_height, expected_url_prefix=expected_url_prefix, default=default)
        main_prompt.wait_window()
        choice = main_prompt.result
        if choice:
            root.destroy()
            return choice
        else:
            root.destroy()
            raise UserCancelledError("User cancelled the URL entry prompt.")

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        expected_prefix = "https://stoffkartotek.nmbu.no/"
        url = prompt_url(title="Enter URL", message="Enter the URL for the location.", expected_url_prefix=expected_prefix, default="https://stoffkartotek.nmbu.no/", window_width=600, window_height=175)
        print(f"User entered URL: {url}")
    except UserCancelledError as e:
        print(f"User cancelled URL entry")