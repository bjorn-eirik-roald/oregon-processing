import tkinter as tk
import tkinter.font as tkfont

from oregon_processing.exceptions import UserCancelledError # used for re import

class NMBUEntryFont:
    """
    Centralizes entry field font for NMBU popups.
    Use get() to obtain a bold font for entry widgets.
    """
    FONT_SIZE = 12
    FONT_WEIGHT = "bold"
    FONT_COLOR = "black"

    @staticmethod
    def get(size=None, weight=None):
        """
        Returns a tkfont.Font for entry fields.
        Optional size and weight override class defaults.
        """
        return tkfont.Font(
            family="TkDefaultFont",
            size=size if size is not None else NMBUEntryFont.FONT_SIZE,
            weight=weight if weight is not None else NMBUEntryFont.FONT_WEIGHT,
        )

class NMBUPromptFont:
    """
    Centralizes prompt label font for NMBU popups.
    Use get() to obtain a bold font for prompt labels.
    """
    FONT_SIZE = 16
    FONT_WEIGHT = "bold"
    FONT_COLOR = "white"

    @staticmethod
    def get(size=None, weight=None):
        """
        Returns a tkfont.Font for prompt labels.
        Optional size and weight override class defaults.
        """
        return tkfont.Font(
            family="TkDefaultFont",
            size=size if size is not None else NMBUPromptFont.FONT_SIZE,
            weight=weight if weight is not None else NMBUPromptFont.FONT_WEIGHT
        )

class NMBUButtonStyle:
    """
    Centralizes button style for all NMBU popups.
    """

    DEFAULT_FONT_WEIGHT = "bold"
    DEFAULT_FONT_SIZE = 10
    DEFAULT_BUTTON_WIDTH = 8 # Tkinter Button width is in characters, so 8 is number of chars that fit comfortably in the selected button size
    DEFAULT_BUTTON_HEIGHT = 1 # Tkinter Button height is in text lines, so 1 is standard single-line button
    DEFAULT_BORDERWIDTH = 2

    # These should match Popup's color scheme
    PRIMARY_GREEN = "#025C4F"
    SECONDARY_GREEN = "#008571"
    WHITE = "#FFFFFF"

    @staticmethod
    def create(parent, text, command, width=None, height=None, borderwidth=None, font_size=None, font_weight=None):
        """
        Create and return a styled tk.Button for NMBU popups.
        Args:
            parent: Parent widget.
            text: Button text.
            command: Button command callback.
            width: Button width in characters (overrides default if provided).
            height: Button height in lines (overrides default if provided).
            borderwidth: Button border width (overrides default if provided).
        Returns:
            tk.Button instance with NMBU style applied.
        """

        font = tkfont.Font(
            family="TkDefaultFont",
            size=font_size if font_size is not None else NMBUButtonStyle.DEFAULT_FONT_SIZE,
            weight=font_weight if font_weight is not None else NMBUButtonStyle.DEFAULT_FONT_WEIGHT
        )

        opts = {
            "font": font,
            "bg": NMBUButtonStyle.PRIMARY_GREEN,
            "fg": NMBUButtonStyle.WHITE,
            "activebackground": NMBUButtonStyle.SECONDARY_GREEN,
            "activeforeground": NMBUButtonStyle.WHITE,
            "relief": "raised",
            "bd": borderwidth if borderwidth is not None else NMBUButtonStyle.DEFAULT_BORDERWIDTH,
            "width": width if width is not None else NMBUButtonStyle.DEFAULT_BUTTON_WIDTH,
            "height": height if height is not None else NMBUButtonStyle.DEFAULT_BUTTON_HEIGHT,
        }

        return tk.Button(parent, text=text, command=command, **opts)

