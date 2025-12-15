@echo off
cd /d "%~dp0"

if exist "camer311\Scripts\activate.bat" (
    call camer311\Scripts\activate.bat
)

python simple_imshow.py

pause