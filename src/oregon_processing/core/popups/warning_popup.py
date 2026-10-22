import tkinter as tk
from tkinter import messagebox


def show_warning_popup(message: str, title: str = "Warning") -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showwarning(title, message, parent=root)
    finally:
        root.destroy()
