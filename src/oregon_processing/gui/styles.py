import tkinter as tk
import tkinter.font as tkfont
from tkinter.font import Font

PRIMARY_GREEN = "#025C4F"
SECONDARY_GREEN = "#008571"
PRIMARY_BLUE = "#53143A"
BLACK = "#000000"
WHITE = "#FFFFFF"

class NormalFont:
    """
    Centralizes normal font for NMBU popups.
    Use get() to obtain a normal font for labels and text.
    """
    FONT_SIZE = 12
    FONT_WEIGHT = "normal"

    @classmethod
    def create(cls, size=None, weight=None):
        """
        Returns a tkfont.Font for normal text.
        Optional size and weight override class defaults.
        """
        return tkfont.Font(
            family="TkDefaultFont",
            size=size if size is not None else cls.FONT_SIZE,
            weight=weight if weight is not None else cls.FONT_WEIGHT
        )

class StandardButtonStyle:


    DEFAULT_FONT_WEIGHT = "bold"
    DEFAULT_FONT_SIZE = 10
    DEFAULT_BUTTON_WIDTH = 8 # Tkinter Button width is in characters, so 8 is number of chars that fit comfortably in the selected button size
    DEFAULT_BUTTON_HEIGHT = 1 # Tkinter Button height is in text lines, so 1 is standard single-line button
    DEFAULT_BORDERWIDTH = 2
    DEFAULT_FG = WHITE
    DEFAULT_BG = PRIMARY_GREEN
    DEFAULT_ACTIVE_FG = WHITE
    DEFAULT_ACTIVE_BG = SECONDARY_GREEN
    DEFAULT_BUTTON_TEXT_SIZE = 10
    DEFAULT_BUTTON_TEXT_WEIGHT = "bold"


    @classmethod
    def create(cls, parent: tk.Widget, button_text: str, command: callable, **kwargs) -> tk.Button:

        button_width = kwargs.get("button_width")
        if button_width is None:
            button_width = cls.DEFAULT_BUTTON_WIDTH
        button_height = kwargs.get("button_height")
        if button_height is None:
            button_height = cls.DEFAULT_BUTTON_HEIGHT
        button_borderwidth = kwargs.get("button_borderwidth")
        if button_borderwidth is None:
            button_borderwidth = cls.DEFAULT_BORDERWIDTH
        button_text_size = kwargs.get("button_text_size")
        if button_text_size is None:
            button_text_size = cls.DEFAULT_BUTTON_TEXT_SIZE
        button_text_weight = kwargs.get("button_text_weight")
        if button_text_weight is None:
            button_text_weight = cls.DEFAULT_BUTTON_TEXT_WEIGHT
        button_text_color = kwargs.get("button_text_color")
        if button_text_color is None:
            button_text_color = cls.DEFAULT_FG
        button_text_font = kwargs.get("button_text_font")
        if button_text_font is None:
            button_text_font = NormalFont.create(size=button_text_size, weight=button_text_weight)
        button_bg = kwargs.get("button_bg")
        if button_bg is None:
            button_bg = cls.DEFAULT_BG
        active_fg = kwargs.get("button_active_fg")
        if active_fg is None:
            active_fg = cls.DEFAULT_ACTIVE_FG
        active_bg = kwargs.get("button_active_bg")
        if active_bg is None:
            active_bg = cls.DEFAULT_ACTIVE_BG

        if not isinstance(parent, tk.Widget):
            raise TypeError("parent must be a tkinter Widget")
        if not isinstance(button_text, str):
            raise TypeError("button_text must be a string")
        if not callable(command):
            raise TypeError("command must be callable")
        if button_width is not None and not isinstance(button_width, int):
            raise TypeError("button_width must be an integer or None")
        if button_height is not None and not isinstance(button_height, int):
            raise TypeError("button_height must be an integer or None")
        if button_borderwidth is not None and not isinstance(button_borderwidth, int):
            raise TypeError("button_borderwidth must be an integer or None")
        if button_text_font is not None and not isinstance(button_text_font, Font):
            raise TypeError("button_text_font must be a tkinter Font or None")
        if button_text_size is not None and not isinstance(button_text_size, int):
            raise TypeError("button_text_size must be an integer or None")
        if button_text_weight is not None and not isinstance(button_text_weight, str):
            raise TypeError("button_text_weight must be a string or None")
        if button_text_color is not None and not isinstance(button_text_color, str):
            raise TypeError("button_text_color must be a string or None")
        if button_bg is not None and not isinstance(button_bg, str):
            raise TypeError("button_bg must be a string or None")
        if active_fg is not None and not isinstance(active_fg, str):
            raise TypeError("button_active_fg must be a string or None")
        if active_bg is not None and not isinstance(active_bg, str):
            raise TypeError("button_active_bg must be a string or None")

        opts = {
            "font": button_text_font,
            "bg": button_bg,
            "fg": button_text_color,
            "activebackground": active_bg,
            "activeforeground": active_fg,
            "relief": "raised",
            "bd": button_borderwidth,
            "width": button_width,
            "height": button_height,
        }

        return tk.Button(parent, text=button_text, command=command, **opts)
