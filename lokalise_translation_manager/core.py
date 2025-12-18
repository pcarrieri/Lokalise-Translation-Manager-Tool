"""
Core Orchestration Module for Lokalise Translation Manager Tool

This module serves as the main entry point and orchestrator for the entire
translation workflow. It coordinates all steps from downloading translations
from Lokalise, scanning project files, translating missing keys, and uploading
results back to Lokalise.

Workflow Steps:
    0. Download existing translations from Lokalise
    1. Scan iOS project for localization keys
    2. Scan Android project for localization keys
    3. Merge missing translations from both platforms
    4. Download all Lokalise keys metadata
    5. Normalize translation data
    6. Prepare final file for translation
    7. Translate missing keys (with optional plugin bypass)
    8. Upload translated keys to Lokalise
    9. Clean up unused keys
   10. Open web UI for report visualization

Plugin System:
    The module implements a generic plugin architecture with three types:
    - ACTION plugins: Run before translation, can bypass OpenAI
    - PROMPT plugins: Modify translation prompts (handled in translator)
    - EXTENSION plugins: Process translated data after translation

    Plugin discovery is marker-based and completely agnostic to implementation
    details. The core module only checks IF plugins exist, not WHAT they do.

Dependencies:
    - colorama: For colored terminal output (optional)
    - Submodules: download, scanner, utils, translator

Usage:
    from lokalise_translation_manager import core
    core.run_tool()

Author: Lokalise Translation Manager Tool
Version: 1.0.0
"""

import importlib
import webbrowser
from pathlib import Path
import importlib.util
from typing import List, Optional
from lokalise_translation_manager.utils.plugin_manager import (
    get_enabled_plugins_by_type,
    sync_plugin_config,
    print_plugin_status
)

# Try to import colorama for colored output
try:
    from colorama import Fore, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False
    # Define dummy Fore class if colorama not available
    class Fore:
        """Dummy color class when colorama is not installed"""
        CYAN = ''
        GREEN = ''
        YELLOW = ''
        RED = ''
        BLUE = ''

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"


def print_colored(text: str, color: str) -> None:
    """
    Print colored text to the console if colorama is available.

    This function provides graceful degradation when colorama is not installed.
    If colorama is available, text is printed with the specified color. Otherwise,
    plain text is printed.

    Args:
        text: The message to print
        color: The color from colorama.Fore (e.g., Fore.CYAN, Fore.GREEN)

    Example:
        print_colored("Success!", Fore.GREEN)
        print_colored("Warning: Check this", Fore.YELLOW)
    """
    print(color + text if color_enabled else text)


def open_browser() -> None:
    """
    Open the default web browser to view CSV reports.

    Opens the React web UI running on localhost:5173, which provides
    an interactive interface for viewing and editing generated CSV reports.

    The web UI features:
    - File picker for selecting reports
    - AG Grid for data visualization
    - Inline editing capabilities
    - Save functionality

    Note:
        Assumes the web UI is already running on port 5173. The UI should
        be started separately via LokaliseTool.command or LokaliseTool.bat.
    """
    webbrowser.open('http://localhost:5173')


def ask_user_yes_no(question: str) -> bool:
    """
    Prompt the user with a yes/no question and return the response.

    This function continuously prompts the user until a valid response is
    received. It accepts various forms of yes/no answers including 'y', 'yes',
    'n', 'no', and Italian variants ('s', 'si').

    Args:
        question: The question to ask the user

    Returns:
        True if the user responds with 'yes' (or variants)
        False if the user responds with 'no' (or variants)

    Example:
        if ask_user_yes_no("Do you want to continue?"):
            # User said yes
            proceed()
        else:
            # User said no
            cancel()

    Note:
        This is a blocking operation that waits for user input.
        The function will loop until a valid response is provided.
    """
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ['y', 'yes', 's', 'si']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' (yes) or 'n' (no).")


