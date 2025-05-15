# run.py - Entry point for Lokalise Translation Manager Tool (refined logging)

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

def install_package(package):
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        print(f"✔ Installed missing library: {package}")
    except subprocess.CalledProcessError:
        print(f"✘ Failed to install: {package}")

def install_from_requirements():
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

def check_standard_libraries():
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

def check_and_install_optional_libraries():
    installed_something = False
    for package in optional_libraries:
        try:
            __import__(package)
        except ImportError:
            install_package(package)
            installed_something = True
    if not installed_something:
        print("✔ All optional libraries are already installed.")

def get_user_config():
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

def main():
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
