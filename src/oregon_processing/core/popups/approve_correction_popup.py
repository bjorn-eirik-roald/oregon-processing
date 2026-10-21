import tkinter as tk
from oregon_processing.core.popups.popup import Popup, NMBUPromptFont, UserCancelledError

class ApproveCorrectionPopup(Popup):

    def __init__(self, parent, title_text: str, context_text: str, suggested_correction: str, action_required: str, window_height: int=350, window_width: int = 500):

        super().__init__(parent, title="Approve Correction", window_height=window_height, window_width=window_width)
        self._title_text = title_text
        self._context_text = context_text
        self._suggested_correction = suggested_correction
        self._action_required = action_required

        self._build()

        self.protocol("WM_DELETE_WINDOW", self._on_abort)

    def _build(self):

        self._build_title_section()
        self._build_context_section()
        self._build_suggested_correction_section()
        self._build_action_required_section()

        self._build_button_section(row=4, button_defs=[
            ("Approve", self._on_approve),
            ("Reject", self._on_reject)
        ])

    def _build_title_section(self):
        title_font = NMBUPromptFont.get()
        self.title_frame = self._build_prompt_section(
            row=0,
            text=self._title_text,
            text_font=title_font,
            anchor="center",
            justify="center"
        )

    def _build_context_section(self):
        context_font = NMBUPromptFont.get(size=10)
        context_bold = NMBUPromptFont.get(weight="bold", size=12)
        self.context_frame = self._build_prompt_section(
            row=1,
            title="Context info:",
            text=self._context_text,
            title_font=context_bold,
            text_font=context_font,
            anchor="w",
            justify="left"
        )

    def _build_suggested_correction_section(self):
        font = NMBUPromptFont.get(size=10)
        bold_font = NMBUPromptFont.get(weight="bold", size=12)
        self.suggested_frame = self._build_prompt_section(
            row=2,
            title="Suggested correction:",
            text=self._suggested_correction,
            title_font=bold_font,
            text_font=font,
            anchor="w",
            justify="left"
        )

    def _build_action_required_section(self):
        font = NMBUPromptFont.get(size=10)
        bold_font = NMBUPromptFont.get(weight="bold", size=12)
        self.action_frame = self._build_prompt_section(
            row=3,
            title="Action required:",
            text=self._action_required,
            title_font=bold_font,
            text_font=font,
            anchor="w",
            justify="left"
        )

    def _on_approve(self):
        self.result = 'approve'
        self.destroy()

    def _on_reject(self):
        self.result = 'reject'
        self.destroy()

    def _on_abort(self):
        self.result = None
        self.destroy()

def handle_correction_approval(title_text, context_text, suggested_correction, action_required, window_height=520):
    root = tk.Tk()
    root.withdraw()
    popup = ApproveCorrectionPopup(root, title_text, context_text, suggested_correction, action_required, window_height=window_height)
    popup.wait_window()
    root.destroy()

    result = popup.result
    if result == 'approve':
        return result
    elif result == 'reject':
         raise UserCancelledError("User rejected the suggested correction, manual review required.")
    else:
        raise UserCancelledError("User aborted the correction approval process.")

if __name__ == "__main__":

    # Section 1: Title
    title_text = "Data Correction Required for Entry"

    # Section 2: Context
    context_text = (
        "Resource: 12345 (John Doe)\n"
        "Work Order: WO-001\n"
        "Period: 2026-03\n"
        "Role computed from rates: academic\n"
        "Employee overview indicates role: academic\n"
        "Registered hours: 0\n"
        "Registered overhead: 0 NOK\n"
        "Registered hourly overhead rate: ∞ NOK/hour\n"
        "Expected hourly overhead rate for this role: 500 NOK/hour\n"
    )

    # Section 3: TLDR/Action
    suggested_correction_text = (f"Based on the overhead and expected rate, the computed hours should be: 10.000")
    action_required_text = (f"Approve using the computed hours above, or abort to manually review and correct the registered hours.")

    try:
        answer = handle_correction_approval(title_text, context_text, suggested_correction_text, action_required_text, window_height=520)
        print(f"User answered: {answer}")
    except UserCancelledError as e:
        print(f"Action aborted: {e}")
