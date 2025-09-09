import sys
import os

# def resource_path(relative_path: str) -> str:
#     """Get the absolute path to a resource, works for dev and PyInstaller."""
#     if hasattr(sys, '_MEIPASS'):
#         # Running as a PyInstaller executable
#         return os.path.join(sys._MEIPASS, relative_path)
#     return os.path.join(os.path.abspath("."), relative_path)

def resource_path(relative_path: str) -> str:
    """Return absolute path to resource inside the 'resources' folder."""
    base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.abspath(".")
    return os.path.join(base, "resources", relative_path)
