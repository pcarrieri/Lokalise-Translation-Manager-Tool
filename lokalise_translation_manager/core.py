# core.py - Main execution flow of Lokalise Translation Manager Tool

import importlib

try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

def print_colored(text, color):
    print(color + text if color_enabled else text)

def run_tool():
    try:
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

        # Step 4: Additional steps (e.g., download all Lokalise keys)
        # You can uncomment and expand here if needed

        print_colored("\n✅ All steps completed.", Fore.GREEN)

    except ModuleNotFoundError as e:
        print_colored(f"Error: Missing module - {e}", Fore.RED)
    except Exception as e:
        print_colored(f"Unexpected error: {e}", Fore.RED)

if __name__ == "__main__":
    run_tool()
