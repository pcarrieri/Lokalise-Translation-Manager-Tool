# lokalise_translation_manager/translator/translate_with_openai.py

import os
import csv
import json
import time
import itertools
import sys
import threading
from pathlib import Path
from openai import OpenAI
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

stop_loader = False


def print_colored(text, color=None):
    if colorama_available and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)


def loader(key_name, languages, total_translations, completed_translations):
    start_time = time.time()
    for c in itertools.cycle(['|', '/', '-', '\\']):
        if stop_loader:
            break
        elapsed = time.time() - start_time
        percent = (completed_translations / total_translations) * 100
        sys.stdout.write(
            f'\rTranslating "{key_name}"... {c} {percent:.2f}% complete. Elapsed: {elapsed:.1f}s')
        sys.stdout.flush()
        time.sleep(0.1)
    print()


def get_api_key():
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            config = json.load(f)
            return config["openai"]["api_key"]
    raise FileNotFoundError("OpenAI API key not found in config")


def translate_text(client, text, lang, prompt=""):
    try:
        instructions = (
            f"Translate the following text to {lang}, ignoring any URLs. {prompt}"
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print_colored(f"ERROR: Translation failed - {e}", Fore.RED)
        return ""


def load_completed_keys():
    if not OUTPUT_FILE.exists():
        return set()
    with OUTPUT_FILE.open('r', encoding='utf-8') as f:
        return {row['key_id'] for row in csv.DictReader(f)}


def count_done_translations():
    if not OUTPUT_FILE.exists():
        return 0
    with OUTPUT_FILE.open('r', encoding='utf-8') as f:
        return sum(len(row['languages'].split(',')) for row in csv.DictReader(f))


def discover_plugins():
    prompt_plugins, action_plugins, extension_plugins = [], [], []
    if PLUGINS_DIR.exists():
        for f in PLUGINS_DIR.glob('*.py'):
            content = f.read_text()
            if "[PROMPT]" in content:
                prompt_plugins.append(f.name)
            if "[ACTION]" in content:
                action_plugins.append(f.name)
            if "[EXTENSION]" in content:
                extension_plugins.append(f.name)
    return prompt_plugins, action_plugins, extension_plugins


def load_prompt_plugins(plugin_names):
    texts = []
    for name in plugin_names:
        path = PLUGINS_DIR / name
        try:
            content = path.read_text()
            texts.append(content)
            print_colored(f"Loaded PROMPT plugin: {name}", Fore.YELLOW)
        except Exception as e:
            print_colored(f"Failed to load PROMPT plugin {name}: {e}", Fore.RED)
    return texts


def run_extension_plugins(plugin_names):
    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"Running EXTENSION plugin: {name}", Fore.MAGENTA)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'filter_translations'):
            module.filter_translations()


def run_action_plugins(plugin_names):
    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"Running ACTION plugin: {name}", Fore.BLUE)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'run'):
            module.run()


def show_summary(prompt_plugins, action_plugins, extension_plugins):
    print_colored("\n===== OPENAI TRANSLATION SUMMARY =====", Fore.CYAN)
    print(f"Model: GPT-4o")
    print(f"Input file: {INPUT_FILE.name}{' (mock)' if INPUT_FILE == MOCK_FILE else ''}")
    print(f"Output file: {OUTPUT_FILE.name}")
    print(f"Plugins found: {len(prompt_plugins) + len(action_plugins) + len(extension_plugins)}")
    print(f" - PROMPT ({len(prompt_plugins)}): {', '.join(prompt_plugins) if prompt_plugins else 'None'}")
    print(f" - ACTION ({len(action_plugins)}): {', '.join(action_plugins) if action_plugins else 'None'}")
    print(f" - EXTENSION ({len(extension_plugins)}): {', '.join(extension_plugins) if extension_plugins else 'None'}")
    print(f"Estimated cost: ~750 tokens per translation")
    print(f"Plugin directory: {PLUGINS_DIR}\n")
    if MOCK_FILE.exists():
        print_colored("⚠️  Using mock file 'ready_to_translations_mock.csv'. Delete it to use the real input.", Fore.YELLOW)


def run_translation(api_key):
    global stop_loader
    client = OpenAI(api_key=api_key)
    completed_keys = load_completed_keys()
    done_count = count_done_translations()

    prompt_plugins, action_plugins, extension_plugins = discover_plugins()
    show_summary(prompt_plugins, action_plugins, extension_plugins)

    run_action_plugins(action_plugins)
    prompt_text = " ".join(load_prompt_plugins(prompt_plugins))

    with INPUT_FILE.open('r', encoding='utf-8') as infile, \
         OUTPUT_FILE.open('a', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['translated']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if outfile.tell() == 0:
            writer.writeheader()

        total = sum(len(r['languages'].split(',')) for r in reader)
        infile.seek(0)
        next(reader)

        start = time.time()
        translated_count = 0

        for row in reader:
            if row['key_id'] in completed_keys:
                continue

            langs = row['languages'].split(',')
            translations = []
            stop_loader = False
            thread = threading.Thread(target=loader, args=(row['key_name'], langs, total, done_count))
            thread.start()

            for lang in langs:
                translation = translate_text(client, row['translation'], lang, prompt_text)
                translations.append(translation)
                done_count += 1
                translated_count += 1

            stop_loader = True
            thread.join()

            row['translated'] = '|'.join(translations)
            writer.writerow(row)

    elapsed = time.time() - start
    print_colored(f"\n✅ Translations saved to {OUTPUT_FILE}", Fore.GREEN)
    print_colored(f"\n===== TRANSLATION COMPLETE =====", Fore.CYAN)
    print_colored(f"Total translations performed: {translated_count}", Fore.CYAN)
    print_colored(f"Elapsed time: {elapsed:.2f} seconds\n", Fore.CYAN)

    run_extension_plugins(extension_plugins)


def main():
    print_colored("\n🔁 Starting OpenAI Translation...", Fore.CYAN)
    key = get_api_key()
    run_translation(key)


if __name__ == "__main__":
    main()
