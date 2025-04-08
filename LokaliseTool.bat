@echo off

:: === PATH ===
cd /d %~dp0

:: === Python version check ===
echo Checking Python version...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Python non trovato. Installa Python >= 3.8 da https://www.python.org/downloads/
  pause
  exit /b
)

:: === Create venv if not exists ===
IF NOT EXIST venv (
  echo ⚙️  Creating virtual environment...
  python -m venv venv
)

:: === Activate venv ===
call venv\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Errore durante l'attivazione della virtualenv
  pause
  exit /b
)

echo ✅ Virtual environment activated.

:: === Start Flask backend ===
echo 🚀 Avvio backend Flask...
cd webapp\backend
pip install -r requirements.txt
start /min cmd /c "python app.py"

:: === Start React frontend ===
echo ⚛️ Avvio frontend React...
cd ..\frontend
call npm install
start /min cmd /c "npm run dev"

:: === Back to root dir ===
cd ..\..

:: === Run Python tool ===
echo ▶️  Esecuzione dello script principale Python...
python run.py

:: === Done ===
echo.
echo ✅ Operazione completata. Premere un tasto per uscire.
pause >nul
