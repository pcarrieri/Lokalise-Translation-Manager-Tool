![Logo](assets/logo.jpeg)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/pcarrieri/Lokalise-Translation-Manager-Tool.svg)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/pcarrieri/Lokalise-Translation-Manager-Tool.svg?style=social)](https://github.com/pcarrieri/Lokalise-Translation-Manager-Tool/stargazers)
[![Issues](https://img.shields.io/github/issues/pcarrieri/Lokalise-Translation-Manager-Tool.svg)](https://github.com/pcarrieri/Lokalise-Translation-Manager-Tool/issues)
[![Release](https://img.shields.io/badge/Release-v1.3.0-green)](https://github.com/pcarrieri/Lokalise-Translation-Manager-Tool/releases)

> A complete end-to-end localization pipeline for iOS and Android projects powered by Lokalise and OpenAI.

---

## 🚀 Overview

**Lokalise Translation Manager Tool** is a powerful CLI + Web UI application that automates the entire translation lifecycle:

- 🔍 Scans your iOS and Android projects for localization keys
- 📈 Detects missing translations
- 🤖 Translates automatically using OpenAI
- 🖆️ Uploads translations back to Lokalise
- 🛁 Optionally detects and deletes unused Lokalise keys
- 📦 Generates detailed CSV reports
- 🌐 Provides a full web UI to browse and edit reports
- 🔌 Supports custom plugins at various stages of execution

> 🧠 Designed for engineers, localization teams, and product owners looking to automate localization with precision and control.

---

## 🆕 What's New in v1.3.0

### Plugin System Overhaul
- **Three plugin types**: ACTION (pre-translation), PROMPT (modify prompts), EXTENSION (post-processing)
- **Configuration file**: Enable/disable plugins via `config/plugins_config.json` without deleting files
- **Auto-discovery**: New plugins are automatically detected and registered

### Dynamic Language Configuration
- **Centralized config**: Add/remove languages via `config/supported_languages.json`
- **New languages**: Turkish, Arabic, Greek, Farsi, Lithuanian, Latvian, Estonian
- **No code changes needed**: Just edit the JSON file to support new locales

### Improved CSV Handling
- **Auto-delimiter detection**: Automatically handles comma, semicolon, or tab-separated files
- **Regional compatibility**: Works with CSV files from different regions (EU uses `;`, US uses `,`)

### Enhanced Web UI
- **Dark mode**: Toggle between light and dark themes
- **Undo/Redo**: Full edit history with keyboard shortcuts (Ctrl+Z/Y)
- **Visual indicators**: See modified rows at a glance
- **Performance**: Optimized rendering for large datasets

### Testing Framework
- **Mock APIs**: Lokalise and OpenAI mocks for offline testing
- **Test runner**: `python3 run_tests.py` with unit and integration tests
- **Coverage reports**: Generate HTML coverage reports

### Bug Fixes
- Fixed Turkish language code mapping (tr_TR)
- Fixed CSV separator compatibility issues
- Improved Android scanner to check all file types (.kt, .java, .xml)
- Better error handling for API rate limits

---

## 📦 Features

- ✅ Fully modular architecture
- ✅ Works with both iOS (`.swift`) and Android (`.kt` / `.java` / `.xml`) projects
- ✅ Advanced plugin system (ACTION, PROMPT, EXTENSION types)
- ✅ Dynamic language configuration via JSON
- ✅ Auto-detection of CSV delimiters (`,` `;` `\t`)
- ✅ Local config file for safe API key storage
- ✅ Full report generation (`/reports`)
- ✅ Interactive prompts with safe-guards for critical actions
- ✅ Handles Lokalise API rate limits automatically
- ✅ Smart diffing of translation usage
- ✅ Web UI with dark mode, undo/redo, inline editing
- ✅ Safe start/stop handling of React & Flask services
- ✅ Comprehensive test suite with mocked APIs

---

## 🧱 Project Structure

```
Lokalise-Translation-Manager-Tool/
├── lokalise_translation_manager/   # Core tool logic
│   ├── core.py                     # Main orchestrator
│   ├── download/                   # Lokalise file downloads
│   ├── scanner/                    # iOS & Android scanners
│   ├── translator/                 # OpenAI translation engine
│   ├── plugins/                    # Custom plugins (user-defined)
│   └── utils/                      # Utilities (CSV, language config, etc.)
├── config/                         # Configuration files
│   ├── user_config.json            # API keys & project paths
│   ├── plugins_config.json         # Plugin enable/disable settings
│   ├── supported_languages.json    # Language definitions
│   └── excluded_locales.ini        # Languages to skip
├── reports/                        # Generated .csv reports
├── tests/                          # Test suite with mocks
├── webapp/                         # Frontend (React) + Backend (Flask)
│   ├── frontend/                   # React + AG Grid UI
│   └── backend/                    # Flask API
├── run.py                          # CLI entry point
├── run_tests.py                    # Test runner
├── LokaliseTool.command            # macOS/Linux starter
└── LokaliseTool.bat                # Windows starter
```

---

## 🔧 Requirements

- **Python 3.8+**
- **Node.js >= 18.18.0**
- **npm >= 9**
- A Lokalise API Key (Read/Write)
- An OpenAI API Key

---

## ⚡ Quick Start (with UI)

### 🖥 macOS / Linux

```bash
./LokaliseTool.command
```

### 🪟 Windows

```bash
LokaliseTool.bat
```

This will:
- Setup Python virtual environment
- Install dependencies
- Start Flask backend on port `5050`
- Start React frontend on port `5173`
- Launch the CLI (`run.py`)
- Open the browser on http://localhost:5173

### 🐍 CLI only (no UI)

```bash
python3 run.py
```

---

## 🖥 Web UI Features

The project includes a full React UI to explore and modify the generated `.csv` reports visually.

- 📁 File picker with special file tabs (Final Report, Keys to Delete, etc.)
- 📊 Interactive data grid (AG Grid) with virtual scrolling
- ✏️ Inline editing, column sorting, filtering
- 💾 Save edits back to CSV
- 🌓 **Dark mode** toggle with persistent theme
- ↩️ **Undo/Redo** with keyboard shortcuts (Ctrl+Z / Ctrl+Y)
- 🔍 Quick search across all columns
- 📤 Export functionality

Backend routes (Flask):
- `GET /files` → list all available reports
- `GET /files/<filename>` → load specific CSV
- `POST /files/<filename>` → save changes to disk

> PID management, port cleanup, and auto-kill of previous processes are handled automatically on both platforms.

---

## 🛠️ Initial Setup

```bash
git clone https://github.com/pcarrieri/Lokalise-Translation-Manager-Tool.git
cd Lokalise-Translation-Manager-Tool
./LokaliseTool.command  # or LokaliseTool.bat
```

On the first run, you'll be prompted to provide:
- iOS and Android project paths
- Lokalise Project ID and API Key
- OpenAI API Key

This information is saved in:  
📁 `config/user_config.json`

---

## 🧠 How It Works (Step-by-Step)

1. 📥 **Download Lokalise translations**
2. 📂 **Scan your project**
3. 🔍 **Compare** with Lokalise
4. 📈 **Detect missing** keys
5. 🌠 **Auto-translate** via OpenAI
6. 🧪 **Apply plugins** (optional)
7. ⬆️ **Upload to Lokalise**
8. 🪑 **Preview deletable keys**
9. 🌐 **Visualize & edit reports in browser**

---

## 📊 Reports Generated

All reports are saved in `/reports/` and available from the Web UI.

| File                               | Description                            |
| ---------------------------------- | -------------------------------------- |
| `missing_ios_translations.csv`     | iOS keys with missing translations     |
| `missing_android_translations.csv` | Android keys with missing translations |
| `translation_done.csv`             | Keys successfully translated           |
| `softpos_translations.csv`         | Plugin-detected `softpos` keys         |
| `url_translations.csv`             | Plugin-detected URL keys               |
| `ready_to_translations.csv`        | Final input for translation            |
| `final_report.csv`                 | Uploaded translations summary          |
| `ready_to_be_deleted.csv`          | Unused Lokalise keys                   |

---

## 🚫 Exclude Specific Languages

Create or edit:

```
config/excluded_locales.ini
```

```ini
[EXCLUDED]
excluded_locales = pl, sv, da
```

These languages will be ignored during validation and translation.

---

## 🌍 Language Configuration

Languages are now configured via `config/supported_languages.json`:

```json
{
  "languages": {
    "en": { "name": "English", "lokalise_code": "en" },
    "de": { "name": "German", "lokalise_code": "de" },
    "tr": { "name": "Turkish", "lokalise_code": "tr_TR" },
    "ar": { "name": "Arabic", "lokalise_code": "ar" }
  }
}
```

**To add a new language:**
1. Add an entry to `supported_languages.json`
2. The tool will automatically include it in translation workflows

**Currently supported:** English, German, French, Italian, Polish, Swedish, Norwegian, Danish, Finnish, Lithuanian, Latvian, Estonian, Turkish, Arabic, Greek, Farsi

---

## 🔌 Plugin System

Plugins allow you to customize the translation workflow without modifying core code.

### Plugin Types

| Type | Marker | When it runs | Purpose |
|------|--------|--------------|---------|
| **ACTION** | `[ACTION]` | Before translation | Can bypass OpenAI (e.g., inject pre-reviewed translations) |
| **PROMPT** | `[PROMPT]` | During translation | Modify prompts (e.g., preserve brand names) |
| **EXTENSION** | `[EXTENSION]` | After translation | Post-process results (e.g., filter by feature) |

### Plugin Configuration

Enable/disable plugins in `config/plugins_config.json`:

```json
{
  "plugins": {
    "my_plugin.py": {
      "enabled": true,
      "type": "ACTION"
    }
  },
  "settings": {
    "auto_discover_new_plugins": true
  }
}
```

### Creating a Plugin

1. Create a `.py` file in `lokalise_translation_manager/plugins/`
2. Add the marker comment: `# [ACTION]`, `# [PROMPT]`, or `# [EXTENSION]`
3. Implement the required function:
   - ACTION: `run()` → returns `True` to bypass translation
   - PROMPT: `get_prompt_addon()` → returns additional prompt text
   - EXTENSION: `main()` or `filter_translations()`

4. The plugin will be auto-discovered on next run

---

## 🧪 Running Tests

```bash
# Run all tests
python3 run_tests.py

# Run only unit tests
python3 run_tests.py --unit

# Run only integration tests
python3 run_tests.py --integration

# Run with coverage report
python3 run_tests.py --coverage

# Run specific test
pytest tests/unit/test_csv_utils.py -v
```

The test suite includes mocked Lokalise and OpenAI APIs for offline testing.

---

## 💡 Tip: Port Conflicts

The tool automatically kills any process using:
- `5050` → Flask API
- `5173` → React Dev Server

PID tracking via temporary files (`/tmp/*.pid` or `%TEMP%\*.pid`) is used to prevent zombie processes.

---

## 📌 Safety First: Deleting Unused Keys

⚠️ **Keys identified as unused are not deleted automatically.**  

You'll receive:

- A full preview of the deletable keys
- A `ready_to_be_deleted.csv` file
- A **Y/N** confirmation prompt
- Clear warnings and disclaimers

Manual review is strongly encouraged before deleting anything.

---

## 💬 Translation Engine

Currently uses OpenAI GPT (4o or 3.5) to perform natural language translation.  
You can customize the prompts using the `PROMPT` plugin category.

Also includes:

- Prompt injection from plugins
- Skipping completed keys
- Estimated cost tracking (token usage)
- Retry logic on API errors (coming soon)

---

## 📊 Example Summary Output

```bash
Model: gpt-4o
Input File: reports/ready_to_translations.csv
Output File: reports/translation_done.csv
Total Keys: 56
Total Translations: 392
Estimated Tokens: ~2,400
Estimated Cost: $0.12 USD
Action Plugins Used: myPayments
Prompt Plugins Used: customPromptHandler.py
```

---

## 🧠 Future Enhancements

- Multi-file diffing (xib, storyboard, Jetpack Compose)
- Post-merge verification
- Custom fallback language support
- CLI argument overrides
- Multi-project mode (monorepo support)
- AI-assisted translation review in UI

---

## 🔏 Troubleshooting

- `ModuleNotFoundError`: Run `pip install -r requirements.txt`
- `Permission denied`: Try `sudo python3 run.py`
- `File not found`: Ensure project paths are correct in `user_config.json`
- `No config found`: Re-run `python3 run.py` to initialize setup

---

## 📜 License

Licensed under the [MIT License](./LICENSE).  
© 2025 [Piero Carrieri](https://github.com/pierocarrieri)

> ✨ Contributions are welcome. Please open a PR or issue!
