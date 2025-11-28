import os
import csv
import json
import requests
from pathlib import Path
from .csv_utils import detect_csv_delimiter

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    color_enabled = True
except ImportError:
    color_enabled = False

try:
    from prettytable import PrettyTable
    table_enabled = True
except ImportError:
    table_enabled = False

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_FILE = BASE_DIR / "config" / "user_config.json"

IOS_KEYS_FILE = REPORTS_DIR / "ios" / "total_keys_used_ios.csv"
ANDROID_KEYS_FILE = REPORTS_DIR / "android" / "total_keys_used_android.csv"
LOKALISE_KEYS_FILE = REPORTS_DIR / "lokalise_keys.csv"
TOTAL_KEYS_FILE = REPORTS_DIR / "total_keys_used_by_both.csv"
READY_TO_BE_DELETED_FILE = REPORTS_DIR / "ready_to_be_deleted.csv"

def print_colored(text, color=None):
    if color_enabled and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_keys(file_path):
    keys = set()
    if file_path.exists():
        delimiter = detect_csv_delimiter(file_path)
        with file_path.open('r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=delimiter)
            for row in reader:
                keys.add(row[0].strip())
    return keys

def merge_keys():
    ios_keys = load_keys(IOS_KEYS_FILE)
    android_keys = load_keys(ANDROID_KEYS_FILE)

    if not ios_keys and not android_keys:
        print_colored("ERROR: No keys found in either iOS or Android report.", Fore.RED)
        return False

    total_keys = ios_keys.union(android_keys)

    with TOTAL_KEYS_FILE.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for key in sorted(total_keys):
            writer.writerow([key])

    print_colored(f"Merged total keys saved to: {TOTAL_KEYS_FILE}", Fore.CYAN)
    return True

def filter_lokalise_keys():
    total_keys = load_keys(TOTAL_KEYS_FILE)
    lokalise_keys = {}

    delimiter = detect_csv_delimiter(LOKALISE_KEYS_FILE)
    with LOKALISE_KEYS_FILE.open('r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=delimiter)
        for row in reader:
            lokalise_keys[row['key_name']] = row['key_id']

    unused_keys = [
        (key_id, key_name)
        for key_name, key_id in lokalise_keys.items()
        if key_name not in total_keys
    ]

    with READY_TO_BE_DELETED_FILE.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['key_id', 'key_name'])
        for key_id, key_name in unused_keys:
            writer.writerow([key_id, key_name])

    print_colored(f"{len(unused_keys)} unused keys saved to: {READY_TO_BE_DELETED_FILE}", Fore.YELLOW)
    return unused_keys

def delete_keys_from_lokalise(keys_to_delete):
    with CONFIG_FILE.open() as f:
        config = json.load(f)

    project_id = config.get("lokalise", {}).get("project_id")
    api_key = config.get("lokalise", {}).get("api_key")

    if not project_id or not api_key:
        print_colored("ERROR: Missing Lokalise credentials in user_config.json", Fore.RED)
        return

    url = f"https://api.lokalise.com/api2/projects/{project_id}/keys"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Token": api_key
    }
    payload = {"keys": [key_id for key_id, _ in keys_to_delete]}

    response = requests.delete(url, json=payload, headers=headers)

    if response.status_code == 200:
        print_colored("✅ Keys successfully deleted from Lokalise.", Fore.GREEN)
    else:
        print_colored(f"ERROR: Failed to delete keys. Status code: {response.status_code}", Fore.RED)
        print_colored(response.text, Fore.RED)

def main():
    print_colored("\n📦 CLEANUP UNUSED LOKALISE KEYS\n", Fore.MAGENTA)

    if not merge_keys():
        return

    keys_to_delete = filter_lokalise_keys()

    if not keys_to_delete:
        print_colored("🎉 No unused keys found. Your Lokalise project is clean!", Fore.GREEN)
        return

    print_colored(f"\nFound {len(keys_to_delete)} keys that are NOT used in your iOS/Android projects.", Fore.YELLOW)

    if table_enabled:
        table = PrettyTable()
        table.field_names = ["Key ID", "Key Name"]
        for key_id, key_name in keys_to_delete:
            table.add_row([key_id, key_name])
        print(table)
    else:
        for key_id, key_name in keys_to_delete:
            print(f"Key ID: {key_id} | Key Name: {key_name}")

    print_colored("\n⚠️ WARNING: These keys will be permanently removed from your Lokalise project.", Fore.RED)
    print_colored("⚠️ This action is NOT reversible from this tool. Manual recovery from Lokalise UI may be required.\n", Fore.RED)

    user_input = input("👉 Do you want to proceed with deleting these unused keys from Lokalise? (y/n): ").strip().lower()

    if user_input == 'y':
        delete_keys_from_lokalise(keys_to_delete)
    else:
        print_colored("❌ Deletion aborted by user. No keys were deleted.", Fore.YELLOW)

    print_colored(f"\n📝 A list of deletable keys is saved in: {READY_TO_BE_DELETED_FILE}", Fore.CYAN)

if __name__ == "__main__":
    main()
