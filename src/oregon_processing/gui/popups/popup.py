import tkinter as tk
from tkinter.font import Font

from oregon_processing.gui.styles import NormalFont, StandardButtonStyle, PRIMARY_GREEN, SECONDARY_GREEN, WHITE, BLACK
from oregon_processing.gui.root import get_root

class Popup(tk.Toplevel):

    """
    General popup base class for NMBU apps.
    Provides workplace color constants, default font, and utility methods for consistent look.
    Subclasses should use the provided style/color/font helpers for all widgets.
    """

    DEFAULT_WINDOW_WIDTH = 400
    DEFAULT_WINDOW_HEIGHT = 200
    DEFAULT_TITLE = ""

    def __init__(self, parent, **kwargs):
        if parent is None:
            parent = get_root()

        super().__init__(parent)

        self._window_width  = kwargs.get("window_width",  self.DEFAULT_WINDOW_WIDTH)
        self._window_height = kwargs.get("window_height", self.DEFAULT_WINDOW_HEIGHT)
        self._title         = kwargs.get("title",         self.DEFAULT_TITLE)
        resizable           = kwargs.get("resizable",     False)

        self.withdraw()
        self.resizable(resizable, resizable)
        self.title(self._title)
        self.grab_set()
        self._set_geometry()
        self._set_style()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.deiconify()

        self._result = None

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value

    def _build_prompt_section(self, row: int, prompt_text: str, **kwargs) -> tk.Frame:

        text                 = prompt_text
        title_text           = kwargs.get("prompt_title_text")

        text_font            = kwargs.get("prompt_text_font")
        title_font           = kwargs.get("prompt_title_text_font")

        text_size            = kwargs.get("prompt_text_size", 12)
        title_size           = kwargs.get("prompt_title_text_size", 12)

        text_weight          = kwargs.get("prompt_text_weight", "normal")
        title_weight         = kwargs.get("prompt_title_text_weight", "bold")

        title_text_color     = kwargs.get("prompt_title_text_color", WHITE)
        text_color           = kwargs.get("prompt_text_color", WHITE)

        prompt_bg            = kwargs.get("prompt_bg", SECONDARY_GREEN)
        prompt_pady          = kwargs.get("prompt_pady", (16, 12))
        prompt_padx          = kwargs.get("prompt_padx", (16, 12))
        prompt_anchor        = kwargs.get("prompt_anchor", "w")
        prompt_justify       = kwargs.get("prompt_justify", "center")

        if not isinstance(row, int):
            raise TypeError(f"row must be an int, got {type(row)}")
        if not isinstance(text, str):
            raise TypeError(f"text must be a str, got {type(text)}")
        if title_text is not None and not isinstance(title_text, str):
            raise TypeError(f"title_text must be a str or None, got {type(title_text)}")
        if text_font is not None and not isinstance(text_font, Font):
            raise TypeError(f"text_font must be a tkinter Font or None, got {type(text_font)}")
        if title_font is not None and not isinstance(title_font, Font):
            raise TypeError(f"title_font must be a tkinter Font or None, got {type(title_font)}")

        if text_font is None:
            text_font = NormalFont.create(weight=text_weight, size=text_size)
        if title_font is None:
            title_font = NormalFont.create(weight=title_weight, size=title_size)

        wraplength = self._window_width - (prompt_padx[0] + prompt_padx[1])

        section_frame = tk.Frame(self, bg=prompt_bg)
        section_frame.grid(row=row, column=0, padx=prompt_padx, pady=prompt_pady, sticky="nsew")

        if title_text is not None:
            tk.Label(section_frame, text=title_text, wraplength=wraplength,
                     justify=prompt_justify, anchor=prompt_anchor,
                     bg=prompt_bg, font=title_font, fg=title_text_color).pack(anchor=prompt_anchor)

        body_label = tk.Label(section_frame, text=text, wraplength=wraplength,
                              justify=prompt_justify, anchor=prompt_anchor,
                              bg=prompt_bg, font=text_font, fg=text_color)
        body_label.pack(anchor=prompt_anchor)

        return section_frame

    def _build_prompt_sections(self, first_section_row=0, **kwargs) -> int:

        prompt_sections = set()
        for arg in kwargs:
            if not arg.startswith("prompt_section_"):
                continue
            try:
                section_num = int(arg.split("_")[2])
            except (ValueError, IndexError):
                continue
            prompt_sections.add(section_num)

        section_nums = sorted(prompt_sections)

        diff = [section_nums[i] - section_nums[i-1] for i in range(1, len(section_nums))]
        if any(d != 1 for d in diff):
            raise ValueError("Prompt section numbers must be consecutive.")

        for section_idx, section_num in enumerate(section_nums):
            section_prefix = f"prompt_section_{section_num}_"
            section_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("prompt_section_")}
            for arg in kwargs:
                if arg.startswith(section_prefix):
                    section_kwargs[arg[len(section_prefix):]] = kwargs[arg]
            self._build_prompt_section(row=first_section_row + section_idx, **section_kwargs)

        return len(prompt_sections)

    def _auto_adjust_window_height(self, extra_padding: int = 12, max_height: int | None = None) -> None:
        """Expand the popup vertically if any child widget extends beyond the current bottom edge."""
        self.update_idletasks()

        root_y = self.winfo_rooty()
        current_bottom = root_y + self.winfo_height()
        max_content_bottom = current_bottom

        widgets_to_check = []
        stack = [self]
        seen = set()

        while stack:
            widget = stack.pop()
            if widget in seen:
                continue
            seen.add(widget)
            try:
                children = widget.winfo_children()
            except Exception:
                children = []
            if children:
                stack.extend(widget.winfo_children())
            widgets_to_check.append(widget)

        for widget in widgets_to_check:
            try:
                if not widget.winfo_viewable():
                    continue
                bottom = widget.winfo_rooty() + widget.winfo_height()
                if bottom > max_content_bottom:
                    max_content_bottom = bottom
            except Exception:
                continue

        if max_content_bottom > current_bottom:
            needed_height = max_content_bottom - root_y + extra_padding
            if max_height is not None:
                needed_height = min(needed_height, max_height)
            self._window_height = max(self._window_height, needed_height)
            self.minsize(self._window_width, self._window_height)
            self.geometry(f"{self._window_width}x{self._window_height}+{self.winfo_x()}+{self.winfo_y()}")

    def _build_entry_section(self, row: int, **kwargs) -> tk.Frame:

        entry_text_font    = kwargs.get("entry_text_font")
        entry_text_size    = kwargs.get("entry_text_size", 12)
        entry_text_color   = kwargs.get("entry_text_color", BLACK)

        entry_bg           = kwargs.get("entry_bg", WHITE)
        entry_insert_color = kwargs.get("entry_insert_color", "black")
        entry_section_bg   = kwargs.get("entry_section_bg", SECONDARY_GREEN)

        entry_pady         = kwargs.get("entry_pady", (10, 10))
        entry_padx         = kwargs.get("entry_padx", (20, 20))
        entry_justify      = kwargs.get("entry_justify", "center")

        entry_default_value = kwargs.get("entry_default_value", None)
        entry_field_width = kwargs.get("entry_field_width", max(20, (self._window_width - (entry_padx[0] + entry_padx[1])) // 10))

        if not isinstance(row, int):
            raise TypeError(f"row must be an int, got {type(row)}")
        if entry_default_value is not None and not isinstance(entry_default_value, str):
            raise TypeError(f"entry_default_value must be a str or None, got {type(entry_default_value)}")

        if entry_text_font is None:
            entry_text_font = NormalFont.create(size=entry_text_size)

        section_frame = tk.Frame(self, bg=entry_section_bg)
        section_frame.grid(row=row, column=0, padx=entry_padx, pady=entry_pady, sticky="nsew")

        entry_field = tk.Entry(section_frame, width=entry_field_width, justify=entry_justify,
                               font=entry_text_font, fg=entry_text_color, bg=entry_bg,
                               insertbackground=entry_insert_color)
        entry_field.pack()

        if entry_default_value is not None:
            entry_field.insert(0, entry_default_value)

        entry_field.focus_set()

        return section_frame, entry_field

    def _build_entry_error_section(self, row: int, **kwargs) -> tuple:
        """
        Unique kwarg names: entry_error_text_font, entry_error_text_size, entry_error_text_color,
        entry_error_bg, entry_error_pady, entry_error_padx, entry_error_anchor, entry_error_justify
        """
        entry_error_text_font  = kwargs.get("entry_error_text_font")
        entry_error_text_size  = kwargs.get("entry_error_text_size", 12)
        entry_error_text_color = kwargs.get("entry_error_text_color", "red")

        entry_error_bg         = kwargs.get("entry_error_bg", SECONDARY_GREEN)
        entry_error_pady       = kwargs.get("entry_error_pady", (5, 5))
        entry_error_padx       = kwargs.get("entry_error_padx", (20, 20))
        entry_error_anchor     = kwargs.get("entry_error_anchor", "center")
        entry_error_justify    = kwargs.get("entry_error_justify", "center")

        if not isinstance(row, int):
            raise TypeError(f"row must be an int, got {type(row)}")

        if entry_error_text_font is None:
            entry_error_text_font = NormalFont.create(size=entry_error_text_size)

        wraplength = self._window_width - (entry_error_padx[0] + entry_error_padx[1])

        section_frame = tk.Frame(self, bg=entry_error_bg)
        section_frame.grid(row=row, column=0, padx=entry_error_padx, pady=entry_error_pady, sticky="nsew")

        error_label = tk.Label(section_frame, text="", wraplength=wraplength,
                               justify=entry_error_justify, anchor=entry_error_anchor,
                               bg=entry_error_bg, font=entry_error_text_font, fg=entry_error_text_color)
        error_label.pack(anchor=entry_error_anchor, fill="x")

        return section_frame, error_label

    def _build_button_section(self, row: int, button_defs: list, **kwargs) -> tk.Frame:

        button_pady           = kwargs.get("button_pady", (5, 5))
        button_padx           = kwargs.get("button_padx", (5, 5))

        button_section_pady   = kwargs.get("button_section_pady", (5, 5))
        button_section_padx   = kwargs.get("button_section_padx", (20, 20))
        button_section_bg     = kwargs.get("button_section_bg", SECONDARY_GREEN)

        if not isinstance(row, int):
            raise TypeError("row must be an integer")

        if not isinstance(button_defs, list) or not all(
            isinstance(b, tuple) and len(b) == 2 and isinstance(b[0], str) and callable(b[1])
            for b in button_defs
        ):
            raise TypeError("button_defs must be a list of tuples (label: str, callback: callable)")

        section_frame = tk.Frame(self, bg=button_section_bg)
        section_frame.grid(row=row, column=0, padx=button_section_padx, pady=button_section_pady, sticky="ew")
        section_frame.grid_columnconfigure(0, weight=1)

        button_row_frame = tk.Frame(section_frame, bg=button_section_bg)
        button_row_frame.grid(row=0, column=0)

        for i, (label_text, callback) in enumerate(button_defs):
            button = StandardButtonStyle.create(button_row_frame, label_text, callback, **kwargs)
            button.grid(row=0, column=i, padx=button_padx, pady=button_pady)

        return section_frame

    def _set_geometry(self):
        self.minsize(self._window_width, self._window_height)
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (self._window_width // 2)
        y = (hs // 2) - (self._window_height // 2)
        self.geometry(f"{self._window_width}x{self._window_height}+{x}+{y}")
        self.grid_columnconfigure(0, weight=1)

    def _set_style(self):
        self.configure(bg=SECONDARY_GREEN)

    def _on_close(self):
        self.result = None
        self.destroy()
