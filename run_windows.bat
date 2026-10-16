
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Tiny Job Search AI has not been installed yet.
    echo First run install_windows.bat.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "src\main.py" %*
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo Tiny Job Search AI exited with an error. Read the message above.
    pause
)

exit /b %APP_EXIT%
