"""
OpenAI Translation Module for Lokalise Translation Manager

This module handles the automated translation of text strings using OpenAI's GPT models.
It is the core translation engine of the Lokalise Translation Manager Tool.

WORKFLOW:
---------
1. Load user configuration to get OpenAI API key
2. Read input CSV file (ready_to_translations.csv or mock version)
3. Discover and execute plugins in the correct order:
   - ACTION plugins: Run BEFORE translation (can bypass the translation step)
   - PROMPT plugins: Load DURING translation (modify translation prompts)
   - EXTENSION plugins: Run AFTER translation (post-process results)
4. Translate text for each language using OpenAI API
5. Save translated results to output CSV (translation_done.csv)
6. Track progress and allow resuming from last completed key

PLUGIN SYSTEM:
--------------
This module implements a sophisticated plugin system with three types:

1. **ACTION Plugins** ([ACTION] marker):
   - Execute BEFORE translation starts
   - Can bypass the entire translation step by returning True
   - Useful for custom pre-processing or conditional translation
   - Example: Check if translations already exist and skip API calls

2. **PROMPT Plugins** ([PROMPT] marker):
   - Loaded DURING translation
   - Their content is injected into the OpenAI prompt
   - Used to add context, constraints, or special instructions
   - Example: "Never translate brand names" or "Use formal tone"

3. **EXTENSION Plugins** ([EXTENSION] marker):
   - Execute AFTER translation completes
   - Process the translated results
   - Used for post-processing, validation, or integration
   - Example: Upload results to Lokalise, generate reports

RETRY MECHANISM:
----------------
Implements exponential backoff for API reliability:
- MAX_RETRIES: 5 attempts per translation
- Initial delay: 5 seconds
- Delay multiplier: 2x (5s, 10s, 20s, 40s, 80s)
- Handles: connection errors, rate limits, timeouts, API errors

RESUME CAPABILITY:
------------------
Translations are saved incrementally to allow resuming:
- Each successful translation is immediately written to output file
- On restart, already completed keys are skipped
- Prevents data loss and avoids redundant API calls

ERROR HANDLING:
---------------
- Missing required columns: Skip row and log warning
- Empty source text: Skip API call, write empty placeholder
- API failures: Retry with backoff, then skip if all attempts fail
- Plugin errors: Log error and continue with remaining plugins

CSV FORMAT:
-----------
Input (ready_to_translations.csv):
    key_name, key_id, languages, translation_id, translation

Output (translation_done.csv):
    key_name, key_id, languages, translation_id, translation, translated

The 'translated' column contains translations separated by '|' in the same
order as the languages in the 'languages' column.

DEPENDENCIES:
-------------
- openai: OpenAI Python SDK for API access
- colorama: Console color output (optional, graceful fallback)
- csv_utils: Custom CSV delimiter detection

CONFIGURATION:
--------------
Requires config/user_config.json with OpenAI API key:
{
    "openai": {
        "api_key": "sk-..."
    }
}

USAGE:
------
As a module:
    from lokalise_translation_manager.translator import translate_with_openai
    translate_with_openai.main()

As a script:
    python3 -m lokalise_translation_manager.translator.translate_with_openai

Via core workflow:
    The core.py module automatically calls this when translation is needed

EXAMPLE:
--------
Input CSV:
    key_name,key_id,languages,translation_id,translation
    welcome_msg,001,"it,de",t001,"Welcome to our app"

Output CSV:
    key_name,key_id,languages,translation_id,translation,translated
    welcome_msg,001,"it,de",t001,"Welcome to our app","Benvenuto nella nostra app|Willkommen in unserer App"

AUTHORS:
--------
Part of the Lokalise Translation Manager Tool
Enhanced with comprehensive documentation and generic plugin architecture
"""

import os
import csv
import json
import time
import sys
from pathlib import Path
from typing import Set, List, Tuple, Optional, Dict, Any
from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError, APIStatusError
import importlib.util
import sys