class Popup(tk.Toplevel):

    """
    General popup base class for NMBU apps.
    Provides workplace color constants, default font, and utility methods for consistent look.
    Subclasses should use the provided style/color/font helpers for all widgets.
    """
    # Workplace style colors (NMBU branding)
    PRIMARY_GREEN = "#025C4F"
    SECONDARY_GREEN = "#008571"
    WHITE = "#FFFFFF"

    def __init__(self, parent, title: str, window_width, window_height):
        """
        Args:
            parent: Parent window (usually root or another Toplevel).
            title: Window title.
            window_width: Width of the window.
            window_height: Height of the window.
        """
        super().__init__(parent)

        self._parent = parent
        self._title = title
        self._window_width = window_width
        self._window_height = window_height

        self._result = None

        self.withdraw()  # Hide window until fully positioned

        self.title(title)
        self.resizable(False, False)
        self.grab_set()

        self._set_geometry()

        self._setup_style()

        self._default_font = tkfont.nametofont("TkDefaultFont")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Center all content horizontally in the popup
        self.grid_columnconfigure(0, weight=1)

        # Subclasses should call self._build() to construct the UI after initialization
        self.deiconify()  # Show the window after setup

    @property
    def result(self):
        return self._result

    @property
    def default_font(self):
        return self._default_font

    @property
    def primary_green(self):
        return self.PRIMARY_GREEN

    @property
    def secondary_green(self):
        return self.SECONDARY_GREEN

    @property
    def white(self):
        return self.WHITE

    @result.setter
    def result(self, value):
        self._result = value

    def _build_prompt_section(self, row, text,
                              title=None, text_font=None, title_font=None,
                              text_size=None, title_size=None,
                              fg=None, bg=None,
                              wraplength=440, pady=(16, 12), padx=20,
                              anchor="w", justify="left"):
        """
        Build a labeled prompt/info section (e.g., context, issue, action) in a frame.
        Args:
            row: grid row to place the frame in.
            title: Section title (e.g., 'Context info:').
            text: Section body text.
            title_font: Font for the title label.
            text_font: Font for the body text.
            bg: Background color.
            fg: Foreground/text color for both labels.
            wraplength: Max label width in pixels.
            pady: Vertical padding for the frame.
            padx: Horizontal padding for the frame.
            anchor: Anchor for label packing (default: 'w').
            justify: Text justification (default: 'left').
        Returns: The frame containing the section.
        """
        if bg is None:
            bg = self.secondary_green

        if fg is None:
            fg = self.white

        if text_font is None:
            text_font = NMBUPromptFont.get(size=text_size or 12)

        if title_font is None:
            title_font = NMBUPromptFont.get(weight="bold", size=title_size or 12)

        section_frame = tk.Frame(self, bg=bg or self.secondary_green)
        section_frame.grid(row=row, column=0, padx=padx, pady=pady, sticky="nsew")
        if title is not None:
            tk.Label(
                section_frame,
                text=title,
                wraplength=wraplength,
                justify=justify,
                anchor=anchor,
                bg=bg,
                font=title_font,
                fg=fg
            ).pack(anchor=anchor)

        # Always create the body text label, even if text is empty, to maintain consistent spacing
        tk.Label(
            section_frame,
            text=text,
            wraplength=wraplength,
            justify=justify,
            anchor=anchor,
            bg=bg,
            font=text_font,
            fg=fg
        ).pack(anchor=anchor)
        return section_frame

    def _build_entry_section(self, row=1, entry_width=30, default=None,
                             justify="center", font=None, fg=None, bg="white",
                             insertbackground="black", pady=(0, 10), padx=20):
        """
        Build a single entry field in its own frame at the given row.
        row: grid row to place the entry frame in.
        width: Entry width (characters)
        height: Entry height (not used by tk.Entry, but can be used for ttk.Entry or custom widgets)
        default: Default value to insert
        justify: Text justification
        font: Font to use (defaults to NMBUEntryFont)
        fg: Foreground color
        bg: Background color
        insertbackground: Cursor color
        pady: vertical padding for the entry frame
        padx: horizontal padding for the entry frame
        Returns (entry_frame, entry_widget)
        """
        entry_frame = tk.Frame(self, bg=self.secondary_green)
        entry_frame.grid(row=row, column=0, padx=padx, pady=pady, sticky="nsew")
        entry_font = font or NMBUEntryFont.get()
        entry_opts = {
            "width": entry_width,
            "justify": justify,
            "font": entry_font,
            "fg": fg or NMBUEntryFont.FONT_COLOR,
            "bg": bg,
            "insertbackground": insertbackground
        }
        entry = tk.Entry(entry_frame, **entry_opts)
        entry.pack()
        if default is not None:
            entry.insert(0, default)
        entry.focus_set()
        return entry_frame, entry

    def _build_entry_error_section(self, row, pady=(0, 10), padx=20,
                                   font=None, fg="red", bg=None):
        """
        Build a frame containing an error label for entry validation feedback.
        row: grid row to place the error frame in.
        pady: vertical padding for the error frame.
        padx: horizontal padding for the error frame.
        font: Font for the error label (defaults to self.default_font).
        fg: Foreground color for the error label (default: red).
        bg: Background color for the error frame (defaults to self.secondary_green).
        Returns (error_frame, error_label)
        """
        error_frame = tk.Frame(self, bg=bg if bg is not None else self.secondary_green)
        error_frame.grid(row=row, column=0, padx=padx, pady=pady, sticky="nsew")
        error_font = font or tkfont.Font(family=self.default_font.actual("family"), size=self.default_font.actual("size"), weight="bold")
        error_label = tk.Label(
            error_frame,
            text="",
            fg=fg,
            font=error_font,
            bg=bg if bg is not None else self.secondary_green
        )
        error_label.pack()
        return error_frame, error_label

    def _build_button_section(self, button_defs, row,
                              pady=(15, 15), padx=10,
                              button_width=None, button_height=None,
                              borderwidth=None, font_size=None, font_weight=None):
        """
        Build a row of buttons at the given row.
        button_defs: list of (label, callback) tuples.
        row: grid row to place the button frame in.
        pady: vertical padding for the button frame. form (top, bottom) or single value for both.
        padx: horizontal padding for each button.
        button_width: button width in characters (overrides default if provided).
        button_height: button height in lines (overrides default if provided).
        borderwidth: button border width (overrides default if provided).
        font_size: button font size (overrides default if provided).
        font_weight: button font weight (overrides default if provided).
        Returns the button_frame for further customization if needed.
        """
        button_frame = tk.Frame(self, bg=self.secondary_green)
        button_frame.grid(row=row, column=0, pady=pady)
        for i, (label, callback) in enumerate(button_defs):
            NMBUButtonStyle.create(
                button_frame, label, callback,
                width=button_width, height=button_height,
                borderwidth=borderwidth, font_size=font_size, font_weight=font_weight
            ).grid(row=0, column=i, padx=padx)
        return button_frame

    def _set_geometry(self):

        self.minsize(self._window_width, self._window_height)
        self.update_idletasks()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (self._window_width // 2)
        y = (hs // 2) - (self._window_height // 2)
        self.geometry(f"{self._window_width}x{self._window_height}+{x}+{y}")

    def _setup_style(self):
        """
        Set the background color of the popup window to secondary green (light green).
        Override in subclasses for custom backgrounds.
        """
        self.configure(bg=self.secondary_green)

    def _on_close(self):
        """
        Default close handler for the popup. Sets result to None and destroys the window.
        Subclasses can override or extend this method for custom close behavior.
        """
        self.result = None
        self.destroy()