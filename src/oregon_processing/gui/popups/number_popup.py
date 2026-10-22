from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root

class NumberPopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 175
    DEFAULT_TITLE         = "Enter Number"
    DEFAULT_PROMPT_TEXT   = "Please enter a number."
    DEFAULT_PROMPT_ANCHOR = "center"
    DEFAULT_PROMPT_JUSTIFY = "center"
    DEFAULT_PROMPT_PADY    = (20, 10)
    DEFAULT_ENTRY_PADY     = (0, 0)
    DEFAULT_BUTTON_SECTION_PADY = (0, 10)
    DEFAULT_ENTRY_FIELD_WIDTH = 30
    DEFAULT_ALLOW_NEGATIVE_NUMBERS = True
    DEFAULT_ALLOW_DECIMAL_NUMBERS = True
    DEFAULT_ALLOW_EMPTY_INPUT = False
    DEFAULT_MIN_VALUE = None
    DEFAULT_MAX_VALUE = None
    DEFAULT_NUMBER_TYPE = int


    def __init__(self, parent, **kwargs):
        kwargs.setdefault("window_width",  self.DEFAULT_WINDOW_WIDTH)
        kwargs.setdefault("window_height", self.DEFAULT_WINDOW_HEIGHT)
        kwargs.setdefault("title",         self.DEFAULT_TITLE)
        kwargs.setdefault("prompt_section_1_prompt_text", self.DEFAULT_PROMPT_TEXT)
        kwargs.setdefault("prompt_anchor",  self.DEFAULT_PROMPT_ANCHOR)
        kwargs.setdefault("prompt_justify", self.DEFAULT_PROMPT_JUSTIFY)
        kwargs.setdefault("prompt_pady",    self.DEFAULT_PROMPT_PADY)
        kwargs.setdefault("entry_field_width",   self.DEFAULT_ENTRY_FIELD_WIDTH)
        kwargs.setdefault("entry_pady",          self.DEFAULT_ENTRY_PADY)
        kwargs.setdefault("button_section_pady", self.DEFAULT_BUTTON_SECTION_PADY)

        self._number_type      = kwargs.get("number_type",      self.DEFAULT_NUMBER_TYPE)
        self._negative_allowed = kwargs.get("negative_allowed", self.DEFAULT_ALLOW_NEGATIVE_NUMBERS)
        self._decimal_allowed  = kwargs.get("decimal_allowed",  self.DEFAULT_ALLOW_DECIMAL_NUMBERS)
        self._empty_allowed    = kwargs.get("empty_allowed",    self.DEFAULT_ALLOW_EMPTY_INPUT)
        self._min_value        = kwargs.get("min_value",        self.DEFAULT_MIN_VALUE)
        self._max_value        = kwargs.get("max_value",        self.DEFAULT_MAX_VALUE)
        self._valid_values     = kwargs.get("valid_values", None)

        self._entry_field = None
        self._error_label = None

        super().__init__(parent, **kwargs)
        self._build(**kwargs)

    def _build(self, **kwargs):
        num_sections  = self._build_prompt_sections(first_section_row=0, **kwargs)
        _, self._entry_field = self._build_entry_section(row=num_sections, **kwargs)
        _, self._error_label = self._build_entry_error_section(row=num_sections + 1, **kwargs)
        self._build_button_section(row=num_sections + 2, button_defs=[("OK", self._on_ok), ("Cancel", self._on_close)], **kwargs)

        self.bind('<Return>', lambda event: self._on_ok())
        self.bind('<Escape>', lambda event: self._on_close())

    def _on_ok(self):
        val = self._entry_field.get().strip()
        try:
            try:
                if self._number_type == int:
                    val = int(val)
                if self._number_type == float:
                    val = float(val)
            except ValueError:
                raise ValueError(f"Invalid input. Please enter a valid {self._number_type.__name__} number.")

            if not self._negative_allowed and val < 0:
                raise ValueError("Negative numbers are not allowed.")

            if not self._zero_allowed and val == 0:
                raise ValueError("Zero is not allowed.")

            if self._valid_values is not None and val not in self._valid_values:
                raise ValueError(f"Invalid input. Please enter one of the following values: {', '.join(map(str, self._valid_values))}.")

            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))


def integer_prompt(message: str = None, negative_allowed: bool = False, zero_allowed: bool = True, valid_values=None, **kwargs) -> int:
    kwargs.setdefault("title", "Enter Integer")
    kwargs.setdefault("prompt_section_1_prompt_text", message if message is not None else "Please enter an integer value.")
    kwargs["number_type"] = int
    kwargs.setdefault("negative_allowed", negative_allowed)
    kwargs.setdefault("zero_allowed",     zero_allowed)
    if valid_values is not None:
        kwargs.setdefault("valid_values", valid_values)
    root  = get_root()
    popup = NumberPopup(root, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice is not None:
        return int(choice)
    raise UserCancelledError("User cancelled the number entry prompt.")


def float_prompt(message: str = None, negative_allowed: bool = False, zero_allowed: bool = True, valid_values=None, **kwargs) -> float:
    kwargs.setdefault("title", "Enter Number")
    kwargs.setdefault("prompt_section_1_prompt_text", message if message is not None else "Please enter a numeric value.")
    kwargs["number_type"] = float
    kwargs.setdefault("negative_allowed", negative_allowed)
    kwargs.setdefault("zero_allowed",     zero_allowed)
    if valid_values is not None:
        kwargs.setdefault("valid_values", valid_values)

    root  = get_root()
    popup = NumberPopup(root, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice is not None:
        return float(choice)
    raise UserCancelledError("User cancelled the number entry prompt.")
