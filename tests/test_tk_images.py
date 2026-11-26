"""Exercise native Tk PNG transfer when Debian's optional ImageTk is absent."""
import gc
import tkinter as tk
import unittest
from unittest.mock import patch
from PIL import Image
from wetterstation.ui.tk_images import photo_image


class TkImageTests(unittest.TestCase):
    def test_native_fallback_preserves_size_color_and_transparency(self):
        root=tk.Tk();root.withdraw()
        try:
            pixels=Image.new('RGBA',(3,2),(250,20,70,255))
            pixels.putpixel((2,1),(0,0,0,0))
            with patch('wetterstation.ui.tk_images._image_tk',None):
                photo=photo_image(pixels,master=root)
            self.assertEqual((photo.width(),photo.height()),(3,2))
            self.assertEqual(photo.get(0,0),(250,20,70))
            self.assertTrue(photo.transparency_get(2,1))
            del photo
        finally:
            root.update_idletasks();root.destroy();gc.collect()
