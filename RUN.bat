@echo off
setlocal
cd /d "%~dp0"
title COGNIX - Image Processing Using Matrices

if exist main.py if exist matrix_ops.py goto havefiles
echo.
echo Some project files are missing next to this file.
echo Did you extract the zip first?
echo Right-click the zip, choose Extract All, open the new folder, and run this file from there.
echo.
echo Folder checked: %cd%
echo.
pause
exit /b 1

:havefiles
set PY=
python --version >nul 2>nul && set PY=python
if defined PY goto havepy
py --version >nul 2>nul && set PY=py
if defined PY goto havepy
goto nopython

:havepy
%PY% -c "import numpy, PIL, customtkinter" >nul 2>nul
if not errorlevel 1 goto launch

echo First run: installing the required packages. This takes about a minute...
echo.
%PY% -m pip install numpy "Pillow>=10.1" "customtkinter>=5.2"
if errorlevel 1 goto failed

:launch
%PY% main.py
if errorlevel 1 goto failed
exit /b 0

:nopython
echo Python is not installed on this computer.
echo.
echo 1. The download page will open now.
echo 2. In the installer, tick "Add Python to PATH" (bottom of the first screen), then click Install.
echo 3. When it finishes, double-click RUN.bat again.
echo.
start https://www.python.org/downloads/
pause
exit /b 1

:failed
echo.
echo Something went wrong. Take a screenshot of this window and send it to the team.
pause
exit /b 1
