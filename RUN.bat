@echo off
TITLE RBXStalker V2 Launcher

if exist "installed.flag" (
    echo Dependencies already installed. Launching...
    goto launch
)

echo First time setup: Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing requirements. Check your Python installation.
    pause
    exit
)
echo Setup complete. > installed.flag
echo.

:launch
echo Starting Dashboard...
python gui.py
pause