def discover_action_plugins() -> List[str]:
    """
    Discover and return enabled ACTION-type plugins.

    This function uses the plugin configuration manager to find ACTION plugins
    that are both present in the plugins directory AND enabled in the
    configuration file (config/plugins_config.json).

    ACTION plugins run before translation and can bypass the OpenAI translation
    step by returning True from their run() function.

    The discovery process:
    1. Reads plugin configuration from config/plugins_config.json
    2. Scans all .py files in the plugins directory for [ACTION] marker
    3. Returns only plugins that are marked as enabled in configuration
    4. Respects auto_discover setting for new plugins

    Returns:
        List of enabled plugin filenames (e.g., ['inject_updated_translations.py'])

    Configuration:
        Plugins can be enabled/disabled in config/plugins_config.json:
        {
            "plugins": {
                "inject_updated_translations.py": {
                    "enabled": true,
                    "type": "ACTION"
                }
            }
        }

    Example:
        action_plugins = discover_action_plugins()
        if action_plugins:
            print(f"Found {len(action_plugins)} enabled ACTION plugins")
            # Plugins will be executed in translate_with_openai.py

    Note:
        - Plugins can be disabled without deleting files
        - New plugins are auto-enabled if auto_discover setting is true
        - Configuration is synchronized automatically on first run

    See Also:
        - discover_extension_plugins(): For discovering EXTENSION plugins
        - lokalise_translation_manager.utils.plugin_manager: Configuration management
        - config/plugins_config.json: Plugin configuration file
    """
    return get_enabled_plugins_by_type("ACTION")


def discover_extension_plugins() -> List[str]:
    """
    Discover and return enabled EXTENSION-type plugins.

    This function uses the plugin configuration manager to find EXTENSION plugins
    that are both present in the plugins directory AND enabled in the
    configuration file (config/plugins_config.json).

    EXTENSION plugins run after translation (or after ACTION plugin bypass) and
    process the translated data.

    Common uses for EXTENSION plugins:
    - Filtering translations by category (e.g., payment-related keys)
    - Generating additional reports
    - Validation of translated content
    - Post-processing of translation data

    The discovery process:
    1. Reads plugin configuration from config/plugins_config.json
    2. Scans all .py files in the plugins directory for [EXTENSION] marker
    3. Returns only plugins that are marked as enabled in configuration
    4. Respects auto_discover setting for new plugins

    Returns:
        List of enabled plugin filenames (e.g., ['myPayments.py'])

    Configuration:
        Plugins can be enabled/disabled in config/plugins_config.json:
        {
            "plugins": {
                "myPayments.py": {
                    "enabled": true,
                    "type": "EXTENSION"
                }
            }
        }

    Example:
        extension_plugins = discover_extension_plugins()
        if extension_plugins:
            print(f"Found {len(extension_plugins)} enabled EXTENSION plugins")
            run_extension_plugins(extension_plugins)

    Note:
        - Plugins can be disabled without deleting files
        - New plugins are auto-enabled if auto_discover setting is true
        - Configuration is synchronized automatically on first run

    See Also:
        - run_extension_plugins(): Executes discovered EXTENSION plugins
        - discover_action_plugins(): For discovering ACTION plugins
        - lokalise_translation_manager.utils.plugin_manager: Configuration management
        - config/plugins_config.json: Plugin configuration file
    """
    return get_enabled_plugins_by_type("EXTENSION")


def run_extension_plugins(plugin_names: List[str]) -> None:
    """
    Execute EXTENSION-type plugins.

    This function dynamically loads and executes each EXTENSION plugin.
    Plugins are expected to have either a main() or filter_translations()
    function which will be called automatically.

    Execution process:
    1. For each plugin name, construct the full path
    2. Dynamically load the plugin module
    3. Look for main() or filter_translations() function
    4. Execute the function
    5. Handle any errors gracefully (one plugin failure doesn't stop others)

    Args:
        plugin_names: List of plugin filenames to execute

    Example:
        plugins = discover_extension_plugins()
        run_extension_plugins(plugins)
        # Output:
        # Running EXTENSION plugins (2)...
        #   → Running EXTENSION plugin: myPayments.py
        #   → Running EXTENSION plugin: customFilter.py

    Error Handling:
        - If a plugin file cannot be loaded, an error is printed but execution continues
        - If a plugin lacks the expected functions, a warning is printed
        - Plugin errors are isolated (one failure doesn't affect others)

    Note:
        This function is called in two scenarios:
        1. When translation is skipped (user choice)
        2. After translation completes (in translate_with_openai.py)
        3. After ACTION plugin bypasses translation

    See Also:
        - discover_extension_plugins(): Finds plugins to execute
        - Plugin architecture in GENERIC_ARCHITECTURE.md
    """
    if not plugin_names:
        print_colored("No EXTENSION plugins found.", Fore.YELLOW)
        return

    print_colored(
        f"\nRunning EXTENSION plugins ({len(plugin_names)})...",
        Fore.CYAN
    )

    for name in plugin_names:
        path = PLUGINS_DIR / name
        print_colored(f"  → Running EXTENSION plugin: {name}", Fore.BLUE)

        try:
            # Dynamically load the plugin module
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # EXTENSION plugins typically have main() or filter_translations()
            if hasattr(module, 'main'):
                module.main()
            elif hasattr(module, 'filter_translations'):
                module.filter_translations()
            else:
                print_colored(
                    f"    Warning: Plugin {name} has no main() or "
                    f"filter_translations() function",
                    Fore.YELLOW
                )

        except Exception as e:
            print_colored(
                f"    ERROR: Failed to run plugin {name}: {e}",
                Fore.RED
            )


