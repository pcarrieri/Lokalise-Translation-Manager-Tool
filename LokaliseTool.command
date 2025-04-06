#!/bin/bash

cd "$(dirname "$0")"

echo "🔍 Checking for Python 3.8+ ..."

PYTHON_COMMAND=""

# Check python3 version
if command -v python3 &>/dev/null; then
  PY_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  if [[ "$PY_VERSION" =~ ^3\.[8-9]|[1-9][0-9] ]]; then
    PYTHON_COMMAND="python3"
  else
    echo "❌ Found python3 version $PY_VERSION (must be >= 3.8)"
  fi
fi

# Fallback to python (only if version is 3.8+)
if [[ -z "$PYTHON_COMMAND" ]] && command -v python &>/dev/null; then
  PY_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
  if [[ "$PY_VERSION" =~ ^3\.[8-9]|[1-9][0-9] ]]; then
    PYTHON_COMMAND="python"
  else
    echo "❌ Found python version $PY_VERSION (must be >= 3.8)"
  fi
fi

# Abort if no compatible Python found
if [[ -z "$PYTHON_COMMAND" ]]; then
  echo "❌ ERROR: No suitable Python 3.8+ interpreter found."
  echo "💡 Please install Python 3.8+ from https://www.python.org/downloads/"
  read -p "Press ENTER to exit..."
  exit 1
fi

echo "✅ Using $PYTHON_COMMAND ($PY_VERSION)"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
  echo "⚙️  Creating virtual environment..."
  $PYTHON_COMMAND -m venv venv || {
    echo "❌ Failed to create virtual environment."
    exit 1
  }
fi

# Activate the venv
source venv/bin/activate
echo "✅ Virtual environment activated."

# Run the tool
echo "🚀 Launching Lokalise Translation Manager Tool..."
$PYTHON_COMMAND run.py

echo ""
read -p "🔚 Press ENTER to close this window..."
