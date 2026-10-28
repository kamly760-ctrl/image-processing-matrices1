"""
matrix_ops.py - the core of the project
=======================================
Every image operation here is plain NumPy matrix math.
Pillow is used only to read an image file into a matrix.

A color image is a matrix of shape (H, W, 3):  H rows, W columns, and 3 numbers
per pixel (Red, Green, Blue), each from 0 to 255.  A gray image is (H, W).
"""

import numpy as np
from PIL import Image, ImageOps

GRAY_WEIGHTS = np.array([0.299, 0.587, 0.114])  # how much the eye "feels" R, G, B


def load_image_matrix(path):
    """Read an image file and return it as a matrix of shape (H, W, 3), values 0..255."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return np.asarray(img, dtype=np.uint8).copy()


def to_grayscale(m):
    """(H, W, 3) -> (H, W).  gray = 0.299*R + 0.587*G + 0.114*B  (a weighted sum)."""
    if m.ndim == 2:  # already gray
        return m
    gray = m[..., :3].astype(np.float64) @ GRAY_WEIGHTS
    return np.clip(np.rint(gray), 0, 255).astype(np.uint8)


def adjust_brightness(m, value):
    """Add `value` (negative = darker) to every element, then clip to 0..255."""
    # int16 so that 250 + 20 does not overflow before clipping (uint8 would wrap around)
    return np.clip(m.astype(np.int16) + value, 0, 255).astype(np.uint8)


def flip_horizontal(m):
    """Reverse the order of the columns in every row:  out[:, j] = in[:, W-1-j]."""
    return np.ascontiguousarray(m[:, ::-1])


def to_black_white(m, threshold):
    """Gray first, then every pixel becomes 255 (white) if gray >= threshold, else 0 (black)."""
    gray = to_grayscale(m)
    return np.where(gray >= threshold, 255, 0).astype(np.uint8)


def run_pipeline(m, brightness=0, gray=False, bw=False, thresh=128, flip=False):
    """Apply the selected operations in a fixed order and return the new matrix."""
    out = m
    if brightness != 0:
        out = adjust_brightness(out, brightness)
    if gray or bw:
        out = to_grayscale(out)
    if bw:
        out = to_black_white(out, thresh)
    if flip:
        out = flip_horizontal(out)
    return out
