import datetime
from pathlib import Path

from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root

class DatetimePopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 200
    DEFAULT_TITLE         = "Enter datetime"
    DEFAULT_PROMPT_TEXT   = "Please set the datetime."
    DEFAULT_PROMPT_ANCHOR = "center"
    DEFAULT_PROMPT_JUSTIFY = "center"

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("window_width",  self.DEFAULT_WINDOW_WIDTH)
        kwargs.setdefault("window_height", self.DEFAULT_WINDOW_HEIGHT)
        kwargs.setdefault("title",         self.DEFAULT_TITLE)
        kwargs.setdefault("prompt_section_1_prompt_text", self.DEFAULT_PROMPT_TEXT)
        kwargs.setdefault("prompt_section_1_prompt_anchor", self.DEFAULT_PROMPT_ANCHOR)
        kwargs.setdefault("prompt_section_1_prompt_justify", self.DEFAULT_PROMPT_JUSTIFY)

        self._date_only = kwargs.get("date_only", False)

        super().__init__(parent, **kwargs)
        self._build(**kwargs)

    def _build(self, **kwargs):
        num_sections = self._build_prompt_sections(first_section_row=0, **kwargs)
        self._build_button_section(
            row=num_sections,
            button_defs=[("Use Current", self._on_use_current), ("Define Manually", self._on_define), ("Cancel", self._on_close)],
            **kwargs
        )

    def _on_use_current(self):
        self.result = "use_current"
        self.destroy()

    def _on_define(self):
        self.result = "define"
        self.destroy()


class ManualDatetimePopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 250
    DEFAULT_TITLE         = "Enter datetime manually"

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("window_width",  self.DEFAULT_WINDOW_WIDTH)
        kwargs.setdefault("window_height", self.DEFAULT_WINDOW_HEIGHT)
        kwargs.setdefault("title",         self.DEFAULT_TITLE)

        self._date_only = kwargs.get("date_only", False)

        self._entry_field = None
        self._error_label = None

        super().__init__(parent, **kwargs)
        self._build(**kwargs)

    def _build(self, **kwargs):
        num_sections = self._build_prompt_sections(first_section_row=0, **kwargs)
        _, self._entry_field = self._build_entry_section(row=num_sections, **kwargs)
        _, self._error_label = self._build_entry_error_section(row=num_sections + 1, **kwargs)
        self._build_button_section(row=num_sections + 2, button_defs=[("OK", self._on_ok), ("Cancel", self._on_close)], **kwargs)

        self.bind('<Return>', lambda event: self._on_ok())
        self.bind('<Escape>', lambda event: self._on_close())

    def _on_ok(self):
        val = self._entry_field.get().strip()
        try:
            if self._date_only:
                formats = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d")
                for fmt in formats:
                    try:
                        dt = datetime.datetime.strptime(val, fmt).replace(hour=0, minute=0, second=0, microsecond=0)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid date format. Use YYYY-MM-DD.")
            else:
                formats = ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y.%m.%d %H:%M", "%Y%m%d %H:%M")
                for fmt in formats:
                    try:
                        dt = datetime.datetime.strptime(val, fmt).replace(second=0, microsecond=0)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError("Invalid datetime format. Use YYYY-MM-DD HH:MM.")

            self.result = dt
            self.destroy()
        except Exception:
            if self._date_only:
                self._error_label.config(text="Invalid format. Use YYYY-MM-DD.")
            else:
                self._error_label.config(text="Invalid format. Use YYYY-MM-DD HH:MM.")


def file_export_datetime_prompt(input_filename: Path, **kwargs) -> datetime.datetime:
    root = get_root()

    while True:
        main_kwargs.setdefault("date_only", False)
        if main_kwargs["date_only"]:
            message = (f"Set export date for file.\n File: {input_filename}\n\n"
                       "Choose 'Use Current' to use current date, "
                       "or 'Define' to enter manually.")
        else:
            message = (f"Set export date and time for file.\n File: {input_filename}\n\n"
                       "Choose 'Use Current' to use current date and time, "
                       "or 'Define' to enter manually.")

        main_kwargs = dict(kwargs)
        main_kwargs.setdefault("title", "Enter export datetime")
        main_kwargs.setdefault("prompt_section_1_prompt_text", message)

        main_popup = DatetimePopup(parent=root, **main_kwargs)
        main_popup.wait_window()
        choice = main_popup.result

        if choice == "use_current":
            if main_kwargs["date_only"]:
                return datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                return datetime.datetime.now()
        elif choice == "define":
            if main_kwargs["date_only"]:
                manual_message = f"Please enter the export date for the file ({input_filename}):\nFormat: YYYY-MM-DD"
            else:
                manual_message = f"Please enter the export datetime for the file ({input_filename}):\nFormat: YYYY-MM-DD HH:MM"

            manual_kwargs = dict(kwargs)
            manual_kwargs.setdefault("title", "Enter export datetime manually")
            manual_kwargs.setdefault("date_only", main_kwargs["date_only"])
            manual_kwargs.setdefault("prompt_section_1_prompt_text", manual_message)
            manual_kwargs.setdefault("prompt_section_1_prompt_anchor", "center")
            manual_kwargs.setdefault("prompt_section_1_prompt_justify", "center")
            manual_kwargs["window_height"] = manual_kwargs.get("window_height", ManualDatetimePopup.DEFAULT_WINDOW_HEIGHT)

            manual_popup = ManualDatetimePopup(parent=root, **manual_kwargs)
            manual_popup.wait_window()

            if manual_popup.result is not None:
                return manual_popup.result
        else:
            raise UserCancelledError("User cancelled export datetime selection.")


def datetime_prompt(message: str, title: str = "Enter datetime", date_only: bool = False, **kwargs) -> datetime.datetime:
    root = get_root()

    if date_only:
        full_message = (f"{message}\n\n"
                        "Choose 'Use Current' to use current date, "
                        "or 'Define' to enter manually.")
    else:
        full_message = (f"{message}\n\n"
                        "Choose 'Use Current' to use current date and time, "
                        "or 'Define' to enter manually.")

    if date_only:
        manual_message = "Please enter the date:\nFormat: YYYY-MM-DD"
    else:
        manual_message = "Please enter the datetime:\nFormat: YYYY-MM-DD HH:MM"

    main_kwargs = dict(kwargs)
    main_kwargs.setdefault("title", title)
    main_kwargs.setdefault("date_only", date_only)
    main_kwargs.setdefault("prompt_section_1_prompt_text", full_message)
    manual_kwargs = dict(kwargs)
    manual_kwargs.setdefault("title", "Enter datetime manually")
    manual_kwargs.setdefault("date_only", date_only)
    manual_kwargs.setdefault("prompt_section_1_prompt_text", manual_message)
    manual_kwargs.setdefault("prompt_section_1_prompt_anchor", "center")
    manual_kwargs.setdefault("prompt_section_1_prompt_justify", "center")

    while True:

        main_popup = DatetimePopup(parent=root, **main_kwargs)
        main_popup.wait_window()
        choice = main_popup.result

        if choice == "use_current":
            if date_only:
                return datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                return datetime.datetime.now()
        elif choice == "define":
            manual_popup = ManualDatetimePopup(parent=root, **manual_kwargs)
            manual_popup.wait_window()

            if manual_popup.result is not None:
                return manual_popup.result
        else:
            raise UserCancelledError("User cancelled datetime selection.")
