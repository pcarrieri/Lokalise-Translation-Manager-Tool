import os
import csv
import json
import time
import sys
from pathlib import Path
from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError, APIStatusError
import importlib.util

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    colorama_available = True
except ImportError:
    colorama_available = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "config" / "user_config.json"

MOCK_FILE = REPORTS_DIR / "ready_to_translations_mock.csv"
REAL_FILE = REPORTS_DIR / "ready_to_translations.csv"
INPUT_FILE = MOCK_FILE if MOCK_FILE.exists() else REAL_FILE
OUTPUT_FILE = REPORTS_DIR / "translation_done.csv"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"

# --- CONFIGURAZIONE AVANZATA ---
MAX_RETRIES = 5
INITIAL_DELAY_SECONDS = 5
OPENAI_MODEL = "gpt-4o-mini" # Modello consigliato per performance/costi

# Mapping dei codici lingua ai nomi completi per un prompt migliore
LANGUAGE_NAMES = {
    "en": "English", "de": "German", "fr": "French", "it": "Italian", "pl": "Polish",
    "sv": "Swedish", "nb": "Norwegian (Bokmål)", "da": "Danish", "fi": "Finnish",
    "lt_LT": "Lithuanian", "lv_LV": "Latvian", "et_EE": "Estonian",
    "tr_TR": "Turkish", "ar": "Arabic"
}
# --------------------------------

def print_colored(text, color=None):
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def get_api_key():
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            config = json.load(f)
            return config["openai"]["api_key"]
    raise FileNotFoundError("OpenAI API key not found in config")

