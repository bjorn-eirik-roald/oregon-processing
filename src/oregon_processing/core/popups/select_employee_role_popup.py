import tkinter as tk
from oregon_processing.core.popups.popup import Popup, UserCancelledError, NMBUPromptFont

class SelectEmployeeRolePopup(Popup):

    def __init__(self, parent, title_text: str, context_text: str, issue_text: str, action_text: str, window_height: int=250, window_width: int = 500):

        super().__init__(parent, title="Select Employee Role", window_height=window_height, window_width=window_width)

        self.title_text = title_text
        self.context_text = context_text
        self.issue_text = issue_text
        self.action_text = action_text
        self._window_height = window_height
        self._window_width = window_width

        self.result = None

        self._build()

    def _build(self):

        self._build_title_section()
        self._build_context_section()
        self._build_issue_section()
        self._build_action_section()

        self._build_button_section(row=4, button_width=15, button_defs=[
            ("Academic", lambda: self._on_select("academic")),
            ("Non-academic", lambda: self._on_select("non-academic")),
            ("Foreign academic", lambda: self._on_select("foreign academic"))
        ])


    def _build_title_section(self):
        self.title_frame = tk.Frame(self, bg=self.secondary_green)
        self.title_frame.grid(row=0, column=0, padx=20, pady=(16, 12), sticky="nsew")
        title_font = NMBUPromptFont.get()
        tk.Label(
            self.title_frame,
            text=self.title_text,
            justify="center",
            bg=self.secondary_green,
            font=title_font,
            fg=NMBUPromptFont.FONT_COLOR
        ).pack()

    def _build_context_section(self):
        context_font = NMBUPromptFont.get(size=10)
        context_bold = NMBUPromptFont.get(weight="bold", size=12)
        self.context_frame = self._build_prompt_section(
            row=1,
            title="Context info:",
            text=self.context_text,
            title_font=context_bold,
            text_font=context_font
        )

    def _build_issue_section(self):
        font = NMBUPromptFont.get(size=10)
        bold_font = NMBUPromptFont.get(weight="bold", size=12)
        self.issue_frame = self._build_prompt_section(
            row=2,
            title="Issue:",
            text=self.issue_text,
            title_font=bold_font,
            text_font=font
        )

    def _build_action_section(self):
        font = NMBUPromptFont.get(size=10)
        bold_font = NMBUPromptFont.get(weight="bold", size=12)
        self.action_frame = self._build_prompt_section(
            row=3,
            title="Action required:",
            text=self.action_text,
            title_font=bold_font,
            text_font=font
        )

    def _on_select(self, role):
        self.result = role
        self.destroy()

    def _on_abort(self):
        self.result = None
        self.destroy()

def select_employee_role(title_text, context_text, issue_text, action_text, window_height=550):
    root = tk.Tk()
    root.withdraw()
    popup = SelectEmployeeRolePopup(root, title_text, context_text, issue_text, action_text, window_height)
    popup.wait_window()
    result = popup.result

    if result == "academic":
        root.destroy()
        return result
    elif result == "non-academic":
        root.destroy()
        return "non_academic"
    elif result == "foreign academic":
        root.destroy()
        return "foreign_academic"
    else:
        root.destroy()
        raise UserCancelledError("User aborted employee role selection.")

if __name__ == "__main__":
    # Example usage with generic placeholders
    title_text = "Select Employee Role"
    context_text = (
        "Resource: 12345 (John Doe)\n"
        "Work Order: WO-001\n"
        "Period: 2026-03\n"
        "Registered hours: 0\n"
        "Registered overhead: 0 NOK\n"
        "Registered hourly overhead rate: ∞ NOK/hour\n"
        "Expected rates:\n"
        "\t- academic 500 NOK/hour\n"
        "\t- non-academic 400 NOK/hour\n"
        "\t- foreign academic 600 NOK/hour\n"
        "Employee overview indicates role: academic"
    )
    issue_text = "Computed hourly rate is infinite due to zero registered hours, which does not match any expected rate for this employee."
    action_text = "Please select the correct role for this employee. Employee overview indicates role: academic."

    try:
        choice = select_employee_role(title_text, context_text, issue_text, action_text, window_height=550)
        print(f"User selected role: {choice}")
    except UserCancelledError as e:
        print(f"User aborted action: {e}")
