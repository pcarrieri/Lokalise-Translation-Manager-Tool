<p align="center">
  <img src="assets/logo.png" alt="Lokalise Translation Manager Tool Logo" width="200"/>
</p>



[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/your-org/Lokalise-Translation-Manager-Tool.svg)](./LICENSE)
[![Stars](https://img.shields.io/github/stars/your-org/Lokalise-Translation-Manager-Tool.svg?style=social)](https://github.com/your-org/Lokalise-Translation-Manager-Tool/stargazers)
[![Issues](https://img.shields.io/github/issues/your-org/Lokalise-Translation-Manager-Tool.svg)](https://github.com/your-org/Lokalise-Translation-Manager-Tool/issues)

> A complete end-to-end localization pipeline for iOS and Android projects powered by Lokalise and OpenAI.

---

## 🚀 Overview

**Lokalise Translation Manager Tool** is a powerful CLI application that automates the entire translation lifecycle:

- 🔍 Scans your iOS and Android projects for localization keys
- 📈 Detects missing translations
- 🤖 Translates automatically using OpenAI
- 🖆️ Uploads translations back to Lokalise
- 🛁 Optionally detects and deletes unused Lokalise keys
- 📦 Generates detailed CSV reports
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
- ✅ Estimates translation cost before using OpenAI

---

## 🧱 Project Structure

```
Lokalise-Translation-Manager-Tool/
├── lokalise_translation_manager/
│   ├── scanner/                # iOS & Android key scanners
│   ├── translator/             # OpenAI-powered translator
│   ├── utils/                  # Core logic & support scripts
│   ├── plugins/                # Custom user plugins
│   ├── config/                 # Config files
│   └── core.py                 # Orchestrator of all steps
├── reports/                    # All generated .csv reports
├── run.py                      # Entry point
├── requirements.txt
└── README.md
```

---

## 🔧 Requirements

- **Python 3.8+**
- Internet connection (for Lokalise + OpenAI)
- A Lokalise API Key (Read/Write)
- An OpenAI API Key

---

## 🛠️ Initial Setup

```bash
git clone https://github.com/your-org/Lokalise-Translation-Manager-Tool.git
cd Lokalise-Translation-Manager-Tool
python3 run.py
```

On the first run, you'll be prompted to provide:

- iOS and Android project paths
- Lokalise Project ID and API Key
- OpenAI API Key

This information is saved in:  
📁 `config/user_config.json`

---

## 🧠 How It Works (Step-by-Step)

1. 📥 **Download Lokalise translations** (iOS `.strings`, Android `.xml`)
2. 📂 **Scan your project files** for used keys (`NSLocalizedString` / `R.string`)
3. 🔍 **Compare** used keys against Lokalise
4. 📈 **Detect missing translations**
5. 🌠 **Auto-translate missing keys** via OpenAI
6. 🧪 **Run post-processing plugins** (e.g. filter out URLs, keywords, etc.)
7. ⬆️ **Upload new translations** to Lokalise
8. 🪑 **(Optional)** List and delete unused keys from Lokalise

---

## ⚙️ Plugin System

The tool supports **custom Python plugins** for additional logic or filtering.

- 🔀 **ACTION** – Run before translation starts
- 🧠 **PROMPT** – Inject custom prompt logic for OpenAI
- 📩 **EXTENSION** – Run after translation ends

**Example plugin**:  
`myPayments.py` filters keys with `softpos` or `http(s)://` and removes them before uploading.

💪 Plugins live in:  
📁 `lokalise_translation_manager/plugins/`

---

## 📟 Reports Generated

All reports are saved in `/reports`:

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
