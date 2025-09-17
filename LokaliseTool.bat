@echo off
REM Naviga nella cartella in cui si trova lo script
cd /d "%~dp0"

REM Attiva l'ambiente virtuale
call venv\Scripts\activate.bat

REM Esegui lo script principale Python che gestisce tutto
echo "🚀 Avvio del Lokalise Translation Manager..."
python start_manager.py