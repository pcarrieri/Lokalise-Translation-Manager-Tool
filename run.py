"""
Lokalise Translation Manager Tool - Main Entry Point

This module serves as the main entry point for the Lokalise Translation Manager Tool.
It handles dependency installation, configuration setup, and launches the core workflow.

Features:
    - Automatic dependency installation (pip packages)
    - First-time configuration setup with interactive prompts
    - Configuration validation and storage
    - Standard and optional library checking
    - Graceful fallback for missing dependencies
    - Clean error handling and user feedback

Workflow:
    1. Check standard libraries availability
    2. Install dependencies from requirements.txt (preferred)
    3. Fall back to manual installation if requirements.txt fails
    4. Create or validate user_config.json
    5. Launch core translation workflow

Dependencies:
    Standard Libraries (should be available):
        - os, re, csv, time, threading, subprocess, json, configparser, itertools

    Optional Libraries (auto-installed):
        - prettytable: Enhanced table formatting
        - colorama: Colored terminal output
        - tqdm: Progress bars
        - requests: HTTP API calls
        - openai: OpenAI API integration
        - pandas: CSV processing (webapp)
        - flask, flask-cors: Web UI backend (webapp)

Configuration:
    First-time setup creates config/user_config.json with:
    - Lokalise credentials (project_id, api_key)
    - OpenAI API key
    - Project paths (iOS, Android)

Usage:
    python3 run.py

    The tool will:
    1. Install missing dependencies
    2. Prompt for configuration (first time only)
    3. Launch the interactive translation workflow

Example First-Time Run:
    $ python3 run.py

    🧩 Starting Lokalise Translation Manager Tool...

    💡 Tip: You can run "pip install -r requirements.txt" manually to install dependencies.

    ✔ All dependencies installed from requirements.txt.
    ✔ Configuration already exists at config/user_config.json.

    [Core workflow launches...]

Example Configuration (config/user_config.json):
    {
        "lokalise": {
            "project_id": "123456789abcdef.12345678",
            "api_key": "your_lokalise_api_key"
        },
        "openai": {
            "api_key": "sk-your_openai_api_key"
        },
        "project_paths": {
            "ios": "/path/to/ios/project",
            "android": "/path/to/android/project"
        }
    }

Exit Conditions:
    - Missing standard library: Warning displayed but continues
    - Failed dependency install: Warning displayed but continues
    - Core workflow error: Error message displayed and exits
"""

import os
import subprocess
import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

standard_libraries = [
    'os', 're', 'csv', 'time', 'threading', 'subprocess',
    'json', 'configparser', 'itertools'
]

optional_libraries = [
    'prettytable',
    'colorama',
    'tqdm',
    'requests'
]

def install_package(package: str) -> None:
    """
    Install a single Python package using pip.

    Args:
        package: Name of the package to install (e.g., 'colorama', 'requests')

    Note:
        - Installs silently (stdout/stderr redirected to DEVNULL)
        - Prints success or failure message
        - Does not raise exception on failure

    Example:
        install_package('prettytable')
        # Output: ✔ Installed missing library: prettytable
    """
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        print(f"✔ Installed missing library: {package}")
    except subprocess.CalledProcessError:
        print(f"✘ Failed to install: {package}")

def install_from_requirements() -> bool:
    """
    Install all dependencies from requirements.txt file.

    Returns:
        bool: True if installation succeeded, False otherwise

    Note:
        - Looks for requirements.txt in the current directory
        - Installs silently (stdout/stderr to DEVNULL)
        - Falls back to manual installation if this fails
        - Returns False if requirements.txt doesn't exist

    Example:
        if install_from_requirements():
            print("Dependencies installed successfully")
        else:
            print("Need to install dependencies manually")
    """
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            print("✔ All dependencies installed from requirements.txt.")
            return True
        except subprocess.CalledProcessError:
            print("✘ Failed to install from requirements.txt. Falling back to manual installation.")
    return False

def check_standard_libraries() -> None:
    """
    Check availability of standard Python libraries.

    Verifies that all expected standard libraries are available in the
    Python installation. Prints warning if any are missing but does not
    halt execution.

    Standard Libraries Checked:
        - os, re, csv, time, threading, subprocess
        - json, configparser, itertools

    Note:
        - Non-critical check (only displays warning)
        - Does not install missing libraries
        - Silent if all libraries are present
        - Can be removed if unnecessary

    Example Output:
        ⚠ Missing standard libraries: configparser, itertools
    """
    # Optional: Can be silenced or removed entirely
    missing = []
    for lib in standard_libraries:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
    if missing:
        print(f"⚠ Missing standard libraries: {', '.join(missing)}")
    # Otherwise silent

