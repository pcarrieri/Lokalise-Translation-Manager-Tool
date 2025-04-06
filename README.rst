Lokalise Translation Manager Tool
=================================

.. image:: https://img.shields.io/badge/Python-3.8%2B-blue
   :target: https://www.python.org/downloads/
.. image:: https://img.shields.io/github/license/your-org/Lokalise-Translation-Manager-Tool.svg
   :target: ./LICENSE
.. image:: https://img.shields.io/github/stars/your-org/Lokalise-Translation-Manager-Tool.svg?style=social
   :target: https://github.com/your-org/Lokalise-Translation-Manager-Tool/stargazers
.. image:: https://img.shields.io/github/issues/your-org/Lokalise-Translation-Manager-Tool.svg
   :target: https://github.com/your-org/Lokalise-Translation-Manager-Tool/issues

A complete end-to-end localization pipeline for iOS and Android projects powered by Lokalise and OpenAI.

Overview
--------

**Lokalise Translation Manager Tool** is a powerful CLI application that automates the entire translation lifecycle:

- Scans your iOS and Android projects for localization keys
- Detects missing translations
- Translates automatically using OpenAI
- Uploads translations back to Lokalise
- Optionally detects and deletes unused Lokalise keys
- Generates detailed CSV reports
- Supports custom plugins at various stages of execution

Features
--------

- ✅ Fully modular architecture
- ✅ Works with both iOS (.swift) and Android (.kt / .java) projects
- ✅ Plugin system for pre/post-processing
- ✅ Local config file for safe API key storage
- ✅ Full report generation (`/reports`)
- ✅ Interactive prompts with safe-guards for critical actions
- ✅ Handles Lokalise API rate limits automatically
- ✅ Smart diffing of translation usage
- ✅ Estimates translation cost before using OpenAI

Project Structure
-----------------

::

  Lokalise-Translation-Manager-Tool/
  ├── lokalise_translation_manager/
  │   ├── scanner/
  │   ├── translator/
  │   ├── utils/
  │   ├── plugins/
  │   ├── config/
  │   └── core.py
  ├── reports/
  ├── run.py
  ├── requirements.txt
  └── README.rst

Requirements
------------

- Python 3.8+
- Internet connection (for Lokalise + OpenAI)
- A Lokalise API Key (Read/Write)
- An OpenAI API Key

Initial Setup
-------------

.. code-block:: bash

   git clone https://github.com/your-org/Lokalise-Translation-Manager-Tool.git
   cd Lokalise-Translation-Manager-Tool
   python3 run.py

The tool will prompt you to configure:

- iOS and Android project paths
- Lokalise Project ID and API Key
- OpenAI API Key

This configuration is saved in ``config/user_config.json``.

How It Works (Step-by-Step)
---------------------------

1. Download Lokalise translations (.strings, .xml)
2. Scan your project files for used keys
3. Compare used keys against Lokalise
4. Detect missing translations
5. Translate missing keys via OpenAI
6. Run post-processing plugins
7. Upload new translations to Lokalise
8. (Optional) List and delete unused Lokalise keys

Plugin System
-------------

The tool supports **custom plugins** placed in ``lokalise_translation_manager/plugins/``:

- **ACTION** – Run before translation starts
- **PROMPT** – Inject custom prompt logic for OpenAI
- **EXTENSION** – Run after translation ends

Example plugin: ``myPayments.py`` filters `softpos` and `http(s)://` keys.

Reports Generated
-----------------

All reports are saved in the ``/reports`` directory:

+-------------------------------+---------------------------------------------+
| File                          | Description                                 |
+===============================+=============================================+
| missing_ios_translations.csv  | iOS keys with missing translations          |
| missing_android_translations.csv | Android keys with missing translations  |
| translation_done.csv          | Keys successfully translated                |
| softpos_translations.csv      | Plugin-detected softpos keys                |
| url_translations.csv          | Plugin-detected URL keys                    |
| ready_to_translations.csv     | Final input for OpenAI                      |
| final_report.csv              | Uploaded translations summary               |
| ready_to_be_deleted.csv       | Lokalise keys not used in any project       |
+-------------------------------+---------------------------------------------+

Exclude Specific Languages
--------------------------

To ignore certain languages, create this config file:

.. code-block:: ini

   [EXCLUDED]
   excluded_locales = pl, sv, da

Deleting Unused Keys (Manual Confirmation)
------------------------------------------

Keys are **never deleted automatically**.

- A full preview table will be shown
- ``ready_to_be_deleted.csv`` will be generated
- You must confirm manually with Y/N prompt
- Clear warnings and disclaimers will be shown

Translation Engine
------------------

Uses OpenAI GPT-4 or 3.5 via API. Prompts can be customized via ``PROMPT`` plugins.

- Skips completed keys
- Tracks estimated cost per key
- Retry logic for OpenAI planned

Example Output Summary
----------------------

.. code-block:: text

   Model: gpt-4o
   Input File: reports/ready_to_translations.csv
   Output File: reports/translation_done.csv
   Total Keys: 56
   Total Translations: 392
   Estimated Tokens: ~2,400
   Estimated Cost: $0.12 USD
   Action Plugins Used: myPayments
   Prompt Plugins Used: customPromptHandler.py

Future Enhancements
-------------------

- UI configuration tool
- Jetpack Compose / Storyboard support
- Key exclusions per module
- Web-based final report viewer

Troubleshooting
---------------

- ``ModuleNotFoundError`` → Run ``pip install -r requirements.txt``
- ``Permission denied`` → Try ``sudo python3 run.py``
- ``File not found`` → Check paths in ``user_config.json``

License
-------

MIT License

Copyright (c) 2025 Piero Carrieri

See LICENSE file for full details.
