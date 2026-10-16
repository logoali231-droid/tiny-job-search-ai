@echo off
set "PROJECT_DIR=%~dp0"
if not exist "%PROJECT_DIR%.venv\Scripts\pythonw.exe" (
    echo ❌  Ambiente faltando. Rode install.bat primeiro.
    pause
    exit /b 1
)
"%PROJECT_DIR%.venv\Scripts\pythonw.exe" "%PROJECT_DIR%src\main.py" %*
