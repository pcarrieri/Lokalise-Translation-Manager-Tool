# Lokalise Translation Manager Tool

## Overview

**Lokalise Translation Manager Tool** is a CLI utility designed to streamline the localization process for iOS and Android projects using [Lokalise](https://lokalise.com/).  
It automates:

- Key usage detection across projects
- Identification of missing translations
- Automatic translation via OpenAI
- Upload of new translations to Lokalise
- Optional deletion of unused keys
- Generation of detailed CSV reports

It’s modular, extensible, and customizable via plugins.

---

## Requirements

- **Python 3**: [Download here](https://www.python.org/downloads/)
- **pip**: Python package manager (usually comes with Python 3)

---

## Initial Setup

When run for the first time, the tool prompts the user to provide:

- Path(s) to iOS and/or Android project(s)
- Lokalise API key (read/write)
- OpenAI API key

It automatically installs all dependencies and optional libraries (like `prettytable`, `colorama`) if missing.

---

## 🚀 Usage

1. **Clone the Repository**:

   ```bash
   git clone <repository-url>
   cd <repository-directory>


2. **Run the Tool**:
   
   ```bash
   python3 run.py
   
This will:

- Install dependencies
- Collect required input if not already configured
- Start the analysis and translation process

---

## 🧾 Reports Generated

The tool outputs several CSV reports, including:

- **Per Platform**:

- iOS and Android keys with missing translations
- Used keys per platform
- Used keys with missing translations

- **Global**:

- Lokalise keys with English base
- Missing translations per language
- Keys that were translated and uploaded 
- Deleted keys (optional)
  
- **Plugin-specific**:

- Keys with URLs
- Keys with terms like softpos

---

## 🔧 Excluding Languages

Languages can be excluded using "excluded_locales.ini":

[EXCLUDED_LOCALES]
excluded_locales = pl

---

## 🔌 Plugin System

The tool supports custom plugins:

- ACTION: executed before translations
- PROMPT: allows modification of AI prompts
- EXTENSION: executed after translations

**Example**: "myPayments" plugin avoids uploading keys with URLs or “softpos”, generating two dedicated reports instead.

---

## 📈 Future Improvements

Planned features:

- Enhanced logging per analyzed file
- Unified report file
- Support for additional translators
- GUI interface
- .xib and .storyboard scanning
- Optional platform-only usage (iOS or Android)
- Retry logic for OpenAI errors
- Web-based final report
- Key-specific exclusion configuration

---

## 🛠 Troubleshooting

- ❌ Python not found: Make sure it’s installed and on your PATH
- ❌ pip missing: Install it manually if needed
- 🔒 Permission denied: Try running with elevated privileges

---

## 📄 License

MIT License

Copyright (c) 2025 Piero Carrieri

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions:

⚠️ The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

💡 Credit must be clearly attributed to **Piero Carrieri** in any derivative work, publication, or presentation using this tool.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


📄 License: [MIT License](./LICENSE) — Copyright © 2025 Piero Carrieri