def run_tool() -> None:
    """
    Execute the complete translation workflow.

    This is the main orchestrator function that coordinates all steps of the
    translation process. It handles the entire pipeline from downloading
    existing translations to uploading new ones.

    Workflow Steps:
        0. Download existing translations from Lokalise
        1. Scan iOS project for NSLocalizedString() calls
        2. Scan Android project for R.string.* and @string/* references
        3. Merge missing translations from both platforms
        4. Download all Lokalise keys for metadata enrichment
        5. Normalize translation data (consistent format)
        6. Prepare final input file for translation engine
        7. Translate missing keys using OpenAI (or bypass with ACTION plugins)
        8. Upload translated keys to Lokalise
        9. Clean up unused keys (with user confirmation)
       10. Open web UI for report visualization

    Plugin Integration:
        - ACTION plugins are discovered and given opportunity to execute
        - If ACTION plugins exist, translation step is always entered
        - Plugins decide autonomously whether to bypass OpenAI translation
        - EXTENSION plugins run after translation (or bypass)

    Error Handling:
        - ModuleNotFoundError: If required submodules are missing
        - Generic Exception: For any unexpected errors during execution
        - Errors are printed in red and execution stops

    Example:
        from lokalise_translation_manager.core import run_tool
        run_tool()
        # Executes the complete workflow

    Note:
        This function is typically called from run.py, which handles
        initial setup (dependencies, configuration) before calling this.

    Side Effects:
        - Creates/modifies files in /reports/ directory
        - Makes API calls to Lokalise and OpenAI (unless mocked)
        - Opens web browser at the end
        - May prompt user for input (skip translation, delete keys)

    See Also:
        - run.py: Entry point that calls this function
        - CLAUDE.md: Complete workflow documentation
    """
    try:
        # ===================================================================
        # PLUGIN SYSTEM: Synchronize and Display Status
        # ===================================================================
        print_colored("\n🔌 Synchronizing plugin configuration...", Fore.CYAN)
        new_plugins, missing_plugins = sync_plugin_config()

        if new_plugins:
            print_colored(
                f"  ✅ Auto-discovered {len(new_plugins)} new plugin(s): {', '.join(new_plugins)}",
                Fore.GREEN
            )

        if missing_plugins:
            print_colored(
                f"  ⚠️  {len(missing_plugins)} plugin(s) in config but not found: {', '.join(missing_plugins)}",
                Fore.YELLOW
            )

        # Display plugin status
        print_plugin_status()

        # ===================================================================
        # STEP 0: Download Lokalise Files
        # ===================================================================
        print_colored("\nDownloading Lokalise files...", Fore.CYAN)
        download_module = importlib.import_module(
            "lokalise_translation_manager.download.download_lokalise_files"
        )
        download_module.main()

        # ===================================================================
        # STEP 1: Scan iOS Project
        # ===================================================================
        print_colored("\nRunning iOS scanner...", Fore.CYAN)
        ios_scanner = importlib.import_module(
            "lokalise_translation_manager.scanner.ios_scanner"
        )
        ios_scanner.main()

        # ===================================================================
        # STEP 2: Scan Android Project
        # ===================================================================
        print_colored("\nRunning Android scanner...", Fore.CYAN)
        android_scanner = importlib.import_module(
            "lokalise_translation_manager.scanner.android_scanner"
        )
        android_scanner.main()

        # ===================================================================
        # STEP 3: Merge Platform Results
        # ===================================================================
        print_colored(
            "\nMerging iOS and Android missing translations...",
            Fore.CYAN
        )
        merge_module = importlib.import_module(
            "lokalise_translation_manager.utils.merge_translations"
        )
        merge_module.run_merge()

        # ===================================================================
        # STEP 4: Download Lokalise Keys
        # ===================================================================
        print_colored(
            "\nDownloading all Lokalise keys for final processing...",
            Fore.CYAN
        )
        keys_module = importlib.import_module(
            "lokalise_translation_manager.utils.download_lokalise_keys"
        )
        keys_module.main()

        # ===================================================================
        # STEP 5: Normalize Data
        # ===================================================================
        print_colored("\nNormalizing data for translation...", Fore.CYAN)
        normalize_module = importlib.import_module(
            "lokalise_translation_manager.utils.normalize_translations"
        )
        normalize_module.process_normalization()

        # ===================================================================
        # STEP 6: Prepare Translation Input
        # ===================================================================
        print_colored(
            "\nPreparing final file for translation engine...",
            Fore.CYAN
        )
        prepare_module = importlib.import_module(
            "lokalise_translation_manager.utils.prepare_translations"
        )
        prepare_module.main()

        # ===================================================================
        # STEP 7: Translation (with Plugin Support)
        # ===================================================================
        # Generic plugin discovery - check if ACTION plugins exist
        action_plugins = discover_action_plugins()
        skip_translation = False

        if action_plugins:
            # If ACTION plugins exist, always enter translate_with_openai.py
            # The plugins will decide autonomously whether to bypass or not
            print_colored(
                f"\nDetected {len(action_plugins)} ACTION plugin(s): "
                f"{', '.join(action_plugins)}",
                Fore.CYAN
            )
            print_colored(
                "Entering translation step to allow ACTION plugins to execute...",
                Fore.CYAN
            )
            skip_translation = False

        elif TRANSLATION_DONE_FILE.exists():
            # No ACTION plugins, but translation_done.csv exists
            # Ask the user if they want to skip translation
            print_colored(
                "\n⚠️  NOTICE: A 'translation_done.csv' file already exists!",
                Fore.YELLOW
            )
            print_colored(
                "This means translations may have already been completed "
                "in a previous run.",
                Fore.YELLOW
            )
            print_colored("\nOptions:", Fore.CYAN)
            print("  - Answer 'y' to SKIP the translation step and "
                  "proceed directly to upload")
            print("  - Answer 'n' to RE-RUN the translation "
                  "(will make new API calls to OpenAI)")

            skip_translation = ask_user_yes_no(
                "\nDo you want to SKIP the translation step and "
                "use existing translations?"
            )

        if skip_translation:
            # User chose to skip translation
            print_colored(
                "\n✓ Skipping translation step. Using existing "
                "translation_done.csv file.",
                Fore.GREEN
            )

            # Even when skipping translation, we must run EXTENSION plugins
            # because they operate on already-translated data (e.g., filtering)
            print_colored(
                "\nChecking for EXTENSION plugins to run on existing translations...",
                Fore.CYAN
            )
            extension_plugins = discover_extension_plugins()

            if extension_plugins:
                print_colored(
                    f"Found {len(extension_plugins)} EXTENSION plugin(s): "
                    f"{', '.join(extension_plugins)}",
                    Fore.YELLOW
                )
                run_extension_plugins(extension_plugins)
            else:
                print_colored("No EXTENSION plugins found to run.", Fore.YELLOW)
        else:
            # Perform translation (with possible ACTION plugin bypass)
            print_colored("\nPerforming translations with OpenAI...", Fore.CYAN)
            translate_module = importlib.import_module(
                "lokalise_translation_manager.translator.translate_with_openai"
            )
            translate_module.main()
            # Note: EXTENSION plugins are executed automatically in
            # translate_with_openai.py after translation completes

        # ===================================================================
        # STEP 8: Upload to Lokalise
        # ===================================================================
        print_colored("\nUploading translations to Lokalise...", Fore.CYAN)
        upload_module = importlib.import_module(
            "lokalise_translation_manager.utils.upload_translations"
        )
        upload_module.main()

        # ===================================================================
        # STEP 9: Clean Unused Keys
        # ===================================================================
        print_colored("\nListing all unused keys from Lokalise...", Fore.CYAN)
        cleanup_module = importlib.import_module(
            "lokalise_translation_manager.utils.cleanup_unused_keys"
        )
        cleanup_module.main()

        # ===================================================================
        # STEP 10: Success & Web UI
        # ===================================================================
        print_colored("\n✅ All steps completed.", Fore.GREEN)

        print_colored(
            "\nOpening browser for CSV report visualization...",
            Fore.CYAN
        )
        open_browser()

    except ModuleNotFoundError as e:
        print_colored(f"Error: Missing module - {e}", Fore.RED)
        print_colored(
            "Please ensure all dependencies are installed: "
            "pip install -r requirements.txt",
            Fore.YELLOW
        )
    except Exception as e:
        print_colored(f"Unexpected error: {e}", Fore.RED)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_tool()