def translate_text(client, text, lang_code, prompt_addons=""):
    """
    Esegue la traduzione con un prompt robusto e un meccanismo di retry.
    """
    lang_name = LANGUAGE_NAMES.get(lang_code, lang_code)
    system_prompt = f"""You are a professional software localization expert. Your task is to translate the given English text for an application's user interface.

**Instructions:**
1. Translate the following text into **{lang_name}** (language code: `{lang_code}`).
2. **Output ONLY the translated string.** Do not include explanations, introductions, quotes, or any other text.
3. **Preserve placeholders** (like `{{variable}}`, `%s`, `%d`) exactly as they appear in the original text. Do not translate them.
4. Maintain a neutral and clear tone suitable for software.
5. Ignore any URLs found in the text.
{prompt_addons}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.2, # Un valore basso per traduzioni più consistenti
                timeout=90
            )
            return response.choices[0].message.content.strip()
        except (APIConnectionError, RateLimitError, APITimeoutError, APIStatusError) as e:
            print_colored(f"  API ERROR: {type(e).__name__}", Fore.RED)
            if attempt < MAX_RETRIES - 1:
                delay = INITIAL_DELAY_SECONDS * (2 ** attempt)
                print_colored(f"    -> Retrying in {delay}s... (Attempt {attempt + 2}/{MAX_RETRIES})", Fore.YELLOW)
                time.sleep(delay)
            else:
                print_colored(f"    -> FAILED after {MAX_RETRIES} attempts. Skipping.", Fore.RED)
                return ""
        except Exception as e:
            print_colored(f"  UNEXPECTED ERROR: {e}", Fore.RED)
            return ""
    return ""

def load_completed_keys():
    if not OUTPUT_FILE.exists():
        return set()
    with OUTPUT_FILE.open('r', encoding='utf-8') as f:
        try:
            return {row['key_id'] for row in csv.DictReader(f)}
        except (csv.Error, KeyError):
             print_colored(f"WARNING: Could not parse {OUTPUT_FILE.name}. Starting fresh.", Fore.YELLOW)
             return set()

# --- Funzioni per i plugin (invariate) ---
def discover_plugins():
    prompt_plugins, action_plugins, extension_plugins = [], [], []
    if PLUGINS_DIR.exists():
        for f in PLUGINS_DIR.glob('*.py'):
            content = f.read_text()
            if "[PROMPT]" in content: prompt_plugins.append(f.name)
            if "[ACTION]" in content: action_plugins.append(f.name)
            if "[EXTENSION]" in content: extension_plugins.append(f.name)
    return prompt_plugins, action_plugins, extension_plugins

def load_prompt_plugins(plugin_names):
    texts = []
    for name in plugin_names:
        try:
            content = (PLUGINS_DIR / name).read_text()
            texts.append(content)
            print_colored(f"Loaded PROMPT plugin: {name}", Fore.YELLOW)
        except Exception as e:
            print_colored(f"Failed to load PROMPT plugin {name}: {e}", Fore.RED)
    return " ".join(texts)

def run_plugins(plugin_names, plugin_type):
    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"Running {plugin_type} plugin: {name}", Fore.BLUE)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if plugin_type == "ACTION" and hasattr(module, 'run'):
                module.run()
            elif plugin_type == "EXTENSION" and hasattr(module, 'filter_translations'):
                module.filter_translations()
        except Exception as e:
            print_colored(f"Failed to run plugin {name}: {e}", Fore.RED)

def show_summary(prompt_plugins, action_plugins, extension_plugins):
    print_colored("\n===== OPENAI TRANSLATION SUMMARY =====", Fore.CYAN)
    print(f"Model: {OPENAI_MODEL}")
    print(f"Input file: {INPUT_FILE.name}{' (mock)' if INPUT_FILE == MOCK_FILE else ''}")
    print(f"Output file: {OUTPUT_FILE.name}")
    print(f"Plugins found: {len(prompt_plugins) + len(action_plugins) + len(extension_plugins)}")
    print(f" - PROMPT ({len(prompt_plugins)}): {', '.join(prompt_plugins) if prompt_plugins else 'None'}")
    print(f" - ACTION ({len(action_plugins)}): {', '.join(action_plugins) if action_plugins else 'None'}")
    print(f" - EXTENSION ({len(extension_plugins)}): {', '.join(extension_plugins) if extension_plugins else 'None'}")
    if MOCK_FILE.exists():
        print_colored("⚠️  Using mock file 'ready_to_translations_mock.csv'. Delete it to use the real input.", Fore.YELLOW)
    print("-" * 40)

def run_translation(api_key):
    client = OpenAI(api_key=api_key)
    completed_keys = load_completed_keys()
    
    prompt_plugins, action_plugins, extension_plugins = discover_plugins()
    show_summary(prompt_plugins, action_plugins, extension_plugins)

    run_plugins(action_plugins, "ACTION")
    prompt_addons = load_prompt_plugins(prompt_plugins)
    
    if not INPUT_FILE.exists():
        print_colored(f"ERROR: Input file not found at {INPUT_FILE}", Fore.RED)
        return
        
    with INPUT_FILE.open('r', encoding='utf-8') as infile:
         all_rows = [row for row in csv.DictReader(infile)]

    if not all_rows:
        print_colored("INFO: Input file is empty. Nothing to translate.", Fore.YELLOW)
        return

    rows_to_translate = [row for row in all_rows if row['key_id'] not in completed_keys]
    total_keys_to_translate = len(rows_to_translate)
    
    if total_keys_to_translate == 0:
        print_colored("\nAll translations are already complete!", Fore.GREEN)
        return

    print_colored(f"\nFound {total_keys_to_translate} new keys to translate.", Fore.CYAN)
    start_time = time.time()
    translated_in_session = 0

    with OUTPUT_FILE.open('a', newline='', encoding='utf-8') as outfile:
        # La struttura del CSV di output è derivata dall'input + la nuova colonna 'translated'
        # Questo corrisponde a: key_name,key_id,languages,translation_id,translation,translated
        fieldnames = list(all_rows[0].keys()) + ['translated']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if outfile.tell() == 0:
            writer.writeheader()

        for index, row in enumerate(rows_to_translate):
            key_name = row.get('key_name', 'N/A')
            
            # --- NUOVO: Validazione delle colonne essenziali per ogni riga ---
            required_cols = ['key_id', 'translation', 'languages']
            if not all(col in row for col in required_cols):
                print_colored(f'\nERROR: Skipping key "{key_name}" ({index + 1}/{total_keys_to_translate}) due to missing required columns.', Fore.RED)
                continue
            
            print_colored(f'\nTranslating key "{key_name}" ({index + 1}/{total_keys_to_translate})...', Fore.WHITE)
            
            langs = [lang.strip() for lang in row['languages'].split(',') if lang.strip()]
            translations = []

            # --- NUOVO: Gestione delle stringhe di traduzione vuote ---
            source_text = row.get('translation', '').strip()
            if not source_text:
                print_colored("  -> Source text is empty. Skipping API calls.", Fore.YELLOW)
                translations = [""] * len(langs) # Crea placeholder vuoti
            else:
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
                        translations.append("") # Aggiungi placeholder per fallimenti

            # Scrive nel file CSV solo se ci sono traduzioni o se la sorgente era vuota (per marcare come completato)
            row_to_write = row.copy()
            row_to_write['translated'] = '|'.join(translations)
            writer.writerow(row_to_write)
            outfile.flush()

    elapsed = time.time() - start_time
    print_colored(f"\n✅ All tasks complete. Results saved to {OUTPUT_FILE}", Fore.GREEN)
    print_colored("\n===== TRANSLATION COMPLETE =====", Fore.CYAN)
    print_colored(f"Total translations performed in this session: {translated_in_session}", Fore.CYAN)
    print_colored(f"Elapsed time: {elapsed:.2f} seconds\n", Fore.CYAN)

    run_plugins(extension_plugins, "EXTENSION")

def main():
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
