# run.py - Entry point for Lokalise Translation Manager Tool (hybrid version with stdlib awareness)

import os
import subprocess
import sys
import json
from pathlib import Path

# 🔧 Aggiungi la root del progetto al sys.path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))


# Standard libraries (for user info)
standard_libraries = [
    'os', 're', 'csv', 'time', 'threading', 'subprocess',
    'json', 'configparser', 'itertools'
]

# Optional external libraries to install if not present
optional_libraries = [
    'prettytable',
    'colorama',
    'tqdm',
    'requests'
]

def install_package(package):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")

def install_from_requirements():
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("\nInstalling dependencies from requirements.txt...\n")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)])
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install from requirements.txt: {e}\nFalling back to manual installation.")
    else:
        print("requirements.txt not found. Falling back to manual installation.")
    return False

def check_standard_libraries():
    print("\nChecking standard Python libraries...")
    for lib in standard_libraries:
        try:
            __import__(lib)
            print(f"{lib} is available (standard library).")
        except ImportError:
            print(f"{lib} is missing. Please ensure your Python installation is complete.")

def check_and_install_optional_libraries():
    print("\nChecking and installing optional libraries...")
    for package in optional_libraries:
        try:
            __import__(package)
            print(f"{package} is already installed.")
        except ImportError:
            print(f"{package} is missing. Attempting to install...")
            install_package(package)

def get_user_config():
    """
    Prompt user for config (Lokalise + OpenAI) if not already provided
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
        print(f"Configuration saved to {config_file}.")
    else:
        print(f"Configuration already exists at {config_file}.")

def main():
    print("\nWelcome to Lokalise Translation Manager Tool 🚀\n")

    print("Tip: You can also manually run \"pip install -r requirements.txt\" to install all dependencies.\n")

    check_standard_libraries()
    used_requirements = install_from_requirements()
    if not used_requirements:
        check_and_install_optional_libraries()

    get_user_config()

    # Call the iOS and Android scanners as modules
    try:
        from lokalise_translation_manager.scanner.ios_scanner import main as run_ios_scanner
        from lokalise_translation_manager.scanner.android_scanner import main as run_android_scanner

        print("\n--- Running iOS Scanner ---\n")
        run_ios_scanner()

        print("\n--- Running Android Scanner ---\n")
        run_android_scanner()

    except ImportError as e:
        print(f"Error importing scanner modules: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during scanning: {e}")

if __name__ == "__main__":
    main()
