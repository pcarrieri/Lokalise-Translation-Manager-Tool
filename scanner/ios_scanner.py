import os
import re
import csv
import time
import threading
import configparser
import subprocess

# Check for colorama
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

# Check for prettytable
try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

# Define paths relative to the script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config_ios.ini')
FINAL_RESULT_CSV = os.path.join(SCRIPT_DIR, 'final_result.csv')
TOTAL_KEYS_CSV = os.path.join(SCRIPT_DIR, 'total_keys_used_ios.csv')
MISSING_TRANSLATIONS_DIR = os.path.join(SCRIPT_DIR, '..', 'missing_translations')

def print_colored(text, color):
    if color_enabled:
        print(color + text)
    else:
        print(text)

def spinner():
    while not stop_loading:
        for cursor in '|/-\\':
            print('\r' + cursor + ' Loading...', end='', flush=True)
            time.sleep(0.1)

def extract_localized_strings(directory):
    """
    Explore a directory and its subdirectories to find all .swift files,
    extract NSLocalizedString instances, and save results to final_result.csv.
    """
    localized_strings = set()
    file_analysis = {}
    pattern = re.compile(r'NSLocalizedString\("([^"]+)",\s*comment\s*:\s*"[^"]*"\)')

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.swift'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        localized_strings.update(matches)
                        file_analysis[relative_path] = len(matches)
                except Exception as e:
                    print_colored(f"Error reading {file_path}: {e}", Fore.RED)

    try:
        with open(FINAL_RESULT_CSV, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nResults have been written to final_result.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to CSV: {e}", Fore.RED)

    try:
        with open(TOTAL_KEYS_CSV, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for string in sorted(localized_strings):
                writer.writerow([string])
        print_colored("\nTotal keys have been written to total_keys_used_ios.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to total_keys_used_ios.csv: {e}", Fore.RED)

    try:
        with open(os.path.join(SCRIPT_DIR, 'swift_files.csv'), 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['File Path', 'Number of Keys'])
            for file_path, count in file_analysis.items():
                writer.writerow([file_path, count])
        print_colored("\nSwift file details have been written to swift_files.csv", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to swift_files.csv: {e}", Fore.RED)
    
    return len(localized_strings), file_analysis

def load_strings_file(file_path):
    """
    Load key-value pairs from a Localizable.strings file.
    """
    strings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
            for line in content:
                if '=' in line:
                    key_value = line.split('=')
                    key = key_value[0].strip().strip('"')
                    value = key_value[1].strip().strip(';').strip().strip('"')
                    strings[key] = value
    except Exception as e:
        print_colored(f"Error reading {file_path}: {e}", Fore.RED)
    return strings

def load_excluded_locales():
    """
    Load excluded locales from excluded_locales.ini.
    """
    excluded_locales = set()
    config_path = os.path.join(SCRIPT_DIR, 'excluded_locales.ini')
    config = configparser.ConfigParser()

    if os.path.exists(config_path):
        config.read(config_path)
        if 'EXCLUDED' in config and 'excluded_locales' in config['EXCLUDED']:
            # Split by comma and strip whitespace
            locales = config['EXCLUDED']['excluded_locales'].split(',')
            excluded_locales = {locale.strip() for locale in locales}

    # Debug print to verify excluded locales
    print_colored(f"Excluded locales: {excluded_locales}", Fore.YELLOW)
    return excluded_locales

def compare_translations(localizable_dir):
    """
    Compare translations and find missing keys in Localizable.strings.
    """
    print_colored("Comparing translations...", Fore.CYAN)

    excluded_locales = load_excluded_locales()
    missing_translations = {}
    en_path = os.path.join(localizable_dir, 'en.lproj', 'Localizable.strings')
    en_strings = load_strings_file(en_path)

    keys_to_check = []
    try:
        with open(FINAL_RESULT_CSV, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            keys_to_check = [row[0] for row in reader]
    except Exception as e:
        print_colored(f"Error reading {FINAL_RESULT_CSV}: {e}", Fore.RED)

    for language_dir in os.listdir(localizable_dir):
        if language_dir.endswith('.lproj'):
            lang_code = language_dir.replace('.lproj', '').split('-')[0]  # Simplify locale code
            if lang_code in excluded_locales:
                continue

            lang_path = os.path.join(localizable_dir, language_dir, 'Localizable.strings')
            lang_strings = load_strings_file(lang_path)

            for key in keys_to_check:
                if key in en_strings and (key not in lang_strings or not lang_strings[key].strip()):
                    if key not in missing_translations:
                        missing_translations[key] = []
                    missing_translations[key].append(lang_code)

    # Ensure the directory exists
    os.makedirs(MISSING_TRANSLATIONS_DIR, exist_ok=True)
    missing_translations_path = os.path.join(MISSING_TRANSLATIONS_DIR, 'missing_ios_translations.csv')

    try:
        with open(missing_translations_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for key, languages in missing_translations.items():
                if languages:
                    writer.writerow([key, ", ".join(languages)])
        print_colored(f"Results have been written to {missing_translations_path}", Fore.CYAN)
    except Exception as e:
        print_colored(f"Error writing to CSV: {e}", Fore.RED)

    return len(missing_translations)

def get_directory_from_config():
    """
    Retrieve the directory path from the configuration file.
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'Settings' in config and 'directory' in config['Settings']:
            return config['Settings']['directory']
    return None

def get_localizable_dir_from_config():
    """
    Retrieve the Localizable directory path from the configuration file.
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if 'Settings' in config and 'localizable_dir' in config['Settings']:
            return config['Settings']['localizable_dir']
    return None

def save_to_config(directory=None, localizable_dir=None):
    """
    Save the directory and Localizable directory path to the configuration file.
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    if directory:
        config['Settings'] = {'directory': directory}
    if localizable_dir:
        config['Settings']['localizable_dir'] = localizable_dir
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

def validate_localizable_dir(path):
    """
    Validate if the given path is a directory containing .lproj folders with Localizable.strings files.
    """
    if not os.path.isdir(path):
        return False

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if item.endswith('.lproj') and os.path.isdir(item_path):
            localizable_file = os.path.join(item_path, 'Localizable.strings')
            if os.path.isfile(localizable_file):
                return True
    return False

def run_additional_script():
    """
    Run the additional script located in the specified path.
    """
    additional_script_path = os.path.join(SCRIPT_DIR, '..', 'extract_from_localized_strings', 'extract_localized_strings_android_colored.py')
    try:
        subprocess.run(['python3', additional_script_path], check=True)
    except Exception as e:
        print_colored(f"Error running additional script: {e}", Fore.RED)

# Main execution
if __name__ == "__main__":
    if not color_enabled:
        print("Colorama is not installed. Running without graphical enhancements...")

    initial_directory = get_directory_from_config()
    if not initial_directory:
        initial_directory = input("Enter the path to the directory containing the .swift files: ").strip()
        save_to_config(directory=initial_directory)

    localizable_dir = get_localizable_dir_from_config()
    while not localizable_dir or not validate_localizable_dir(localizable_dir):
        localizable_dir = input("Enter the path to the directory containing .lproj folders with Localizable.strings files: ").strip()
        if validate_localizable_dir(localizable_dir):
            save_to_config(localizable_dir=localizable_dir)
        else:
            print_colored("Invalid path. Please enter a valid directory.", Fore.RED)

    start_time = time.time()

    # Start spinner
    stop_loading = False
    threading.Thread(target=spinner, daemon=True).start()

    total_keys, file_analysis = extract_localized_strings(initial_directory)
    missing_keys_count = compare_translations(localizable_dir)

    # Stop spinner
    stop_loading = True
    time.sleep(0.2)
    
    end_time = time.time()
    execution_time_ms = int((end_time - start_time) * 1000)

    # Calculate total swift files analyzed and those with at least one key
    total_swift_files = len(file_analysis)
    files_with_keys = sum(1 for count in file_analysis.values() if count > 0)

    # Print summary using PrettyTable if available
    if table_enabled:
        summary_table = PrettyTable()
        summary_table.field_names = ["Metric", "Value"]
        summary_table.add_row(["Total keys used by the project", total_keys])
        summary_table.add_row(["Keys with missing translations", missing_keys_count])
        summary_table.add_row(["Execution time (ms)", execution_time_ms])
        summary_table.add_row(["Total .swift files analyzed", total_swift_files])
        summary_table.add_row([".swift files with at least one key", files_with_keys])
        summary_output = summary_table.get_string()
    else:
        summary_output = (f"\n--- Summary ---\n"
                          f"Total keys used by the project: {total_keys}\n"
                          f"Keys with missing translations: {missing_keys_count}\n"
                          f"Execution time (ms): {execution_time_ms}\n"
                          f"Total .swift files analyzed: {total_swift_files}\n"
                          f".swift files with at least one key: {files_with_keys}")

    print_colored(summary_output, Fore.CYAN)

    # Run the additional script
    run_additional_script()