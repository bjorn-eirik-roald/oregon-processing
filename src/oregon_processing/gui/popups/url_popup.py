from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root

class UrlPopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 175
    DEFAULT_TITLE         = "Enter URL"
    DEFAULT_PROMPT_TEXT   = "Please enter a URL."
    DEFAULT_PROMPT_ANCHOR = "center"
    DEFAULT_PROMPT_JUSTIFY = "center"
    DEFAULT_PROMPT_PADY    = (20, 10)
    DEFAULT_ENTRY_PADY     = (0, 0)
    DEFAULT_BUTTON_SECTION_PADY = (0, 10)

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("window_width",  self.DEFAULT_WINDOW_WIDTH)
        kwargs.setdefault("window_height", self.DEFAULT_WINDOW_HEIGHT)
        kwargs.setdefault("title",         self.DEFAULT_TITLE)
        kwargs.setdefault("prompt_section_1_prompt_text", self.DEFAULT_PROMPT_TEXT)
        kwargs.setdefault("prompt_anchor",  self.DEFAULT_PROMPT_ANCHOR)
        kwargs.setdefault("prompt_justify", self.DEFAULT_PROMPT_JUSTIFY)
        kwargs.setdefault("prompt_pady",    self.DEFAULT_PROMPT_PADY)
        kwargs.setdefault("entry_pady",     self.DEFAULT_ENTRY_PADY)
        kwargs.setdefault("button_section_pady", self.DEFAULT_BUTTON_SECTION_PADY)

        self._expected_url_prefix = kwargs.get("expected_url_prefix")

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
            if self._expected_url_prefix:
                if not val or not val.startswith(self._expected_url_prefix):
                    raise ValueError(f"Invalid URL. Must start with: {self._expected_url_prefix}")
            self.result = val
            self.destroy()
        except ValueError as e:
            self._error_label.config(text=str(e))


def url_prompt(message: str = None, default_value: str = None, expected_url_prefix: str = None, **kwargs) -> str:
    cancel_error_message = kwargs.pop("cancel_error_message", "User cancelled the URL entry prompt.")

    kwargs.setdefault("prompt_section_1_prompt_text", message if message is not None else UrlPopup.DEFAULT_PROMPT_TEXT)

    if default_value is not None:
        kwargs.setdefault("entry_default_value", default_value)
    if expected_url_prefix is not None:
        kwargs.setdefault("expected_url_prefix", expected_url_prefix)

    root  = get_root()
    popup = UrlPopup(root, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice:
        return choice
    raise UserCancelledError(cancel_error_message)