# Add parent directory to path for relative imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.csv_utils import detect_csv_delimiter

# Optional colorama support for colored console output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    colorama_available = True
except ImportError:
    colorama_available = False
    # Create dummy classes when colorama is not available
    class Fore:
        WHITE = ''
        GREEN = ''
        RED = ''
        YELLOW = ''
        CYAN = ''
        BLUE = ''

    class Style:
        RESET_ALL = ''

# ==================== DIRECTORY CONFIGURATION ====================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"

# Input file selection: Use mock file if it exists, otherwise use real file
MOCK_FILE = REPORTS_DIR / "ready_to_translations_mock.csv"
REAL_FILE = REPORTS_DIR / "ready_to_translations.csv"
INPUT_FILE = MOCK_FILE if MOCK_FILE.exists() else REAL_FILE

OUTPUT_FILE = REPORTS_DIR / "translation_done.csv"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"

# ==================== ADVANCED CONFIGURATION ====================

# Maximum number of retry attempts for API calls
MAX_RETRIES = 5

# Initial delay in seconds for exponential backoff (doubles each retry)
INITIAL_DELAY_SECONDS = 5

# OpenAI model to use (recommended model for performance/cost balance)
OPENAI_MODEL = "gpt-4o-mini"

# Mapping of language codes to full language names for better prompts
# This improves translation quality by providing clear language context
LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "pl": "Polish",
    "sv": "Swedish",
    "nb": "Norwegian (Bokmål)",
    "da": "Danish",
    "fi": "Finnish",
    "lt_LT": "Lithuanian",
    "lv_LV": "Latvian",
    "et_EE": "Estonian",
    "tr_TR": "Turkish",
    "ar": "Arabic",
    "el": "Greek"
}

# ==================== UTILITY FUNCTIONS ====================

def print_colored(text: str, color: Optional[str] = None) -> None:
    """
    Print text to console with optional color formatting.

    Uses colorama if available for colored output. If colorama is not installed,
    falls back to plain text output without colors. This ensures the tool works
    even without colorama dependency.

    Args:
        text: The text to print
        color: Optional colorama color constant (e.g., Fore.GREEN, Fore.RED)
               If None or colorama unavailable, prints plain text

    Example:
        print_colored("Success!", Fore.GREEN)
        print_colored("Error occurred", Fore.RED)
        print_colored("Normal text")  # No color
    """
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)


def get_api_key() -> str:
    """
    Load OpenAI API key from user configuration file.

    Reads the config/user_config.json file and extracts the OpenAI API key.
    The configuration file must contain a valid JSON structure with the
    OpenAI API key under openai.api_key path.

    Returns:
        str: The OpenAI API key

    Raises:
        FileNotFoundError: If the configuration file doesn't exist or API key is missing

    Example Configuration (config/user_config.json):
        {
            "openai": {
                "api_key": "sk-proj-..."
            }
        }
    """
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open(encoding='utf-8') as f:
            config = json.load(f)
            return config["openai"]["api_key"]
    raise FileNotFoundError("OpenAI API key not found in config")


