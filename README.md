<p align="center">
  <img src="assets/COGNIX.png" alt="COGNIX" width="220">
</p>

<h1 align="center">Image Processing Using Matrices</h1>

<p align="center">
  A desktop program that treats a real image as a matrix and processes it with plain NumPy math.<br>
  Made by <b>COGNIX team</b>.
</p>

<p align="center">
  <img src="docs/splash.png" alt="Animated splash screen" width="640">
</p>

## What it does

Pick any image from your computer, then apply operations on its matrix and compare **Original** vs **Processed** side by side. Everything updates live while you move the sliders.

| Operation | Matrix math |
|---|---|
| Grayscale | `gray = 0.299*R + 0.587*G + 0.114*B` (weighted sum of the 3 channels) |
| Brightness | `out = clip(pixel + value, 0, 255)` |
| Horizontal flip | `out[:, j] = in[:, W-1-j]` (reverse the columns) |
| Black and white | `out = 255 if gray >= threshold else 0` |

Extra features:

- **Pixel values inspector:** shows the real numbers of a 7 x 7 block at the center of the image, before and after, for the R, G or B channel.
- **What is running:** shows the formula of every active operation.
- **Array info:** `shape`, `dtype` and mean of the original and processed matrices.
- **Save result:** saves the processed image at full resolution (PNG, JPEG or BMP). The live preview uses a smaller copy so the sliders stay smooth.
- Animated splash screen, `Ctrl+O` to open, `Ctrl+S` to save.

<p align="center">
  <img src="docs/app-grayscale.png" alt="Grayscale" width="48%">
  <img src="docs/app-black-white.png" alt="Black and white with flip" width="48%">
</p>

## Quick start (no terminal)

1. Install Python 3.9 or newer from python.org. Tick **Add Python to PATH** in the installer.
2. **Windows:** double-click `RUN.bat`. **macOS:** double-click `run.command`.

The first run installs the packages it needs (about a minute), then the program opens. After that it opens right away.

## Run it from the terminal

```bash
git clone https://github.com/kamly760-ctrl/image-processing-matrices.git
cd image-processing-matrices
pip install -r requirements.txt
python main.py
```

Try it with the included `samples/sample.png`, or any photo you like.

## How it works

A color image is a matrix of shape `(H, W, 3)`: `H` rows, `W` columns and 3 numbers (R, G, B) from 0 to 255 for every pixel. A gray image is `(H, W)`.

All the operations live in [`matrix_ops.py`](matrix_ops.py), about 50 lines of NumPy. Two details worth knowing:

- **Brightness** converts to `int16` before adding. With `uint8`, `250 + 20` would wrap around to `14` instead of staying bright, so we add first and clip after.
- **Grayscale** uses unequal weights because the eye is most sensitive to green and least to blue.

Pillow is used only to read and write image files and to draw on the screen.

## Project structure

```
main.py             the interface: splash screen + main window (CustomTkinter)
RUN.bat             double-click to run (installs packages on the first run)
build_exe.bat       double-click to build COGNIX-ImageLab.exe
matrix_ops.py       the matrix operations (NumPy)
assets/COGNIX.png   team logo (used by the splash screen and the sidebar)
assets/COGNIX.ico   icon of the .exe
samples/sample.png  an image to try
tests/              unit tests for the matrix operations
docs/               screenshots used in this README
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Settings

At the top of `main.py`:

- `SHOW_SPLASH = False` turns the splash screen off.
- `SPLASH_SPEED = 1.5` makes it faster (1.0 is about 4 seconds).

## Download the program (Windows, no Python needed)

Go to the [Releases page](https://github.com/kamly760-ctrl/image-processing-matrices/releases) and download `COGNIX-ImageLab.exe`. Double-click it and it opens.

Windows may show a "Windows protected your PC" warning because the program is not signed. Click **More info**, then **Run anyway**.

## Build the .exe yourself (Windows)

Double-click `build_exe.bat`. It installs the build tools and creates `dist\COGNIX-ImageLab.exe` (2 to 5 minutes). The manual command is:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --noconsole --onefile --name COGNIX-ImageLab --icon assets/COGNIX.ico --collect-all customtkinter --hidden-import PIL._tkinter_finder --add-data "assets;assets" main.py
```

On macOS and Linux use `:` instead of `;` in `--add-data` (and leave out `--icon`). The first launch of the single-file build takes a few seconds before the splash screen appears.

## نبذة بالعربي

مشروع جامعي بعنوان **معالجة الصور باستخدام المصفوفات**. البرنامج بيقرا صورة حقيقية من الجهاز ويحوّلها لمصفوفة أرقام، وبعدين يطبق عليها: تحويل لدرجات الرمادي، تعديل السطوع، قلب أفقي، وتحويل لأبيض وأسود. بيعرض الصورة قبل وبعد ويحفظ الناتج. كل العمليات مكتوبة بـ NumPy في ملف `matrix_ops.py`.

## License

MIT, see [LICENSE](LICENSE).
