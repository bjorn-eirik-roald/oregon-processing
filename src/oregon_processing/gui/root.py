import atexit

_root = None

def get_root():
    global _root
    if _root is None:
        import tkinter as tk
        _root = tk.Tk()
        _root.withdraw()
    return _root


def shutdown_gui():
    global _root
    if _root is not None:
        _root.destroy()
        _root = None


# ✅ runs immediately on import
atexit.register(shutdown_gui)