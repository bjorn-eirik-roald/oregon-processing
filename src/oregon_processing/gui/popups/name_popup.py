from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root

class NamePopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 150
    DEFAULT_TITLE         = "Enter Name"
    DEFAULT_PROMPT_TEXT   = "Please enter a name."
    DEFAULT_PROMPT_ANCHOR = "center"
    DEFAULT_PROMPT_JUSTIFY = "center"
    DEFAULT_PROMPT_PADY    = (20, 10)
    DEFAULT_ENTRY_PADY     = (0, 0)
    DEFAULT_BUTTON_SECTION_PADY = (0, 10)
    DEFAULT_ALLOW_NUMBERS = True
    DEFAULT_ENTRY_FIELD_WIDTH = 30

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

        self._allow_numbers = kwargs.get("allow_numbers", self.DEFAULT_ALLOW_NUMBERS)

        self._entry_field = None
        self._error_label = None

        super().__init__(parent, **kwargs)
        self._build(**kwargs)

    def _build(self, **kwargs):
        num_sections  = self._build_prompt_sections(first_section_row=0, **kwargs)
        _, self._entry_field = self._build_entry_section(row=num_sections, **kwargs)
        _, self._error_label = self._build_entry_error_section(row=num_sections + 1, **kwargs)
        self._build_button_section(row=num_sections + 2, button_defs=[("OK", self._on_ok), ("Cancel", self._on_close)], **kwargs)

        self.bind("<Return>", lambda event: self._on_ok())
        self.bind("<Escape>", lambda event: self._on_close())

    def _on_ok(self):
        val = self._entry_field.get().strip()
        try:
            if self._allow_numbers:
                if not val:
                    raise ValueError("Input cannot be empty.")
            else:
                if not val or any(char.isdigit() or not char.isalnum() and char not in " -." for char in val):
                    raise ValueError("Invalid name. No digits or special characters allowed.")
            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))

def name_prompt(message: str = None, **kwargs) -> str:
    kwargs.setdefault("prompt_section_1_prompt_text", message if message is not None else NamePopup.DEFAULT_PROMPT_TEXT,)
    root  = get_root()
    popup = NamePopup(root, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice:
        return choice
    raise UserCancelledError("User cancelled the name entry prompt.")
