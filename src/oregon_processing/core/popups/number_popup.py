import tkinter as tk
from pathlib import Path

from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class NumberPopup(Popup):

    def __init__(self, parent, title, message, window_width=500, window_height=150, number_type=int, negative_allowed=False, zero_allowed=True, valid_values=None, default=None):
        super().__init__(parent, title=f"{title}", window_height=window_height, window_width=window_width)
        self._message = message
        self._window_width = window_width
        self._number_type = number_type
        self._negative_allowed = negative_allowed
        self._zero_allowed = zero_allowed
        self._default = default
        self._valid_values = valid_values

        self._window_height = window_height

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
            self._entry.insert(0, str(self._default))
        _, self._error_label = self._build_entry_error_section(row=2)
        self._build_button_section(row=3, button_defs=[
            ("OK", self._on_ok),
            ("Cancel", self._on_cancel)],
            pady=(0,10)
        )

        #Bind pressing enter to OK action and escape to cancel action
        self.bind('<Return>', lambda event: self._on_ok())
        self.bind('<Escape>', lambda event: self._on_cancel())

    def _on_ok(self):
        val = self._entry.get().strip()

        try:
            try:
                # check that input number is of correct type
                if self._number_type == int:
                    val = int(val)
                elif self._number_type == float:
                    val = float(val)
                else:
                    raise ValueError("Unsupported number type specified for NumberPopup.")
            except ValueError:
                raise ValueError(f"Invalid input. Please enter a valid {self._number_type.__name__} number.")

            #check that number is not negative if negative numbers are not allowed
            if not self._negative_allowed and val < 0:
                raise ValueError("Negative numbers are not allowed.")

            #check that number is not zero if zero is not allowed
            if not self._zero_allowed and val == 0:
                raise ValueError("Zero is not allowed.")

            #check that number is in valid values if valid values are specified
            if self._valid_values is not None and val not in self._valid_values:
                raise ValueError(f"Invalid input. Please enter one of the following values: {', '.join(map(str, self._valid_values))}.")

            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))

    def _on_cancel(self):
        self.result = None
        self.destroy()

def prompt_int(title: str, message: str, window_width=600, window_height=175, negative_allowed=False, zero_allowed=True, valid_values=None, default=None) -> int:
    root = tk.Tk()
    root.withdraw()              # Hides the root window

    while True:
        main_prompt = NumberPopup(root, title=title, message=message, window_width=window_width, window_height=window_height, number_type=int, negative_allowed=negative_allowed, zero_allowed=zero_allowed, valid_values=valid_values, default=default)
        main_prompt.wait_window()
        choice = main_prompt.result
        if choice is not None:
            root.destroy()
            return int(choice)
        else:
            root.destroy()
            raise UserCancelledError("User cancelled the number entry prompt.")

def prompt_float(title: str, message: str, window_width=600, window_height=175, negative_allowed=False, zero_allowed=True, valid_values=None, default=None) -> float:
    root = tk.Tk()
    root.withdraw()              # Hides the root window

    while True:
        main_prompt = NumberPopup(root, title=title, message=message, window_width=window_width, window_height=window_height, number_type=float, negative_allowed=negative_allowed, zero_allowed=zero_allowed, valid_values=valid_values, default=default)
        main_prompt.wait_window()
        choice = main_prompt.result
        if choice is not None:
            root.destroy()
            return float(choice)
        else:
            root.destroy()
            raise UserCancelledError("User cancelled the number entry prompt.")

if __name__ == "__main__":
    # Example usage
    file_to_test = Path("C:/path/to/locked_file.xlsx")

    try:
        number = prompt_int(title="Enter a number", message="Enter an integer number", window_width=500, window_height=150, valid_values=[15, 30, 60], default=30)
        print(f"User entered number: {number}")
    except UserCancelledError as e:
        print(f"User cancelled number entry")

    try:
        number = prompt_float(title="Enter a number", message="Enter a float number", window_width=500, window_height=150, valid_values=[0.5, 1.0, 1.5], default=1.0)
        print(f"User entered number: {number}")
    except UserCancelledError as e:
        print(f"User cancelled number entry")

    try:
        number = prompt_int(title="Enter a number", message="Enter an integer number", window_width=500, window_height=150, zero_allowed=False)
        print(f"User entered number: {number}")
    except UserCancelledError as e:
        print(f"User cancelled number entry")