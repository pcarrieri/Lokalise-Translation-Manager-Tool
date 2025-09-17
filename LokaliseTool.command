#!/bin/bash
# Naviga nella cartella in cui si trova lo script
cd "$(dirname "$0")"

# Attiva l'ambiente virtuale
source venv/bin/activate

# Esegui lo script principale Python che gestisce tutto
echo "🚀 Avvio del Lokalise Translation Manager..."
python start_manager.py