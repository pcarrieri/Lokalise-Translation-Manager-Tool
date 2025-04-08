#!/bin/bash

trap cleanup EXIT

cleanup() {
  if [ -f /tmp/vite.pid ]; then
    echo "\n🧹 Cleanup: chiusura server React..."
    kill "$(cat /tmp/vite.pid)" 2>/dev/null
    rm /tmp/vite.pid
  fi
  if [ -f /tmp/flask.pid ]; then
    echo "🧹 Cleanup: chiusura server Flask..."
    kill "$(cat /tmp/flask.pid)" 2>/dev/null
    rm /tmp/flask.pid
  fi
}

cd "$(dirname "$0")"

echo "🔍 Checking for Python 3.8+ ..."

PYTHON_COMMAND=""

if command -v python3 &>/dev/null; then
  PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  if [[ "$PY_VERSION" =~ ^3\.[8-9]|[1-9][0-9] ]]; then
    PYTHON_COMMAND="python3"
  else
    echo "❌ Found python3 version $PY_VERSION (must be >= 3.8)"
  fi
fi

if [[ -z "$PYTHON_COMMAND" ]] && command -v python &>/dev/null; then
  PY_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  if [[ "$PY_VERSION" =~ ^3\.[8-9]|[1-9][0-9] ]]; then
    PYTHON_COMMAND="python"
  else
    echo "❌ Found python version $PY_VERSION (must be >= 3.8)"
  fi
fi

if [[ -z "$PYTHON_COMMAND" ]]; then
  echo "❌ ERROR: No suitable Python 3.8+ interpreter found."
  echo "💡 Please install Python 3.8+ from https://www.python.org/downloads/"
  read -p "Press ENTER to exit..."
  exit 1
fi

echo "✅ Using $PYTHON_COMMAND ($PY_VERSION)"

if [ ! -d "venv" ]; then
  echo "⚙️  Creating virtual environment..."
  $PYTHON_COMMAND -m venv venv || {
    echo "❌ Failed to create virtual environment."
    exit 1
  }
fi

source venv/bin/activate

echo "✅ Virtual environment activated."

# Kill existing process on port 5050 if needed
if lsof -i :5050 &>/dev/null; then
  echo "🛑 Porta 5050 occupata, chiudo il processo esistente..."
  PID=$(lsof -ti :5050)
  kill -9 $PID
fi

# Start Flask backend
(
  echo "🚀 Starting Flask backend..."
  cd webapp/backend
  pip install -r requirements.txt
  python app.py & echo $! > /tmp/flask.pid
) &

# Start React frontend
(
  echo "⚛️ Starting React frontend..."
  cd webapp/frontend
  npm install
  npm run dev & echo $! > /tmp/vite.pid
) &

sleep 5

echo "🚀 Launching Lokalise Translation Manager Tool..."
$PYTHON_COMMAND run.py

echo ""
read -p "🔚 Press ENTER to close this window..."