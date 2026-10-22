from tkinter import messagebox

from oregon_processing.gui.root import get_root


def show_warning_popup(message: str, title: str = "Warning") -> None:
    root = get_root()
    root.withdraw()
    root.lift()
    root.attributes('-topmost', True)
    messagebox.showwarning(title, message, parent=root)
