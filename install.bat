@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"

echo 📦  Instalando Tiny Job Search AI em %PROJECT_DIR%

REM --- Checa python ---
where python >nul 2>nul
if errorlevel 1 (
    echo ❌  Python nao encontrado. Instale em https://python.org/downloads/
    echo     Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

REM --- Cria venv ---
if not exist "%VENV_DIR%" (
    echo 🐍  Criando virtual environment...
    python -m venv "%VENV_DIR%"
)

REM --- Instala dependencias ---
echo 📥  Instalando dependencias Python...
"%VENV_DIR%\Scripts\pip.exe" install --upgrade pip --quiet
"%VENV_DIR%\Scripts\pip.exe" install -r "%PROJECT_DIR%requirements.txt" --quiet

REM --- Playwright chromium ---
echo 🌐  Instalando Playwright Chromium (uma vez, ~150MB)...
"%VENV_DIR%\Scripts\python.exe" -m playwright install chromium

REM --- Cria atalho na area de trabalho ---
echo 🖥️   Criando atalho...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Tiny Job Search AI.lnk');" ^
  "$lnk.TargetPath = '%VENV_DIR%\Scripts\pythonw.exe';" ^
  "$lnk.Arguments = '\"%PROJECT_DIR%src\main.py\"';" ^
  "$lnk.WorkingDirectory = '%PROJECT_DIR%';" ^
  "$lnk.IconLocation = '%PROJECT_DIR%assets\icon.ico';" ^
  "$lnk.Save()"

echo.
echo ✅  Instalacao completa!
echo     Atalho criado na area de trabalho.
echo     Ou execute: run.bat
pause
