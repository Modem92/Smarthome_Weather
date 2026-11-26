"""Pillow/Tk bridge with native PNG fallback for Debian's split ImageTk package."""
import base64
from io import BytesIO

try:
    from PIL import ImageTk as _image_tk
except ImportError:
    _image_tk = None


def photo_image(image, *, master):
    if _image_tk is not None:
        return _image_tk.PhotoImage(image, master=master)
    import tkinter as tk
    data=BytesIO()
    image.save(data,format='PNG')
    return tk.PhotoImage(master=master,data=base64.b64encode(data.getvalue()),format='png')