def check_and_install_optional_libraries() -> None:
    """
    Check and install optional Python libraries.

    Checks each optional library and installs it if missing. This function
    is called as a fallback when requirements.txt installation fails or is
    not available.

    Optional Libraries:
        - prettytable: Table formatting for reports
        - colorama: Colored console output
        - tqdm: Progress bars for long operations
        - requests: HTTP requests to Lokalise API

    Note:
        - Only called if requirements.txt installation fails
        - Installs packages one by one
        - Does not halt on individual package failure
        - Prints summary message if all already installed

    Example Output:
        ✔ Installed missing library: prettytable
        ✔ Installed missing library: tqdm
        ✔ All optional libraries are already installed.
    """
    installed_something = False
    for package in optional_libraries:
        try:
            __import__(package)
        except ImportError:
            install_package(package)
            installed_something = True
    if not installed_something:
        print("✔ All optional libraries are already installed.")

def get_user_config() -> None:
    """
    Setup or validate user configuration file.

    Creates config/user_config.json with interactive prompts on first run.
    On subsequent runs, validates that the config file exists.

    Configuration Structure:
        {
            "lokalise": {
                "project_id": "123456789abcdef.12345678",
                "api_key": "your_lokalise_api_key"
            },
            "openai": {
                "api_key": "sk-your_openai_api_key"
            },
            "project_paths": {
                "ios": "/path/to/ios/project",
                "android": "/path/to/android/project"
            }
        }

    Prompts (First-Time Only):
        1. Lokalise project_id
        2. Lokalise api_key
        3. OpenAI API key
        4. iOS project directory path
        5. Android project directory path

    Note:
        - Creates config directory if it doesn't exist
        - Saves configuration as formatted JSON (indent=4)
        - Does not validate API keys or paths
        - Only runs interactive prompts if config doesn't exist

    Example First-Time Output:
        First-time setup: please enter your configuration.
        Enter your Lokalise project_id: 123456789abcdef.12345678
        Enter your Lokalise api_key: your_key_here
        Enter your OpenAI API key: sk-your_key_here
        Enter the path to the iOS project directory: /Users/me/ios
        Enter the path to the Android project directory: /Users/me/android

        ✔ Configuration saved to config/user_config.json.

    Example Subsequent Output:
        ✔ Configuration already exists at config/user_config.json.
    """
    config_dir = Path("config")
    config_file = config_dir / "user_config.json"
    config_dir.mkdir(exist_ok=True)

    if not config_file.exists():
        print("\nFirst-time setup: please enter your configuration.")
        config = {
            "lokalise": {
                "project_id": input("Enter your Lokalise project_id: ").strip(),
                "api_key": input("Enter your Lokalise api_key: ").strip()
            },
            "openai": {
                "api_key": input("Enter your OpenAI API key: ").strip()
            },
            "project_paths": {
                "ios": input("Enter the path to the iOS project directory: ").strip(),
                "android": input("Enter the path to the Android project directory: ").strip()
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"\n✔ Configuration saved to {config_file}.")
    else:
        print(f"✔ Configuration already exists at {config_file}.")

def main() -> None:
    """
    Main entry point for the Lokalise Translation Manager Tool.

    Orchestrates the complete startup workflow:
    1. Display welcome message
    2. Check standard libraries
    3. Install dependencies (requirements.txt or manual)
    4. Setup/validate configuration
    5. Launch core translation workflow

    Workflow:
        1. Print startup banner
        2. Show dependency installation tip
        3. Check standard library availability
        4. Try to install from requirements.txt
        5. Fall back to manual installation if needed
        6. Setup or validate user_config.json
        7. Import and run core translation workflow
        8. Handle any errors gracefully

    Exit Conditions:
        - Success: Core workflow completes normally
        - Error: Prints error message and exits

    Example Output:
        🧩 Starting Lokalise Translation Manager Tool...

        💡 Tip: You can run "pip install -r requirements.txt" manually to install dependencies.

        ✔ All dependencies installed from requirements.txt.
        ✔ Configuration already exists at config/user_config.json.

        [Core workflow launches with interactive menu...]

    Error Handling:
        Catches all exceptions from core workflow and displays user-friendly
        error message. Does not expose stack traces to end users.
    """
    print("\n🧩 Starting Lokalise Translation Manager Tool...\n")

    # Optional: show this tip
    print("💡 Tip: You can run \"pip install -r requirements.txt\" manually to install dependencies.\n")

    check_standard_libraries()
    used_requirements = install_from_requirements()
    if not used_requirements:
        check_and_install_optional_libraries()

    get_user_config()

    try:
        from lokalise_translation_manager.core import run_tool
        run_tool()
    except Exception as e:
        print(f"\n❌ Error during tool execution: {e}")

if __name__ == "__main__":
    main()
