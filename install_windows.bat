
@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Tiny Job Search AI - Windows installer
echo ========================================
echo.

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found.
    echo Keep this file in the root of the tiny-job-search-ai repository.
    goto :failed
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_LAUNCHER=py"
    set "PYTHON_ARGS=-3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python was not found.
        echo Install Python 3.10 or newer from:
        echo https://www.python.org/downloads/windows/
        echo Enable the Python Launcher or add Python to PATH.
        goto :failed
    )
    set "PYTHON_LAUNCHER=python"
    set "PYTHON_ARGS="
)

echo Checking Python version...
%PYTHON_LAUNCHER% %PYTHON_ARGS% -c "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto :python_version_error

%PYTHON_LAUNCHER% %PYTHON_ARGS% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :tkinter_error

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating virtual environment...
    %PYTHON_LAUNCHER% %PYTHON_ARGS% -m venv ".venv"
    if errorlevel 1 goto :venv_error
)

echo.
echo Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :pip_error

".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto :requirements_error

echo.
choice /C SN /M "Install the Playwright Chromium browser now? (optional; may download hundreds of MB)"
if errorlevel 2 goto :skip_chromium
if errorlevel 1 goto :install_chromium
goto :finish

:install_chromium
echo.
echo Installing Playwright Chromium...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo WARNING: Chromium installation failed.
    echo The main app may still run, but browser-based scrapers may not work.
)
goto :finish

:skip_chromium
echo Skipping Chromium. You can install it later with:
echo .venv\Scripts\python.exe -m playwright install chromium
goto :finish

:finish
echo.
echo Installation finished.
echo Start Tiny Job Search AI by double-clicking run_windows.bat.
echo User data is stored under %%LOCALAPPDATA%%\TinyJobSearchAI.
echo.
pause
exit /b 0

:python_version_error
echo ERROR: Python 3.10 or newer is required.
echo Install a supported version from https://www.python.org/downloads/windows/
goto :failed

:tkinter_error
echo ERROR: Tkinter is missing from this Python installation.
echo Re-run the official Python installer and enable Tcl/Tk support.
goto :failed

:venv_error
echo ERROR: Could not create the virtual environment.
goto :failed

:pip_error
echo ERROR: Could not upgrade pip.
goto :failed

:requirements_error
echo ERROR: Could not install requirements.txt.
goto :failed

:failed
echo.
echo Installation failed. Read the error above, fix it, and run this file again.
pause
exit /b 1
