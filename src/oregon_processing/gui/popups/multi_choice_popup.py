from pathlib import Path
from oregon_processing.exceptions import UserCancelledError
from oregon_processing.gui.popups.popup import Popup
from oregon_processing.gui.root import get_root

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


def multi_choice_prompt(choices: list[str], **kwargs) -> str:
    cancel_error_message = kwargs.pop("cancel_error_message", "User cancelled the multi-choice prompt.")

    root  = get_root()
    popup = MultiChoicePopup(root, choices=choices, **kwargs)
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
