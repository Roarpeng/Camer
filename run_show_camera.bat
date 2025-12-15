@echo off
cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    call camer311\Scripts\activate.bat
)

python show_camera.py

pause