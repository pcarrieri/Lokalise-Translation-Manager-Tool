# core.py - Main execution flow of Lokalise Translation Manager Tool

import importlib
import webbrowser
from pathlib import Path
import importlib.util

try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"

def print_colored(text, color):
    print(color + text if color_enabled else text)

def open_browser():
    webbrowser.open('http://localhost:5173')

def ask_user_yes_no(question):
    """
    Chiede all'utente una domanda yes/no e ritorna True per 'y' o False per 'n'.

    Args:
        question: La domanda da porre all'utente

    Returns:
        bool: True se l'utente risponde 'y', False se risponde 'n'
    """
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ['y', 'yes', 's', 'si']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' (yes) or 'n' (no).")

def discover_extension_plugins():
    """
    Scopre i plugin di tipo EXTENSION nella directory plugins.

    Returns:
        list: Lista dei nomi dei file dei plugin EXTENSION
    """
    extension_plugins = []
    if PLUGINS_DIR.exists():
        for f in PLUGINS_DIR.glob('*.py'):
            if f.name == '__init__.py':
                continue
            try:
                content = f.read_text()
                if "[EXTENSION]" in content:
                    extension_plugins.append(f.name)
            except Exception as e:
                print_colored(f"Warning: Could not read plugin {f.name}: {e}", Fore.YELLOW)
    return extension_plugins

def run_extension_plugins(plugin_names):
    """
    Esegue i plugin di tipo EXTENSION.

    Args:
        plugin_names: Lista dei nomi dei file dei plugin da eseguire
    """
    if not plugin_names:
        print_colored("No EXTENSION plugins found.", Fore.YELLOW)
        return

    print_colored(f"\nRunning EXTENSION plugins ({len(plugin_names)})...", Fore.CYAN)

    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"  → Running EXTENSION plugin: {name}", Fore.BLUE)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # I plugin EXTENSION hanno tipicamente una funzione main() o filter_translations()
            if hasattr(module, 'main'):
                module.main()
            elif hasattr(module, 'filter_translations'):
                module.filter_translations()
            else:
                print_colored(f"    Warning: Plugin {name} has no main() or filter_translations() function", Fore.YELLOW)

        except Exception as e:
            print_colored(f"    ERROR: Failed to run plugin {name}: {e}", Fore.RED)

def run_tool():
    try:
        # Step 0: Download Lokalise files
        print_colored("\nDownloading Lokalise files...", Fore.CYAN)
        download_module = importlib.import_module("lokalise_translation_manager.download.download_lokalise_files")
        download_module.main()

        # Step 1: Run iOS scanner
        print_colored("\nRunning iOS scanner...", Fore.CYAN)
        ios_scanner = importlib.import_module("lokalise_translation_manager.scanner.ios_scanner")
        ios_scanner.main()

        # Step 2: Run Android scanner
        print_colored("\nRunning Android scanner...", Fore.CYAN)
        android_scanner = importlib.import_module("lokalise_translation_manager.scanner.android_scanner")
        android_scanner.main()

        # Step 3: Merge translations
        print_colored("\nMerging iOS and Android missing translations...", Fore.CYAN)
        merge_module = importlib.import_module("lokalise_translation_manager.utils.merge_translations")
        merge_module.run_merge()

        # Step 4: Download all Lokalise keys after merge
        print_colored("\nDownloading all Lokalise keys for final processing...", Fore.CYAN)
        keys_module = importlib.import_module("lokalise_translation_manager.utils.download_lokalise_keys")
        keys_module.main()

        # Step 5: Normalize and prepare data for translation
        print_colored("\nNormalizing data for translation...", Fore.CYAN)
        normalize_module = importlib.import_module("lokalise_translation_manager.utils.normalize_translations")
        normalize_module.process_normalization()

        # Step 6: Prepare final file for translation engine
        print_colored("\nPreparing final file for translation engine...", Fore.CYAN)
        prepare_module = importlib.import_module("lokalise_translation_manager.utils.prepare_translations")
        prepare_module.main()

        # Step 7: Perform translation using OpenAI
        # Check if translation_done.csv already exists
        skip_translation = False
        if TRANSLATION_DONE_FILE.exists():
            print_colored("\n⚠️  NOTICE: A 'translation_done.csv' file already exists!", Fore.YELLOW)
            print_colored("This means translations may have already been completed in a previous run.", Fore.YELLOW)
            print_colored("\nOptions:", Fore.CYAN)
            print("  - Answer 'y' to SKIP the translation step and proceed directly to upload")
            print("  - Answer 'n' to RE-RUN the translation (will make new API calls to OpenAI)")

            skip_translation = ask_user_yes_no("\nDo you want to SKIP the translation step and use existing translations?")

        if skip_translation:
            print_colored("\n✓ Skipping translation step. Using existing translation_done.csv file.", Fore.GREEN)

            # Anche se skippiamo la traduzione, dobbiamo eseguire i plugin EXTENSION
            # perché operano sui dati già tradotti (es: filtraggio, categorizzazione)
            print_colored("\nChecking for EXTENSION plugins to run on existing translations...", Fore.CYAN)
            extension_plugins = discover_extension_plugins()
            if extension_plugins:
                print_colored(f"Found {len(extension_plugins)} EXTENSION plugin(s): {', '.join(extension_plugins)}", Fore.YELLOW)
                run_extension_plugins(extension_plugins)
            else:
                print_colored("No EXTENSION plugins found to run.", Fore.YELLOW)
        else:
            print_colored("\nPerforming translations with OpenAI...", Fore.CYAN)
            translate_module = importlib.import_module("lokalise_translation_manager.translator.translate_with_openai")
            translate_module.main()
            # I plugin EXTENSION vengono eseguiti automaticamente da translate_with_openai.py

        # Step 8: Upload translations to Lokalise
        print_colored("\nUploading translations to Lokalise...", Fore.CYAN)
        upload_module = importlib.import_module("lokalise_translation_manager.utils.upload_translations")
        upload_module.main()

        # Step 9: Clean unused keys on Lokalise
        print_colored("\nListing all unused keys from Lokalise...", Fore.CYAN)
        cleanup_module = importlib.import_module("lokalise_translation_manager.utils.cleanup_unused_keys")
        cleanup_module.main()

        print_colored("\n✅ All steps completed.", Fore.GREEN)

        # Step 10: Open browser to show CSV reports
        print_colored("\nOpening browser for CSV report visualization...", Fore.CYAN)
        open_browser()

    except ModuleNotFoundError as e:
        print_colored(f"Error: Missing module - {e}", Fore.RED)
    except Exception as e:
        print_colored(f"Unexpected error: {e}", Fore.RED)

if __name__ == "__main__":
    run_tool()
