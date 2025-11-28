# Examples Directory

This directory contains example scripts demonstrating advanced usage of the Lokalise Translation Manager Tool.

## Available Examples

### csv_utils_usage.py

Demonstrates the new CSV utilities with automatic delimiter detection.

**Run it:**
```bash
python3 examples/csv_utils_usage.py
```

**What it shows:**
1. How to detect CSV delimiter automatically
2. How to read CSV files with auto-detection
3. How to manually process CSV with custom logic
4. How different delimiters (`,`, `;`, `\t`, `|`) are detected

**Requirements:**
- Run the main tool at least once to generate sample CSV files in `reports/`
- Or the script will create temporary test files for demonstration

## Creating Your Own Examples

You can create your own example scripts in this directory. Make sure to:

1. Add the parent directory to the Python path:
   ```python
   import sys
   from pathlib import Path
   BASE_DIR = Path(__file__).resolve().parent.parent
   sys.path.insert(0, str(BASE_DIR))
   ```

2. Import the utilities you need:
   ```python
   from lokalise_translation_manager.utils.csv_utils import detect_csv_delimiter
   from lokalise_translation_manager.translator.translate_with_openai import translate_text
   # etc.
   ```

3. Document your example with clear comments and docstrings

4. Make it executable:
   ```bash
   chmod +x examples/your_example.py
   ```
