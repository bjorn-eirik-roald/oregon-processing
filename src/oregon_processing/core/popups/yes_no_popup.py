import tkinter as tk
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class YesNoPopup(Popup):

    def __init__(self, parent, title="Confirm action", message="Please confirm your choice:", window_height=100, window_width=500, wraplength=400):
        super().__init__(parent, title=title, window_height=window_height, window_width=window_width)

        self._message = message
        self._window_height = window_height
        self._window_width = window_width
        self._wraplength = wraplength

        self._build()

    def _build(self):
        """
        Build the yes/no popup UI by delegating to section helpers.
        """

        font = NMBUPromptFont.get(size=12)
        self.prompt_frame = self._build_prompt_section(
            row=0,
            text=self._message,
            text_font=font,
            pady=(20, 10),
            anchor="center",
            justify="center",
            wraplength=self._wraplength

        )

        self._build_button_section(row=1,
            button_defs=[
            ("Yes", self._on_yes),
            ("No", self._on_no),
        ])

    def _on_yes(self):
        self.result = 'Yes'
        self.destroy()

    def _on_no(self):
        self.result = 'No'
        self.destroy()

def prompt_yes_no(message: str, window_height: int = 150, window_width: int = 500, wraplength: int = 400) -> str:
    root = tk.Tk()
    root.withdraw()              # Hides the root window
    while True:
        main_prompt = YesNoPopup(root, message=message, window_height=window_height, window_width=window_width, wraplength=wraplength)
        main_prompt.wait_window()
        choice = main_prompt.result



        if choice in ("Yes", "No"):
            root.destroy()
            return choice
        elif choice is None:
            root.destroy()
            raise UserCancelledError("User cancelled the yes/no prompt.")
        else:
            root.destroy()
            raise ValueError("Unexpected choice from YesNoPopup")

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        action = prompt_yes_no(f"Do you want to proceed with the action on {file_to_test}?", window_height=150, window_width=500)
        print(f"User chose to: {action}")
    except UserCancelledError as e:
        print(f"Action aborted: {e}")