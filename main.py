"""
Image Processing Using Matrices  -  by COGNIX team
==================================================
Desktop program: load a real image, treat it as a NumPy matrix, apply matrix
operations, and show Original vs Processed side by side.

    python main.py

The matrix operations are in matrix_ops.py. This file is the interface
(animated splash screen + main window).
"""

import math
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk
import customtkinter as ctk

from matrix_ops import load_image_matrix, run_pipeline  # the matrix math lives in matrix_ops.py


# =====================================================================
# 1) BRAND, COLORS, SETTINGS
# =====================================================================

TEAM_NAME = "COGNIX"
LOGO_FILES = ["COGNIX.png", "cognix_logo.png", "team_logo.png"]  # first one found is used
SHOW_SPLASH = True
SPLASH_SPEED = 1.0       # 1.0 = about 4.3 seconds, 2.0 = twice as fast

# colors taken from the COGNIX logo
VIOLET = (139, 61, 255)
BLUE = (70, 90, 255)
CYAN = (34, 199, 245)

BG = "#080B16"
SIDE = "#0C1020"
SURFACE = "#111631"
LINE = "#1D2447"
TEXT = "#E9ECFA"
MUTED = "#8B94BA"
ACCENT = "#5B6BFF"
ACCENT_HOVER = "#4859E8"
SECONDARY = "#1A2142"
SECONDARY_HOVER = "#242D58"

CHANNEL_HUES = {"R": (255, 82, 82), "G": (72, 214, 120), "B": (86, 148, 255), "Gray": (226, 229, 236)}

PREVIEW_MAX = 1100  # live preview works on a downscaled copy so sliders stay smooth
MATRIX_N = 7        # size of the pixel-value grid

if sys.platform == "win32":
    UI_FONT, MONO_FONT = "Segoe UI", "Consolas"
elif sys.platform == "darwin":
    UI_FONT, MONO_FONT = "Helvetica Neue", "Menlo"
else:
    UI_FONT, MONO_FONT = "DejaVu Sans", "DejaVu Sans Mono"