def translate_text(
    client: OpenAI,
    text: str,
    lang_code: str,
    prompt_addons: str = ""
) -> str:
    """
    Translate text to target language using OpenAI API with retry mechanism.

    This function implements a robust translation system with:
    - Professional localization-focused system prompt
    - Placeholder preservation ({{var}}, %s, %d, etc.)
    - Exponential backoff retry for API failures
    - Consistent translation style (low temperature)

    The function automatically retries on transient errors (connection issues,
    rate limits, timeouts) with exponential backoff (5s, 10s, 20s, 40s, 80s).

    Args:
        client: Initialized OpenAI client instance
        text: Source text in English to translate
        lang_code: Target language code (e.g., 'it', 'de', 'fr')
        prompt_addons: Optional additional instructions from PROMPT plugins
                      These are injected into the system prompt to customize behavior

    Returns:
        str: Translated text, or empty string if all retry attempts fail

    Retry Behavior:
        - APIConnectionError: Network connectivity issues
        - RateLimitError: API rate limit exceeded
        - APITimeoutError: Request timeout (90s timeout per request)
        - APIStatusError: API returned error status code

        On failure, waits with exponential backoff:
        - Attempt 1 fails → wait 5s
        - Attempt 2 fails → wait 10s
        - Attempt 3 fails → wait 20s
        - Attempt 4 fails → wait 40s
        - Attempt 5 fails → return empty string

    Example:
        client = OpenAI(api_key="sk-...")
        result = translate_text(
            client,
            "Welcome to our app",
            "it",
            "Use formal tone."
        )
        # result: "Benvenuto nella nostra applicazione"
    """
    # Get full language name for better prompt clarity
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)

    # Construct professional localization system prompt
    system_prompt = f"""You are a professional software localization expert. Your task is to translate the given English text for an application's user interface.

**Instructions:**
1. Translate the following text into **{lang_name}** (language code: `{lang_code}`).
2. **Output ONLY the translated string.** Do not include explanations, introductions, quotes, or any other text.
3. **Preserve placeholders** (like `{{{{variable}}}}`, `%s`, `%d`) exactly as they appear in the original text. Do not translate them.
4. Maintain a neutral and clear tone suitable for software.
5. Ignore any URLs found in the text.
{prompt_addons}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    # Retry loop with exponential backoff
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.2,  # Low value for more consistent translations
                timeout=90
            )
            return response.choices[0].message.content.strip()

        except (APIConnectionError, RateLimitError, APITimeoutError, APIStatusError) as e:
            print_colored(f"  API ERROR: {type(e).__name__}", Fore.RED)

            if attempt < MAX_RETRIES - 1:
                # Calculate exponential backoff delay
                delay = INITIAL_DELAY_SECONDS * (2 ** attempt)
                print_colored(
                    f"    -> Retrying in {delay}s... (Attempt {attempt + 2}/{MAX_RETRIES})",
                    Fore.YELLOW
                )
                time.sleep(delay)
            else:
                print_colored(
                    f"    -> FAILED after {MAX_RETRIES} attempts. Skipping.",
                    Fore.RED
                )
                return ""

        except Exception as e:
            print_colored(f"  UNEXPECTED ERROR: {e}", Fore.RED)
            return ""

    return ""


def load_completed_keys() -> Set[str]:
    """
    Load set of already-completed key IDs from output file.

    This function enables resume capability by tracking which translations
    have already been completed. On subsequent runs, these keys will be
    skipped to avoid redundant API calls and costs.

    The function automatically detects the CSV delimiter (comma or semicolon)
    and handles malformed or missing output files gracefully.

    Returns:
        Set[str]: Set of key_id strings that have already been translated
                 Returns empty set if output file doesn't exist or is malformed

    Error Handling:
        - File doesn't exist: Returns empty set (fresh start)
        - CSV parsing error: Returns empty set and logs warning
        - Missing key_id column: Returns empty set and logs warning

    Example:
        completed = load_completed_keys()
        if '12345' in completed:
            print("Key 12345 already translated, skipping...")
    """
    if not OUTPUT_FILE.exists():
        return set()

    delimiter = detect_csv_delimiter(OUTPUT_FILE)

    try:
        with OUTPUT_FILE.open('r', encoding='utf-8') as f:
            return {row['key_id'] for row in csv.DictReader(f, delimiter=delimiter)}
    except (csv.Error, KeyError) as e:
        print_colored(
            f"WARNING: Could not parse {OUTPUT_FILE.name}. Starting fresh.",
            Fore.YELLOW
        )
        return set()


# ==================== PLUGIN SYSTEM FUNCTIONS ====================

def discover_plugins() -> Tuple[List[str], List[str], List[str]]:
    """
    Discover all plugins in the plugins directory by scanning for markers.

    Scans all Python files in the plugins directory and identifies them by
    their marker comments: [PROMPT], [ACTION], or [EXTENSION]. A single plugin
    file can have multiple markers to participate in multiple phases.

    This is a marker-based discovery system that maintains complete separation
    between the core translation engine and plugin implementations. The engine
    only needs to know which plugins exist, not what they do or how they work.

    Plugin Types:
        - PROMPT plugins: Contain [PROMPT] marker
            Their file content is injected into translation prompts

        - ACTION plugins: Contain [ACTION] marker
            Execute before translation, can bypass translation step

        - EXTENSION plugins: Contain [EXTENSION] marker
            Execute after translation for post-processing

    Returns:
        Tuple[List[str], List[str], List[str]]: Three lists of plugin filenames:
            - prompt_plugins: List of PROMPT plugin filenames
            - action_plugins: List of ACTION plugin filenames
            - extension_plugins: List of EXTENSION plugin filenames

    Example:
        prompt_plugins, action_plugins, extension_plugins = discover_plugins()
        print(f"Found {len(action_plugins)} ACTION plugins")
        # Output: "Found 2 ACTION plugins"

    Plugin Example:
        File: plugins/my_plugin.py

        # [ACTION]
        # This plugin checks if translations already exist

        def run():
            # Check some condition
            if translations_exist():
                return True  # Bypass translation
            return False  # Proceed with translation
    """
    prompt_plugins, action_plugins, extension_plugins = [], [], []

    if not PLUGINS_DIR.exists():
        return prompt_plugins, action_plugins, extension_plugins

    for f in PLUGINS_DIR.glob('*.py'):
        if f.name == '__init__.py':
            continue

        try:
            content = f.read_text(encoding='utf-8')

            # Check for markers in file content
            if "[PROMPT]" in content:
                prompt_plugins.append(f.name)
            if "[ACTION]" in content:
                action_plugins.append(f.name)
            if "[EXTENSION]" in content:
                extension_plugins.append(f.name)

        except Exception as e:
            print_colored(
                f"Warning: Could not read plugin {f.name}: {e}",
                Fore.YELLOW
            )

    return prompt_plugins, action_plugins, extension_plugins


def load_prompt_plugins(plugin_names: List[str]) -> str:
    """
    Load content from PROMPT plugins to inject into translation prompts.

    PROMPT plugins are text files (or Python files with docstrings) that contain
    additional instructions to add to the OpenAI system prompt. They allow
    customizing translation behavior without modifying core code.

    All successfully loaded plugin contents are concatenated with spaces and
    returned as a single string to be appended to the system prompt.

    Args:
        plugin_names: List of PROMPT plugin filenames to load

    Returns:
        str: Concatenated content of all PROMPT plugins, space-separated
             Returns empty string if no plugins or all fail to load

    Example:
        Plugin file (plugins/brand_names.py):
        '''
        # [PROMPT]
        6. Never translate the following brand names: MyApp, CompanyName, ProductX
        '''

        Usage:
        addons = load_prompt_plugins(['brand_names.py'])
        # addons: "6. Never translate the following brand names: MyApp, CompanyName, ProductX"

        # This gets appended to the system prompt, affecting all translations
    """
    texts = []

    for name in plugin_names:
        try:
            content = (PLUGINS_DIR / name).read_text(encoding='utf-8')
            texts.append(content)
            print_colored(f"Loaded PROMPT plugin: {name}", Fore.YELLOW)
        except Exception as e:
            print_colored(f"Failed to load PROMPT plugin {name}: {e}", Fore.RED)

    return " ".join(texts)


def run_plugins(plugin_names: List[str], plugin_type: str) -> bool:
    """
    Execute plugins of specified type (ACTION or EXTENSION).

    This function dynamically loads and executes plugin modules. Each plugin
    is imported at runtime and its appropriate function is called based on type.

    Plugin Behavior by Type:

    ACTION Plugins:
        - Must implement a run() function
        - run() should return True to bypass translation, False otherwise
        - First plugin to return True stops execution and signals bypass
        - Used for conditional logic (e.g., skip if already translated)

    EXTENSION Plugins:
        - Must implement a filter_translations() function
        - No return value expected
        - All EXTENSION plugins run sequentially
        - Used for post-processing (e.g., upload results, generate reports)

    Args:
        plugin_names: List of plugin filenames to execute
        plugin_type: Either "ACTION" or "EXTENSION"

    Returns:
        bool: For ACTION plugins, returns True if any plugin signaled bypass
              For EXTENSION plugins, always returns False (no bypass signal)

    Error Handling:
        - Plugin import fails: Logs error and continues with remaining plugins
        - Plugin execution fails: Logs error and continues with remaining plugins
        - Missing required function: Silently skips (allows multi-type plugins)

    Example:
        # ACTION plugin (plugins/check_cache.py):
        def run():
            if cache_exists():
                print("Using cached translations")
                return True  # Signal bypass
            return False

        # Usage:
        should_skip = run_plugins(['check_cache.py'], 'ACTION')
        if should_skip:
            print("Translation bypassed")
    """
    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"Running {plugin_type} plugin: {name}", Fore.BLUE)

        try:
            # Dynamically load plugin module
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if plugin_type == "ACTION" and hasattr(module, 'run'):
                # Capture the result of the plugin's run() function
                result = module.run()

                if result is True:
                    # If plugin returns True, propagate the bypass signal
                    return True

            elif plugin_type == "EXTENSION" and hasattr(module, 'filter_translations'):
                # EXTENSION plugins don't return bypass signal
                module.filter_translations()

        except Exception as e:
            print_colored(f"Failed to run plugin {name}: {e}", Fore.RED)

    # If no plugin signaled bypass, return False
    return False


def show_summary(
    prompt_plugins: List[str],
    action_plugins: List[str],
    extension_plugins: List[str]
) -> None:
    """
    Display translation session summary with configuration and plugin info.

    Shows a formatted summary of the current translation configuration including:
    - OpenAI model being used
    - Input and output file paths
    - Plugin counts and names by type
    - Warning if using mock file instead of real data

    This helps users verify configuration before starting translation and
    understand which plugins will affect the translation process.

    Args:
        prompt_plugins: List of PROMPT plugin filenames
        action_plugins: List of ACTION plugin filenames
        extension_plugins: List of EXTENSION plugin filenames

    Example Output:
        ===== OPENAI TRANSLATION SUMMARY =====
        Model: gpt-4o-mini
        Input file: ready_to_translations.csv
        Output file: translation_done.csv
        Plugins found: 3
         - PROMPT (1): brand_names.py
         - ACTION (1): check_cache.py
         - EXTENSION (1): upload_results.py
        ----------------------------------------
    """
    print_colored("\n===== OPENAI TRANSLATION SUMMARY =====", Fore.CYAN)
    print(f"Model: {OPENAI_MODEL}")
    print(f"Input file: {INPUT_FILE.name}{' (mock)' if INPUT_FILE == MOCK_FILE else ''}")
    print(f"Output file: {OUTPUT_FILE.name}")

    total_plugins = len(prompt_plugins) + len(action_plugins) + len(extension_plugins)
    print(f"Plugins found: {total_plugins}")
    print(f" - PROMPT ({len(prompt_plugins)}): {', '.join(prompt_plugins) if prompt_plugins else 'None'}")
    print(f" - ACTION ({len(action_plugins)}): {', '.join(action_plugins) if action_plugins else 'None'}")
    print(f" - EXTENSION ({len(extension_plugins)}): {', '.join(extension_plugins) if extension_plugins else 'None'}")

    if MOCK_FILE.exists():
        print_colored(
            "⚠️  Using mock file 'ready_to_translations_mock.csv'. Delete it to use the real input.",
            Fore.YELLOW
        )

    print("-" * 40)


# ==================== MAIN TRANSLATION FUNCTION ====================

def run_translation(api_key: str) -> None:
    """
    Execute the complete translation workflow with plugin support.

    This is the main translation orchestrator that coordinates all phases:

    PHASE 1: Setup
        - Initialize OpenAI client
        - Load already-completed keys for resume capability
        - Discover all plugins (PROMPT, ACTION, EXTENSION)
        - Display configuration summary

    PHASE 2: ACTION Plugin Execution
        - Run all ACTION plugins before translation
        - If any plugin returns True, bypass entire translation phase
        - Always run EXTENSION plugins after bypass

    PHASE 3: Translation Preparation (if not bypassed)
        - Load PROMPT plugins to customize translation prompts
        - Validate input file exists
        - Read and parse input CSV
        - Filter out already-completed keys

    PHASE 4: Translation Loop (if not bypassed)
        - For each untranslated key:
            - Validate required columns exist
            - Handle empty source text (skip API call)
            - Translate to all target languages
            - Write results incrementally to output file
        - Track progress and timing statistics

    PHASE 5: EXTENSION Plugin Execution
        - Run all EXTENSION plugins for post-processing
        - Execute regardless of whether translation was bypassed

    Args:
        api_key: Valid OpenAI API key for authentication

    Resume Capability:
        The function automatically resumes from the last completed key by:
        1. Loading completed key IDs from output file
        2. Filtering them out from input data
        3. Only translating remaining keys

        This allows:
        - Recovering from crashes without losing progress
        - Stopping and resuming at any time
        - Avoiding redundant API calls and costs

    Output Format:
        Creates/appends to reports/translation_done.csv:

        key_name,key_id,languages,translation_id,translation,translated
        welcome,001,"it,de",t001,"Welcome","Benvenuto|Willkommen"

        The 'translated' column contains pipe-separated translations in the
        same order as languages in the 'languages' column.

    Error Handling:
        - Missing input file: Log error and return
        - Empty input file: Log info and return
        - All keys completed: Log success message and return
        - Missing required columns: Skip row and continue
        - Empty source text: Skip API call, write empty placeholder
        - API failures: Retry with backoff, write empty on final failure
        - Plugin errors: Log error and continue with remaining plugins

    Example:
        api_key = get_api_key()
        run_translation(api_key)
        # Translates all pending keys and saves results
    """
    # PHASE 1: Setup
    client = OpenAI(api_key=api_key)
    completed_keys = load_completed_keys()

    prompt_plugins, action_plugins, extension_plugins = discover_plugins()
    show_summary(prompt_plugins, action_plugins, extension_plugins)

    # PHASE 2: ACTION Plugin Execution
    # Run ACTION plugins and check if they signal a bypass
    should_bypass = run_plugins(action_plugins, "ACTION")

    if should_bypass:
        # If a plugin signaled bypass, run EXTENSION plugins and terminate
        print_colored("\n⏩ Translation step bypassed by ACTION plugin.", Fore.YELLOW)
        print_colored("\nRunning EXTENSION plugins on translated data...", Fore.CYAN)
        run_plugins(extension_plugins, "EXTENSION")
        return

    # PHASE 3: Translation Preparation
    # Load PROMPT plugins only if we're not bypassing translation
    prompt_addons = load_prompt_plugins(prompt_plugins)

    if not INPUT_FILE.exists():
        print_colored(f"ERROR: Input file not found at {INPUT_FILE}", Fore.RED)
        return

    delimiter = detect_csv_delimiter(INPUT_FILE)

    with INPUT_FILE.open('r', encoding='utf-8') as infile:
        all_rows = [row for row in csv.DictReader(infile, delimiter=delimiter)]

    if not all_rows:
        print_colored("INFO: Input file is empty. Nothing to translate.", Fore.YELLOW)
        return

    # Filter out already-completed keys for resume capability
    rows_to_translate = [row for row in all_rows if row['key_id'] not in completed_keys]
    total_keys_to_translate = len(rows_to_translate)

    if total_keys_to_translate == 0:
        print_colored("\nAll translations are already complete!", Fore.GREEN)
        return

    print_colored(f"\nFound {total_keys_to_translate} new keys to translate.", Fore.CYAN)

    # PHASE 4: Translation Loop
    start_time = time.time()
    translated_in_session = 0

    with OUTPUT_FILE.open('a', newline='', encoding='utf-8') as outfile:
        # The output CSV structure is derived from the input + the new 'translated' column
        # This corresponds to: key_name,key_id,languages,translation_id,translation,translated
        fieldnames = list(all_rows[0].keys()) + ['translated']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        # Write header if file is empty (new file or first write)
        if outfile.tell() == 0:
            writer.writeheader()

        for index, row in enumerate(rows_to_translate):
            key_name = row.get('key_name', 'N/A')

            # NEW: Validation of essential columns for each row
            required_cols = ['key_id', 'translation', 'languages']
            if not all(col in row for col in required_cols):
                print_colored(
                    f'\nERROR: Skipping key "{key_name}" ({index + 1}/{total_keys_to_translate}) '
                    f'due to missing required columns.',
                    Fore.RED
                )
                continue

            print_colored(
                f'\nTranslating key "{key_name}" ({index + 1}/{total_keys_to_translate})...',
                Fore.WHITE
            )

            # Parse target languages from comma-separated list
            langs = [lang.strip() for lang in row['languages'].split(',') if lang.strip()]
            translations = []

            # NEW: Handling of empty translation strings
            source_text = row.get('translation', '').strip()

            if not source_text:
                # Source text is empty, skip API calls and create empty placeholders
                print_colored("  -> Source text is empty. Skipping API calls.", Fore.YELLOW)
                translations = [""] * len(langs)
            else:
                # Translate to each target language
                for lang_code in langs:
                    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
                    print(f"  -> Translating to {lang_name} ({lang_code})... ", end="", flush=True)

                    translation = translate_text(client, source_text, lang_code, prompt_addons)

                    if translation:
                        print_colored("DONE", Fore.GREEN)
                        translations.append(translation)
                        translated_in_session += 1
                    else:
                        print_colored("FAILED", Fore.RED)
                        translations.append("")  # Add empty placeholder for failures

            # Write to CSV file only if there are translations or if source was empty
            # (to mark as completed and avoid re-processing)
            row_to_write = row.copy()
            row_to_write['translated'] = '|'.join(translations)
            writer.writerow(row_to_write)
            outfile.flush()  # Ensure data is written immediately for resume capability

    # PHASE 5: Completion and Statistics
    elapsed = time.time() - start_time
    print_colored(f"\n✅ All tasks complete. Results saved to {OUTPUT_FILE}", Fore.GREEN)
    print_colored("\n===== TRANSLATION COMPLETE =====", Fore.CYAN)
    print_colored(f"Total translations performed in this session: {translated_in_session}", Fore.CYAN)
    print_colored(f"Elapsed time: {elapsed:.2f} seconds\n", Fore.CYAN)

    # PHASE 6: EXTENSION Plugin Execution
    run_plugins(extension_plugins, "EXTENSION")


def main() -> None:
    """
    Main entry point for the OpenAI translation module.

    Initializes the translation process by:
    1. Loading the OpenAI API key from configuration
    2. Starting the translation workflow
    3. Handling any fatal errors gracefully

    This function can be called:
    - Directly: python3 translate_with_openai.py
    - As module: python3 -m lokalise_translation_manager.translator.translate_with_openai
    - From core: Automatically called by core.py in Step 8

    Error Handling:
        - FileNotFoundError: Configuration file missing or API key not found
        - Exception: Any other unexpected error during translation

    Example:
        if __name__ == "__main__":
            main()
    """
    try:
        print_colored("\n🔁 Starting OpenAI Translation...", Fore.CYAN)
        key = get_api_key()
        run_translation(key)
    except FileNotFoundError as e:
        print_colored(f"\nERROR: Configuration file not found. {e}", Fore.RED)
    except Exception as e:
        print_colored(f"\nFATAL ERROR: An unexpected error stopped the script: {e}", Fore.RED)


if __name__ == "__main__":
    main()
