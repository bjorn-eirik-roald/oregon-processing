import tkinter as tk
from pathlib import Path
from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root
from oregon_processing.gui.styles import SECONDARY_GREEN, StandardButtonStyle

class MultiChoicePopup(Popup):

    DEFAULT_WINDOW_WIDTH  = 500
    DEFAULT_WINDOW_HEIGHT = 350
    DEFAULT_TITLE         = "Select an option"
    DEFAULT_PROMPT_TEXT   = "Please select one of the options below."
    DEFAULT_PROMPT_ANCHOR = "center"
    DEFAULT_PROMPT_JUSTIFY = "center"

    def __init__(self, parent, choices: list[str], **kwargs):
        kwargs.setdefault("window_width",  self.DEFAULT_WINDOW_WIDTH)
        kwargs.setdefault("window_height", self.DEFAULT_WINDOW_HEIGHT)
        kwargs.setdefault("prompt_section_1_prompt_text", self.DEFAULT_PROMPT_TEXT)
        kwargs.setdefault("prompt_section_1_prompt_anchor", self.DEFAULT_PROMPT_ANCHOR)
        kwargs.setdefault("prompt_section_1_prompt_justify", self.DEFAULT_PROMPT_JUSTIFY)
        kwargs.setdefault("title",         self.DEFAULT_TITLE)

        self._choices = choices

        super().__init__(parent, **kwargs)
        self._build(**kwargs)

    def _build(self, **kwargs):
        num_sections = self._build_prompt_sections(first_section_row=0, **kwargs)
        button_defs  = [(choice, lambda c=choice: self._on_choice(c)) for choice in self._choices]
        self._build_button_section(row=num_sections, button_defs=button_defs, **kwargs)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda event: self._on_close())

    def _on_choice(self, choice):
        self.result = choice
        self.destroy()


class VerticalMultiChoicePopup(MultiChoicePopup):
    """Stack buttons vertically instead of arranging them in a single row."""

    DEFAULT_WINDOW_WIDTH = 500
    DEFAULT_BASE_WINDOW_HEIGHT = 120

    def __init__(self, parent, choices: list[str], **kwargs):
        if "window_height" not in kwargs:
            base_window_height = kwargs.pop("base_window_height", self.DEFAULT_BASE_WINDOW_HEIGHT)
            button_height = kwargs.get("button_height", StandardButtonStyle.DEFAULT_BUTTON_HEIGHT)
            estimated_height_per_choice = (button_height * 24) + 18
            window_height = base_window_height + len(choices) * estimated_height_per_choice
            kwargs["window_height"] = window_height
        super().__init__(parent, choices=choices, **kwargs)

    def _build(self, **kwargs):
        num_sections = self._build_prompt_sections(first_section_row=0, **kwargs)
        button_defs = [(choice, lambda c=choice: self._on_choice(c)) for choice in self._choices]

        button_section_pady = kwargs.get("button_section_pady", (10, 10))
        button_section_padx = kwargs.get("button_section_padx", (20, 20))
        button_section_bg = kwargs.get("button_section_bg", SECONDARY_GREEN)
        button_padx = kwargs.get("button_padx", (8, 8))
        button_pady = kwargs.get("button_pady", (4, 4))

        section_frame = tk.Frame(self, bg=button_section_bg)
        section_frame.grid(row=num_sections, column=0, padx=button_section_padx, pady=button_section_pady, sticky="ew")
        section_frame.grid_columnconfigure(0, weight=1)

        for i, (label_text, callback) in enumerate(button_defs):
            button = self._build_button(label_text, callback, parent=section_frame, **kwargs)
            button.grid(row=i, column=0, padx=button_padx, pady=button_pady, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda event: self._on_close())

    def _build_button(self, label_text: str, callback, parent=None, **kwargs):

        if parent is None:
            parent = self

        return StandardButtonStyle.create(parent, label_text, callback, **kwargs)


def multi_choice_prompt(choices: list[str], **kwargs) -> str:
    cancel_error_message = kwargs.pop("cancel_error_message", "User cancelled the multi-choice prompt.")

    root  = get_root()
    popup = MultiChoicePopup(root, choices=choices, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice is not None:
        return choice
    raise UserCancelledError(cancel_error_message)


def vertical_multi_choice_prompt(choices: list[str], **kwargs) -> str:
    """Prompt with vertically stacked buttons sized to the number of choices."""
    cancel_error_message = kwargs.pop("cancel_error_message", "User cancelled the vertical multi-choice prompt.")

    root = get_root()
    popup = VerticalMultiChoicePopup(root, choices=choices, **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice is not None:
        return choice
    raise UserCancelledError(cancel_error_message)


def confirm_prompt(message, **kwargs) -> bool:
    cancel_error_message = kwargs.pop("cancel_error_message", "User cancelled the confirm prompt.")

    kwargs.setdefault("title", "Confirm Action")
    kwargs.setdefault("confirm_button_text", "Confirm")
    kwargs.setdefault("cancel_button_text", "Cancel")
    kwargs.setdefault("prompt_section_1_prompt_text", message if message is not None else "Please confirm your action.")
    kwargs.setdefault("prompt_section_1_prompt_anchor",  "center")
    kwargs.setdefault("prompt_section_1_prompt_justify", "center")
    kwargs.setdefault("window_height", 150)

    root = get_root()
    popup = MultiChoicePopup(root, choices=["Confirm", "Cancel"], **kwargs)
    popup.wait_window()
    choice = popup.result
    if choice is not None:
        return choice == "Confirm"
    raise UserCancelledError(cancel_error_message)

def handle_permission_denied(file_path: Path, **kwargs) -> str:
    message = (
        f"Access to the file was denied, likely because it is open in another program. "
        f"Please close the file and retry.\n\n"
        f"File: {file_path.name}"
    )

    # set defaults for title, prompt text, and button width if not provided in kwargs
    kwargs.setdefault("title", f"Access Denied - {file_path.name}")
    kwargs.setdefault("prompt_section_1_prompt_text", message)
    kwargs.setdefault("prompt_section_1_prompt_text_size", 12)
    kwargs.setdefault("prompt_section_1_prompt_anchor", "center")
    kwargs.setdefault("prompt_section_1_prompt_justify", "center")
    kwargs.setdefault("button_width", 10)

    # set choice defaults for the multi-choice popup
    kwargs.setdefault("choices", ["Retry", "Abort"])

    choice = multi_choice_prompt(**kwargs)
    if choice == "Abort":
        raise UserCancelledError("User aborted due to permission denied error.")
    return choice  # "Retry"
