@echo off

:: === PATH ===
cd /d %~dp0

:: === Cleanup function ===
setlocal EnableDelayedExpansion
set "FLASK_PID_FILE=%TEMP%\flask_server.pid"
set "VITE_PID_FILE=%TEMP%\vite_server.pid"

:cleanup
if exist !FLASK_PID_FILE! (
  for /f "usebackq" %%p in (!FLASK_PID_FILE!) do taskkill /F /PID %%p >nul 2>&1
  del /f /q !FLASK_PID_FILE! >nul 2>&1
)
if exist !VITE_PID_FILE! (
  for /f "usebackq" %%p in (!VITE_PID_FILE!) do taskkill /F /PID %%p >nul 2>&1
  del /f /q !VITE_PID_FILE! >nul 2>&1
)

:: === Kill port 5050 if used ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5050') do taskkill /F /PID %%a >nul 2>&1

:: === Kill port 5173 if used ===
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173') do taskkill /F /PID %%a >nul 2>&1

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
start /min cmd /c "python app.py" && echo !ERRORLEVEL! > !FLASK_PID_FILE!

:: === Start React frontend ===
echo ⚛️ Avvio frontend React...
cd ..\frontend
call npm install
start /min cmd /c "npm run dev" && echo !ERRORLEVEL! > !VITE_PID_FILE!

cd ..\..

:: === Run Python tool ===
echo ▶️  Esecuzione dello script principale Python...
python run.py

:: === Cleanup ===
call :cleanup

echo.
echo ✅ Operazione completata. Premere un tasto per uscire.
pause >nul