def blend(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def hex_rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def rgb_hex(c):
    return "#%02x%02x%02x" % c


def brand_gradient(u):
    """Violet -> blue -> cyan, u from 0 to 1."""
    u = min(max(u, 0.0), 1.0)
    return blend(VIOLET, BLUE, u * 2) if u < 0.5 else blend(BLUE, CYAN, (u - 0.5) * 2)


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def seg(t, a, b):
    """0 before time a, 1 after time b, linear in between."""
    return clamp01((t - a) / (b - a))


def ease_out(x):
    return 1 - (1 - x) ** 3


def smooth(x):
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- logo
def load_font(size, bold=False):
    names = (["segoeuib.ttf", "arialbd.ttf", "/System/Library/Fonts/Helvetica.ttc", "DejaVuSans-Bold.ttf"]
             if bold else
             ["segoeui.ttf", "arial.ttf", "/System/Library/Fonts/Helvetica.ttc", "DejaVuSans.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _trim(img):
    box = img.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    return img.crop(box) if box else img


def split_logo(img):
    """Split the logo image into (mark, wordmark) at the biggest empty horizontal gap."""
    img = _trim(img)
    if img.width > 1600:
        img = img.resize((1600, int(img.height * 1600 / img.width)), Image.Resampling.LANCZOS)
    occupied = (np.asarray(img.getchannel("A")) > 20).any(axis=1)
    best, start = None, None
    for i, v in enumerate(list(occupied) + [True]):
        if not v and start is None:
            start = i
        elif v and start is not None:
            if start > img.height * 0.2 and i < img.height * 0.95 and i - start > img.height * 0.02:
                if best is None or i - start > best[1] - best[0]:
                    best = (start, i)
            start = None
    if best is None:
        return img, None
    return _trim(img.crop((0, 0, img.width, best[0]))), _trim(img.crop((0, best[1], img.width, img.height)))


def make_fallback_logo():
    """Used only if the logo file is missing: a gradient badge and a text wordmark."""
    s = 300
    u = np.add.outer(np.arange(s), np.arange(s)) / (2.0 * s)
    px = np.zeros((s, s, 4), np.uint8)
    for ch in range(3):
        px[..., ch] = np.interp(u, [0, 0.5, 1], [VIOLET[ch], BLUE[ch], CYAN[ch]])
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=80, fill=255)
    px[..., 3] = np.asarray(mask)
    mark = Image.fromarray(px, "RGBA")
    ImageDraw.Draw(mark).text((s // 2, s // 2), TEAM_NAME[:1].upper(), font=load_font(190, True),
                              fill=(255, 255, 255, 255), anchor="mm")
    font = load_font(90, True)
    word = Image.new("RGBA", (900, 140), (0, 0, 0, 0))
    d, x = ImageDraw.Draw(word), 10
    for ch in TEAM_NAME.upper():
        d.text((x, 70), ch, font=font, fill=(240, 244, 255, 255), anchor="lm")
        x += font.getlength(ch) + 26
    return mark, _trim(word)


def resource_path(*parts):
    """Path to a bundled file; works from source and from a PyInstaller build."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def load_logo():
    for name in LOGO_FILES:
        for folder in ("assets", ""):
            path = resource_path(folder, name)
            if os.path.exists(path):
                try:
                    return split_logo(Image.open(path).convert("RGBA"))
                except Exception:
                    pass
    return make_fallback_logo()


# =====================================================================
# 2) ANIMATED SPLASH SCREEN
#    SplashRenderer draws one frame for a given time t (pure Pillow + NumPy).
#    SplashScreen shows those frames in a borderless window and fades into the app.
# =====================================================================

def paste(dst, src, x, y):
    """alpha_composite that safely clips against the edges of dst."""
    x, y = int(x), int(y)
    w, h = src.size
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(w, dst.width - x), min(h, dst.height - y)
    if right <= left or bottom <= top:
        return
    if (left, top, right, bottom) != (0, 0, w, h):
        src = src.crop((left, top, right, bottom))
    dst.alpha_composite(src, (x + left, y + top))


class SplashRenderer:
    W0, H0 = 820, 520          # design size in pixels (scaled for high-DPI screens)
    DURATION = 4.3             # seconds, including the exit
    EXIT_START = 3.7

    STATUS = [(0.0, "Loading matrix engine"), (0.30, "Preparing the interface"),
              (0.62, "Almost ready"), (0.97, "Ready")]

    def __init__(self, mark, word, scale=1.0):
        S = self.S = float(scale)
        self.W, self.H = int(round(self.W0 * S)), int(round(self.H0 * S))
        self.ss = 2 if S < 1.3 else 1            # supersampling for smooth network lines
        self.cx, self.cy = self.W // 2, int(150 * S)
        self._lut_cache = {}
        self._build_background()
        self._build_network()
        self._build_logo(mark, word)
        self._build_texts()
        self._build_bar()

    # ---------------------------------------------------- static pieces
    def _build_background(self):
        W, H, S = self.W, self.H, self.S
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

        def glow(cx, cy, r, color, k):
            d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
            return np.exp(-d2 * 1.6)[..., None] * np.array(color, np.float32) * k

        t = (yy / H)[..., None]
        base = np.concatenate([6 + 4 * t, 8 + 5 * t, 22 + 18 * t], axis=-1)
        base += glow(self.cx, self.cy, 330 * S, (70, 45, 170), 0.55)
        base += glow(W * 0.88, H * 0.92, 300 * S, (10, 70, 110), 0.45)
        base += glow(W * 0.08, H * 0.08, 260 * S, (45, 25, 95), 0.35)
        self.bg = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

        # keeps the network quieter around the logo and at the window edges
        d = np.sqrt((xx - self.cx) ** 2 + (yy - self.cy) ** 2) / (250 * S)
        v = 0.28 + 0.72 * np.clip(d, 0, 1) ** 1.5
        edge = np.clip(np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / (40 * S), 0, 1)
        self.vign = Image.fromarray((np.clip(v * (0.4 + 0.6 * edge), 0, 1) * 255).astype(np.uint8), "L")

        # soft light behind the logo
        d2 = ((xx - self.cx) ** 2 + (yy - self.cy) ** 2) / ((150 * S) ** 2)
        a = np.exp(-d2 * 1.2) * 0.42 + np.exp(-d2 * 5) * 0.10
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., 0], arr[..., 1], arr[..., 2] = 105, 95, 255
        arr[..., 3] = np.clip(a * 255, 0, 255)
        self.glow = Image.fromarray(arr, "RGBA")

    def _build_network(self):
        W, H, S = self.W, self.H, self.S
        rng = np.random.default_rng(7)
        n = 48
        self.n = n
        self.bp = np.stack([rng.uniform(0.04 * W, 0.96 * W, n), rng.uniform(0.05 * H, 0.95 * H, n)], 1)
        self.amp = rng.uniform(10, 26, (n, 2)) * S
        self.wv = rng.uniform(0.35, 0.9, (n, 2))
        self.ph = rng.uniform(0, 2 * math.pi, (n, 2))
        self.rad = rng.uniform(1.4, 3.0, n) * S
        d0 = np.sqrt(((self.bp[:, None] - self.bp[None]) ** 2).sum(-1))
        cand = [(i, j) for i in range(n) for j in range(i + 1, n) if d0[i, j] < 140 * S]
        rng.shuffle(cand)
        self.pulses = [(i, j, rng.uniform(), rng.uniform(0.35, 0.7)) for i, j in cand[:16]]

    def _build_logo(self, mark, word):
        S = self.S
        self.mark_h = int(200 * S)
        mh = int(self.mark_h * 1.15)
        self.mark_big = mark.resize((int(mh * mark.width / mark.height), mh), Image.Resampling.LANCZOS)
        self.mark_ar = mark.width / mark.height
        if word is not None:
            ww = int(400 * S)
            self.word = word.resize((ww, max(1, int(ww * word.height / word.width))), Image.Resampling.LANCZOS)
            self.word_alpha = self.word.getchannel("A")
        else:
            self.word = None
        self.word_y = int(322 * S)

    def _sprite(self, parts, size):
        """Text sprite from [(text, (r,g,b), bold), ...] laid out on one line."""
        S = self.S
        fonts = [load_font(max(8, int(size * S)), b) for _, _, b in parts]
        widths = [f.getlength(t) for (t, _, _), f in zip(parts, fonts)]
        h = int(size * S * 1.6)
        spr = Image.new("RGBA", (int(sum(widths)) + 6, h), (0, 0, 0, 0))
        d, x = ImageDraw.Draw(spr), 3
        for (t, c, _), f, w in zip(parts, fonts, widths):
            d.text((x, h // 2), t, font=f, fill=c + (255,), anchor="lm")
            x += w
        return spr

    def _build_texts(self):
        self.t_made = self._sprite([("Made by ", (154, 163, 204), False),
                                    (f"{TEAM_NAME} team", (240, 243, 255), True)], 16)
        self.t_project = self._sprite([("Image Processing Using Matrices", (110, 120, 166), False)], 13)
        self.t_status = [(th, self._sprite([(txt, (125, 135, 180), False)], 12)) for th, txt in self.STATUS]
        self.font_pct = load_font(max(8, int(12 * self.S)), True)

    def _build_bar(self):
        S = self.S
        self.bar_w = int(360 * S)
        self.bar_h = max(2, int(3 * S))
        self.bar_x = self.cx - self.bar_w // 2
        self.bar_y = int(462 * S)
        strip = np.zeros((self.bar_h, self.bar_w, 4), np.uint8)
        for x in range(self.bar_w):
            strip[:, x, :3] = brand_gradient(x / self.bar_w)
        strip[..., 3] = 255
        self.bar_fill = Image.fromarray(strip, "RGBA")
        g = int(40 * S)
        yy, xx = np.mgrid[0:g, 0:g].astype(np.float32)
        d2 = ((xx - g / 2) ** 2 + (yy - g / 2) ** 2) / ((g / 2) ** 2)
        arr = np.zeros((g, g, 4), np.uint8)
        arr[..., :3] = (150, 225, 255)
        arr[..., 3] = np.clip(np.exp(-d2 * 4) * 255, 0, 255)
        self.bar_head = Image.fromarray(arr, "RGBA")

    # --------------------------------------------------------- helpers
    def _faded(self, img, k):
        if k >= 0.995:
            return img
        key = int(k * 64)
        lut = self._lut_cache.get(key)
        if lut is None:
            lut = self._lut_cache[key] = [int(i * key / 64) for i in range(256)]
        out = img.copy()
        out.putalpha(img.getchannel("A").point(lut))
        return out

    @staticmethod
    def progress(t):
        return float(np.interp(t, [0.5, 1.3, 2.1, 2.9, 3.4, 3.7], [0, 0.22, 0.50, 0.76, 0.95, 1.0]))

    def exit_progress(self, t):
        return smooth(seg(t, self.EXIT_START, self.DURATION))

    # ------------------------------------------------------- animated bits
    def _network(self, t, fade):
        W, H, S, ss = self.W, self.H, self.S, self.ss
        pos = self.bp + self.amp * np.stack([np.sin(self.wv[:, 0] * t + self.ph[:, 0]),
                                             np.cos(self.wv[:, 1] * t + self.ph[:, 1])], 1)
        d = np.sqrt(((pos[:, None] - pos[None]) ** 2).sum(-1))
        thr = 150 * S
        ii, jj = np.where(np.triu(d < thr, 1))
        layer = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        lw = max(1, int(round(1.3 * S * ss)))
        for i, j in zip(ii, jj):
            a = 1 - d[i, j] / thr
            col = brand_gradient((pos[i, 0] + pos[j, 0]) / 2 / W)
            dr.line([(pos[i, 0] * ss, pos[i, 1] * ss), (pos[j, 0] * ss, pos[j, 1] * ss)],
                    fill=col + (int(170 * a),), width=lw)
        for k in range(self.n):
            x, y, r = pos[k, 0] * ss, pos[k, 1] * ss, self.rad[k] * ss
            dr.ellipse((x - r, y - r, x + r, y + r), fill=brand_gradient(pos[k, 0] / W) + (210,))
        for i, j, ph, sp in self.pulses:  # little data packets travelling along the lines
            if d[i, j] < thr:
                f = (t * sp + ph) % 1.0
                x = (pos[i, 0] + (pos[j, 0] - pos[i, 0]) * f) * ss
                y = (pos[i, 1] + (pos[j, 1] - pos[i, 1]) * f) * ss
                col = brand_gradient(x / (W * ss))
                for r, al in ((4.5, 60), (2.6, 255)):
                    r *= S * ss
                    dr.ellipse((x - r, y - r, x + r, y + r), fill=col + (al,))
        if ss > 1:
            layer = layer.reduce(ss)
        alpha = ImageChops.multiply(layer.getchannel("A"), self.vign)
        lut = [int(i * fade) for i in range(256)]
        layer.putalpha(alpha.point(lut))
        return layer

    def _ring(self, t, k):
        S, ss = self.S, 2
        half = int(150 * S)
        big = Image.new("RGBA", (half * 2 * ss, half * 2 * ss), (0, 0, 0, 0))
        dr = ImageDraw.Draw(big)
        c, r = half * ss, 128 * S * ss
        box = [c - r, c - r, c + r, c + r]
        dr.ellipse(box, outline=(120, 130, 255, 38), width=max(1, int(1.2 * S * ss)))
        head, span, n = (t * 200) % 360, 140, 40
        for s in range(n):  # sweeping arc: faint violet tail -> bright cyan head
            u = (s + 1) / n
            dr.arc(box, head - span + span * s / n, head - span + span * (s + 1) / n + 1.5,
                   fill=brand_gradient(u) + (int(255 * u ** 1.6),), width=max(2, int(3 * S * ss)))
        return self._faded(big.reduce(ss), k)

    # ---------------------------------------------------------------- frame
    def render(self, t):
        W, H, S = self.W, self.H, self.S
        frame = self.bg.copy()

        paste(frame, self._network(t, ease_out(seg(t, 0.0, 0.8))), 0, 0)

        k_mark = ease_out(seg(t, 0.2, 1.1))
        pulse = 0.75 + 0.25 * math.sin(t * 2.2)
        paste(frame, self._faded(self.glow, k_mark * pulse), 0, 0)

        k_ring = ease_out(seg(t, 0.4, 1.1)) * (1 - 0.55 * seg(t, 3.2, 3.7))
        if k_ring > 0:
            half = int(150 * S)
            paste(frame, self._ring(t, k_ring), self.cx - half, self.cy - half)

        scale = 0.84 + 0.16 * ease_out(seg(t, 0.2, 1.1))
        mh = int(self.mark_h * scale)
        mw = int(mh * self.mark_ar)
        if mh > 0 and k_mark > 0:
            spr = self._faded(self.mark_big.resize((mw, mh), Image.Resampling.BICUBIC), k_mark)
            paste(frame, spr, self.cx - mw // 2, self.cy - mh // 2 + math.sin(t * 1.7) * 3 * S)

        if self.word is not None:
            e = smooth(seg(t, 0.9, 1.6))
            if e > 0:
                ww, wh = self.word.size
                u = np.arange(ww) / ww
                m = np.clip((e * 1.15 - u) / 0.15, 0, 1)
                mask = Image.fromarray((np.tile(m, (wh, 1)) * 255).astype(np.uint8), "L")
                spr = self.word.copy()
                spr.putalpha(ImageChops.multiply(self.word_alpha, mask))
                paste(frame, spr, self.cx - ww // 2, self.word_y - wh // 2 + (1 - e) * 10 * S)

        k1 = ease_out(seg(t, 1.4, 2.0))
        if k1 > 0:
            spr = self._faded(self.t_made, k1)
            paste(frame, spr, self.cx - spr.width // 2, int(372 * S) - spr.height // 2 + (1 - k1) * 8 * S)
        k2 = ease_out(seg(t, 1.65, 2.25))
        if k2 > 0:
            spr = self._faded(self.t_project, k2)
            paste(frame, spr, self.cx - spr.width // 2, int(398 * S) - spr.height // 2 + (1 - k2) * 8 * S)

        self._draw_bar(frame, t)

        dr = ImageDraw.Draw(frame)
        dr.rectangle((0, 0, W - 1, H - 1), outline=(31, 38, 80, 255), width=max(1, int(S)))

        img = frame.convert("RGB")
        e = self.exit_progress(t)
        if e > 0:  # slight push-in while the window fades out
            z = 1 + 0.06 * e
            big = img.resize((int(W * z), int(H * z)), Image.Resampling.BILINEAR)
            lft, top = (big.width - W) // 2, (big.height - H) // 2
            img = big.crop((lft, top, lft + W, top + H))
        return img

    def _draw_bar(self, frame, t):
        S = self.S
        kb = ease_out(seg(t, 0.5, 1.0))
        if kb <= 0:
            return
        p = self.progress(t)
        track = blend((10, 13, 38), (27, 33, 70), kb)
        dr = ImageDraw.Draw(frame)
        dr.rectangle((self.bar_x, self.bar_y, self.bar_x + self.bar_w, self.bar_y + self.bar_h - 1), fill=track + (255,))
        fw = int(self.bar_w * p)
        if fw > 0:
            paste(frame, self._faded(self.bar_fill.crop((0, 0, fw, self.bar_h)), kb), self.bar_x, self.bar_y)
            head = self._faded(self.bar_head, kb * (1 - seg(t, 3.4, 3.7)))
            paste(frame, head, self.bar_x + fw - head.width // 2, self.bar_y + self.bar_h // 2 - head.height // 2)
        status = [s for th, s in self.t_status if p >= th][-1]
        paste(frame, self._faded(status, kb), self.bar_x - 3, self.bar_y + int(20 * S) - status.height // 2)
        txt = f"{int(round(p * 100))}%"
        pct = Image.new("RGBA", (int(60 * S), int(24 * S)), (0, 0, 0, 0))
        ImageDraw.Draw(pct).text((pct.width - 2, pct.height // 2), txt, font=self.font_pct,
                                 fill=(160, 170, 215, 255), anchor="rm")
        paste(frame, self._faded(pct, kb), self.bar_x + self.bar_w - pct.width + 3,
              self.bar_y + int(20 * S) - pct.height // 2)


class SplashScreen:
    """Borderless window that plays the renderer, then cross-fades into the main window."""

    def __init__(self, app, mark, word, on_done):
        self.app, self.on_done = app, on_done
        scale = min(2.0, max(1.0, app.winfo_fpixels("1i") / 96.0))
        self.r = SplashRenderer(mark, word, scale)
        self.top = tk.Toplevel(app)
        self.top.overrideredirect(True)
        self.top.configure(bg="#070A18")
        x = (self.top.winfo_screenwidth() - self.r.W) // 2
        y = (self.top.winfo_screenheight() - self.r.H) // 2
        self.top.geometry(f"{self.r.W}x{self.r.H}+{x}+{y}")
        self._alpha(self.top, 1.0)
        try:
            self.top.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.label = tk.Label(self.top, bd=0, highlightthickness=0, bg="#070A18")
        self.label.pack(fill="both", expand=True)
        self.shown_app = False
        self.t0 = time.perf_counter()
        self._frame()

    @staticmethod
    def _alpha(win, v):
        try:
            win.attributes("-alpha", v)
        except tk.TclError:
            pass

    def _frame(self):
        try:
            t = (time.perf_counter() - self.t0) * SPLASH_SPEED
            if t >= self.r.DURATION:
                return self._finish()
            photo = ImageTk.PhotoImage(self.r.render(t))
            self.label.configure(image=photo)
            self.label.image = photo
            e = self.r.exit_progress(t)
            if e > 0:
                if not self.shown_app:  # main window appears (invisible) and fades in
                    self._alpha(self.app, 0.0)
                    self.app.deiconify()
                    self.shown_app = True
                self._alpha(self.app, e)
                self._alpha(self.top, 1 - e)
            self.top.after(1, self._frame)
        except Exception:
            self._finish()

    def _finish(self):
        try:
            self.top.destroy()
        except tk.TclError:
            pass
        self.on_done()


# =====================================================================
# 3) MAIN WINDOW
# =====================================================================

class MatrixGrid(tk.Frame):
    """A small grid that shows real pixel values; each cell is tinted by its value."""

    def __init__(self, master, n=MATRIX_N):
        super().__init__(master, bg=SURFACE)
        self.n = n
        self.cells = []
        for r in range(n):
            row = []
            for c in range(n):
                lbl = tk.Label(self, text="", width=4, height=1, bd=0, font=(MONO_FONT, 10),
                               bg=SURFACE, fg=TEXT)
                lbl.grid(row=r, column=c, padx=1, pady=1, ipady=3)
                row.append(lbl)
            self.cells.append(row)

    def show(self, patch, hue):
        base = hex_rgb(SURFACE)
        rows, cols = (patch.shape if patch is not None else (0, 0))
        for r in range(self.n):
            for c in range(self.n):
                lbl = self.cells[r][c]
                if r < rows and c < cols:
                    v = int(patch[r, c])
                    t = v / 255.0
                    lbl.configure(text=str(v), bg=rgb_hex(blend(base, hue, t)),
                                  fg="#0B0E13" if t > 0.55 else "#F2F4F8")
                else:
                    lbl.configure(text="", bg=SURFACE)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(f"Image Processing Using Matrices  |  {TEAM_NAME}")
        self.geometry("1380x860")
        self.minsize(1120, 760)
        self.configure(fg_color=BG)

        self.mark, self.word = load_logo()
        self.src = None    # full resolution matrix (used when saving)
        self.work = None   # downscaled matrix (used for live preview)
        self.out = None    # processed preview matrix
        self.path = None
        self._job = None
        self._rjob = None
        self._refs = []

        self.v_bright = tk.IntVar(value=0)
        self.v_gray = tk.BooleanVar(value=False)
        self.v_bw = tk.BooleanVar(value=False)
        self.v_thresh = tk.IntVar(value=128)
        self.v_flip = tk.BooleanVar(value=False)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

        self.bind("<Control-o>", lambda e: self.open_image())
        self.bind("<Control-s>", lambda e: self.save_image())
        self.update_formulas()
        self.after(300, self._set_icon)

        if SHOW_SPLASH:
            self.withdraw()  # hide the main window until the splash screen finishes
            self.after(10, self._start_splash)

    def _start_splash(self):
        try:
            SplashScreen(self, self.mark, self.word, self._show_main)
        except Exception:
            self._show_main()

    def _show_main(self):
        try:
            self.attributes("-alpha", 1.0)
        except tk.TclError:
            pass
        self.deiconify()
        self.lift()
        self.focus_force()

    def _set_icon(self):
        try:
            s = max(self.mark.size)
            sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            sq.paste(self.mark, ((s - self.mark.width) // 2, (s - self.mark.height) // 2))
            self._icon = ImageTk.PhotoImage(sq.resize((64, 64), Image.Resampling.LANCZOS))
            self.iconphoto(True, self._icon)
        except Exception:
            pass

    # ------------------------------------------------------------ sidebar
    def _section(self, parent, text):
        ctk.CTkFrame(parent, height=1, fg_color=LINE).pack(fill="x", padx=22, pady=(14, 0))
        ctk.CTkLabel(parent, text=text, text_color=MUTED,
                     font=ctk.CTkFont(UI_FONT, 12), anchor="w").pack(fill="x", padx=22, pady=(9, 3))

    def _build_sidebar(self):
        side = ctk.CTkFrame(self, width=330, corner_radius=0, fg_color=SIDE)
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)
        side.pack_propagate(False)

        # thin brand-gradient line at the very top
        strip = np.zeros((3, 330, 3), np.uint8)
        for x in range(330):
            strip[:, x] = brand_gradient(x / 330)
        simg = Image.fromarray(strip, "RGB")
        self._strip = ctk.CTkImage(light_image=simg, dark_image=simg, size=(330, 3))
        ctk.CTkLabel(side, text="", image=self._strip, height=3).pack(fill="x")

        head = ctk.CTkFrame(side, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(22, 14))
        mh = 46
        mw = int(mh * self.mark.width / self.mark.height)
        self._mark_img = ctk.CTkImage(light_image=self.mark, dark_image=self.mark, size=(mw, mh))
        ctk.CTkLabel(head, text="", image=self._mark_img).pack(side="left", padx=(0, 14))
        txt = ctk.CTkFrame(head, fg_color="transparent")
        txt.pack(side="left")
        ctk.CTkLabel(txt, text="Image Processing", text_color=TEXT, anchor="w",
                     font=ctk.CTkFont(UI_FONT, 20, "bold")).pack(fill="x")
        ctk.CTkLabel(txt, text=f"Made by {TEAM_NAME} team", text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(UI_FONT, 12)).pack(fill="x")

        ctk.CTkButton(side, text="Open image", height=42, corner_radius=8, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, font=ctk.CTkFont(UI_FONT, 14, "bold"),
                      command=self.open_image).pack(fill="x", padx=22)

        # --- brightness
        self._section(side, "Brightness")
        row = ctk.CTkFrame(side, fg_color="transparent")
        row.pack(fill="x", padx=22)
        ctk.CTkLabel(row, text="Add to every pixel", text_color=TEXT,
                     font=ctk.CTkFont(UI_FONT, 13)).pack(side="left")
        self.lbl_bright = ctk.CTkLabel(row, text="0", text_color=ACCENT,
                                       font=ctk.CTkFont(MONO_FONT, 13, "bold"))
        self.lbl_bright.pack(side="right")
        self.sl_bright = ctk.CTkSlider(side, from_=-100, to=100, number_of_steps=200,
                                       variable=self.v_bright, command=self._on_bright,
                                       progress_color=ACCENT, button_color=ACCENT,
                                       button_hover_color=ACCENT_HOVER, fg_color=LINE)
        self.sl_bright.pack(fill="x", padx=22, pady=(8, 0))

        # --- convert
        self._section(side, "Color")
        self._switch(side, "Grayscale", self.v_gray)
        self._switch(side, "Black and white", self.v_bw, command=self._on_bw)
        row = ctk.CTkFrame(side, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(10, 0))
        ctk.CTkLabel(row, text="Threshold", text_color=TEXT,
                     font=ctk.CTkFont(UI_FONT, 13)).pack(side="left")
        self.lbl_thresh = ctk.CTkLabel(row, text="128", text_color=MUTED,
                                       font=ctk.CTkFont(MONO_FONT, 13, "bold"))
        self.lbl_thresh.pack(side="right")
        self.sl_thresh = ctk.CTkSlider(side, from_=0, to=255, number_of_steps=255,
                                       variable=self.v_thresh, command=self._on_thresh,
                                       progress_color=ACCENT, button_color=ACCENT,
                                       button_hover_color=ACCENT_HOVER, fg_color=LINE,
                                       state="disabled")
        self.sl_thresh.pack(fill="x", padx=22, pady=(8, 0))

        # --- transform
        self._section(side, "Transform")
        self._switch(side, "Flip horizontally", self.v_flip)

        # --- formulas
        self._section(side, "What is running")
        self.lbl_formula = ctk.CTkLabel(side, text="", text_color=TEXT, anchor="nw", justify="left",
                                        wraplength=285, font=ctk.CTkFont(MONO_FONT, 11))
        self.lbl_formula.pack(fill="x", padx=22)

        # --- bottom buttons
        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=22, pady=(0, 22))
        self.lbl_status = ctk.CTkLabel(bottom, text="Open an image to start.", text_color=MUTED,
                                       anchor="w", justify="left", wraplength=285,
                                       font=ctk.CTkFont(UI_FONT, 12))
        self.lbl_status.pack(fill="x", pady=(0, 10))
        btns = ctk.CTkFrame(bottom, fg_color="transparent")
        btns.pack(fill="x")
        btns.grid_columnconfigure((0, 1), weight=1, uniform="b")
        ctk.CTkButton(btns, text="Reset", height=40, corner_radius=8, fg_color=SECONDARY,
                      hover_color=SECONDARY_HOVER, text_color=TEXT, font=ctk.CTkFont(UI_FONT, 13),
                      command=self.reset).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_save = ctk.CTkButton(btns, text="Save result", height=40, corner_radius=8,
                                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                      font=ctk.CTkFont(UI_FONT, 13, "bold"), command=self.save_image,
                                      state="disabled")
        self.btn_save.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _switch(self, parent, text, var, command=None):
        sw = ctk.CTkSwitch(parent, text=text, variable=var,
                           command=lambda: (command and command(), self.schedule()),
                           progress_color=ACCENT, button_color=TEXT, button_hover_color="#FFFFFF",
                           fg_color=LINE, text_color=TEXT, font=ctk.CTkFont(UI_FONT, 13))
        sw.pack(anchor="w", padx=22, pady=(6, 0))
        return sw

    # --------------------------------------------------------------- main
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=22, pady=22)
        main.grid_columnconfigure((0, 1), weight=1, uniform="panel")
        main.grid_rowconfigure(0, weight=1)

        self.panel_orig = self._image_panel(main, "Original", 0)
        self.panel_proc = self._image_panel(main, "Processed", 1)

        # matrix inspector
        insp = ctk.CTkFrame(main, fg_color=SURFACE, corner_radius=12)
        insp.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        head = ctk.CTkFrame(insp, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(head, text="Pixel values at the center of the image", text_color=TEXT,
                     font=ctk.CTkFont(UI_FONT, 14, "bold")).pack(side="left")
        self.seg = ctk.CTkSegmentedButton(head, values=["R", "G", "B"], command=lambda v: self.refresh_matrices(),
                                          selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                                          unselected_color=SECONDARY, unselected_hover_color=SECONDARY_HOVER,
                                          fg_color=SECONDARY, font=ctk.CTkFont(UI_FONT, 12), width=150)
        self.seg.set("R")
        self.seg.pack(side="right")
        ctk.CTkLabel(head, text="Channel", text_color=MUTED,
                     font=ctk.CTkFont(UI_FONT, 12)).pack(side="right", padx=(0, 10))

        body = ctk.CTkFrame(insp, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 16))
        self.grid_orig, self.cap_orig = self._matrix_block(body, "Original")
        self.grid_proc, self.cap_proc = self._matrix_block(body, "Processed")
        info = ctk.CTkFrame(body, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(info, text="Array info", text_color=MUTED, anchor="w",
                     font=ctk.CTkFont(UI_FONT, 12)).pack(fill="x", pady=(0, 6))
        self.lbl_info = ctk.CTkLabel(info, text="No image loaded", text_color=TEXT, anchor="nw", justify="left",
                                     font=ctk.CTkFont(MONO_FONT, 12))
        self.lbl_info.pack(fill="x")

    def _matrix_block(self, parent, title):
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.pack(side="left", padx=(0, 26))
        cap = ctk.CTkLabel(block, text=title, text_color=MUTED, anchor="w", font=ctk.CTkFont(UI_FONT, 12))
        cap.pack(fill="x", pady=(0, 6))
        grid = MatrixGrid(block)
        grid.pack()
        return grid, cap

    def _image_panel(self, parent, title, col):
        box = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=12)
        box.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col == 0 else (8, 0))
        box.grid_propagate(False)
        ctk.CTkLabel(box, text=title, text_color=TEXT, font=ctk.CTkFont(UI_FONT, 14, "bold")
                     ).place(x=18, y=12)
        size_lbl = ctk.CTkLabel(box, text="", text_color=MUTED, font=ctk.CTkFont(MONO_FONT, 12))
        size_lbl.place(relx=1.0, x=-18, y=13, anchor="ne")
        img_lbl = ctk.CTkLabel(box, text="Open an image to start" if col == 0 else "The result appears here",
                               text_color=MUTED, font=ctk.CTkFont(UI_FONT, 13))
        img_lbl.place(relx=0.5, rely=0.52, anchor="center")
        box.bind("<Configure>", self._on_resize)
        return {"box": box, "img": img_lbl, "size": size_lbl}

    # ------------------------------------------------------------- events
    def _on_bright(self, v):
        v = int(round(float(v)))
        self.lbl_bright.configure(text=f"{v:+d}" if v else "0")
        self.schedule()

    def _on_thresh(self, v):
        self.lbl_thresh.configure(text=str(int(round(float(v)))))
        self.schedule()

    def _on_bw(self):
        self.sl_thresh.configure(state="normal" if self.v_bw.get() else "disabled")
        self.lbl_thresh.configure(text_color=ACCENT if self.v_bw.get() else MUTED)

    def _on_resize(self, _e):
        if self._rjob:
            self.after_cancel(self._rjob)
        self._rjob = self.after(80, self.refresh_images)

    def schedule(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(20, self.process)

    def params(self):
        return dict(brightness=int(round(self.v_bright.get())), gray=self.v_gray.get(), bw=self.v_bw.get(),
                    thresh=int(round(self.v_thresh.get())), flip=self.v_flip.get())

    # ------------------------------------------------------------ actions
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.src = load_image_matrix(path)
        except Exception as exc:
            messagebox.showerror("Cannot open image", f"This file could not be read as an image.\n\n{exc}")
            return
        self.path = path
        h, w = self.src.shape[:2]
        s = PREVIEW_MAX / max(h, w)
        if s < 1:
            small = Image.fromarray(self.src).resize((max(1, int(w * s)), max(1, int(h * s))),
                                                     Image.Resampling.LANCZOS)
            self.work = np.asarray(small, dtype=np.uint8).copy()
        else:
            self.work = self.src
        self.btn_save.configure(state="normal")
        self.lbl_status.configure(text=f"{os.path.basename(path)} loaded ({w} x {h} pixels).")
        self.process()

    def reset(self):
        self.v_bright.set(0)
        self.v_gray.set(False)
        self.v_bw.set(False)
        self.v_thresh.set(128)
        self.v_flip.set(False)
        self.lbl_bright.configure(text="0")
        self.lbl_thresh.configure(text="128", text_color=MUTED)
        self.sl_thresh.configure(state="disabled")
        self.process()

    def save_image(self):
        if self.src is None:
            return
        base = os.path.splitext(os.path.basename(self.path))[0]
        path = filedialog.asksaveasfilename(
            title="Save processed image", defaultextension=".png", initialfile=f"{base}_processed.png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("BMP", "*.bmp")])
        if not path:
            return
        try:
            full = run_pipeline(self.src, **self.params())  # full resolution, not the preview
            Image.fromarray(full).save(path)
        except Exception as exc:
            messagebox.showerror("Cannot save image", f"The image could not be saved.\n\n{exc}")
            return
        self.lbl_status.configure(text=f"Saved {os.path.basename(path)}.")

    # ---------------------------------------------------------- rendering
    def process(self):
        self._job = None
        self.update_formulas()
        if self.work is None:
            return
        self.out = run_pipeline(self.work, **self.params())
        self.refresh_images()
        self.refresh_matrices()

    def update_formulas(self):
        p = self.params()
        lines = []
        if p["brightness"]:
            sign = "+" if p["brightness"] > 0 else "-"
            lines.append(f"out = clip(pixel {sign} {abs(p['brightness'])}, 0, 255)")
        if p["gray"] or p["bw"]:
            lines.append("gray = 0.299*R + 0.587*G + 0.114*B")
        if p["bw"]:
            lines.append(f"out = 255 if gray >= {p['thresh']} else 0")
        if p["flip"]:
            lines.append("out[:, j] = in[:, W-1-j]")
        self.lbl_formula.configure(text="\n\n".join(lines) if lines else "No operation selected.")

    def _show(self, panel, arr):
        box = panel["box"]
        aw, ah = box.winfo_width() - 36, box.winfo_height() - 64
        if aw < 40 or ah < 40:
            return
        pil = Image.fromarray(arr)
        s = min(aw / pil.width, ah / pil.height)
        size = (max(1, int(pil.width * s)), max(1, int(pil.height * s)))
        pil = pil.resize(size, Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
        self._refs.append(img)
        self._refs = self._refs[-4:]
        panel["img"].configure(image=img, text="")
        panel["img"].place(relx=0.5, rely=0.5, y=18, anchor="center")
        h, w = arr.shape[:2]
        panel["size"].configure(text=f"{w} x {h}")

    def refresh_images(self):
        self._rjob = None
        if self.work is None or self.out is None:
            return
        self._show(self.panel_orig, self.work)
        self._show(self.panel_proc, self.out)

    @staticmethod
    def _center_patch(m, n=MATRIX_N):
        h, w = m.shape[:2]
        r0, c0 = max(0, h // 2 - n // 2), max(0, w // 2 - n // 2)
        return m[r0:r0 + n, c0:c0 + n]

    def refresh_matrices(self):
        if self.work is None or self.out is None:
            return
        ch = self.seg.get()
        idx = "RGB".index(ch)

        patch_o = self._center_patch(self.work)[..., idx]
        self.grid_orig.show(patch_o, CHANNEL_HUES[ch])
        self.cap_orig.configure(text=f"Original, {ch} channel")

        if self.out.ndim == 2:
            patch_p, hue, name = self._center_patch(self.out), CHANNEL_HUES["Gray"], "gray level"
        else:
            patch_p, hue, name = self._center_patch(self.out)[..., idx], CHANNEL_HUES[ch], f"{ch} channel"
        self.grid_proc.show(patch_p, hue)
        self.cap_proc.configure(text=f"Processed, {name}")

        h, w = self.src.shape[:2]
        self.lbl_info.configure(text=(
            f"Original\n"
            f"  shape  {self.src.shape}\n"
            f"  dtype  {self.src.dtype}\n"
            f"  mean   {self.work.mean():.1f}\n\n"
            f"Processed\n"
            f"  shape  {(h, w) if self.out.ndim == 2 else (h, w, 3)}\n"
            f"  dtype  {self.out.dtype}\n"
            f"  mean   {self.out.mean():.1f}"))


if __name__ == "__main__":
    App().mainloop()
