![Logo](assets/logo.jpeg)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/your-org/Lokalise-Translation-Manager-Tool.svg)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/your-org/Lokalise-Translation-Manager-Tool.svg?style=social)](https://github.com/your-org/Lokalise-Translation-Manager-Tool/stargazers)
[![Issues](https://img.shields.io/github/issues/your-org/Lokalise-Translation-Manager-Tool.svg)](https://github.com/your-org/Lokalise-Translation-Manager-Tool/issues)

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

## 📦 Features

- ✅ Fully modular architecture
- ✅ Works with both iOS (`.swift`) and Android (`.kt` / `.java`) projects
- ✅ Plugin system for pre/post-processing
- ✅ Local config file for safe API key storage
- ✅ Full report generation (`/reports`)
- ✅ Interactive prompts with safe-guards for critical actions
- ✅ Handles Lokalise API rate limits automatically
- ✅ Smart diffing of translation usage
- ✅ Web UI for CSV browsing and editing
- ✅ Safe start/stop handling of React & Flask services

---

## 🧱 Project Structure

```
Lokalise-Translation-Manager-Tool/
├── lokalise_translation_manager/   # Tool logic
├── reports/                        # Generated .csv reports
├── webapp/                         # Frontend (React) + Backend (Flask)
│   ├── frontend/                   # React + Tailwind UI
│   └── backend/                    # Flask API
├── run.py                          # CLI entry point
├── LokaliseTool.command            # macOS/Linux starter
├── LokaliseTool.bat                # Windows starter
└── README.md
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

- 📁 File picker to choose a report
- 📊 Interactive data grid (AG Grid)
- ✏️ Inline editing, column sorting, filtering
- 💾 Save edits back to CSV
- 🌓 Responsive layout with Tailwind CSS

Backend routes (Flask):
- `GET /files` → list all available reports
- `GET /files/<filename>` → load specific CSV
- `POST /files/<filename>` → save changes to disk

> PID management, port cleanup, and auto-kill of previous processes are handled automatically on both platforms.

---

## 🛠️ Initial Setup

```bash
git clone https://github.com/your-org/Lokalise-Translation-Manager-Tool.git
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

- UI-based configuration tool
- Multi-file diffing (xib, storyboard, Jetpack Compose)
- Post-merge verification
- Custom fallback language support
- CLI argument overrides
- Multi-project mode (monorepo support)

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
