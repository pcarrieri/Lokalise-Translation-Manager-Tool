"""
Unused Keys Cleanup Module for Lokalise Translation Manager

This module identifies and optionally deletes translation keys from Lokalise that
are no longer used in the iOS and Android projects. It helps maintain a clean
Lokalise project by removing orphaned translation keys.

Workflow:
    1. Merge iOS and Android used keys into a single list
    2. Download all keys from Lokalise
    3. Compare and identify keys in Lokalise but not in code
    4. Display unused keys with interactive prompt
    5. Optionally delete unused keys from Lokalise via API

Safety Features:
    - Shows detailed list of keys to be deleted
    - Requires explicit user confirmation (y/n)
    - Warning messages about irreversibility
    - Generates CSV report of unused keys
    - PrettyTable display when available

Input Files:
    - reports/ios/total_keys_used_ios.csv: Keys used in iOS project
    - reports/android/total_keys_used_android.csv: Keys used in Android project
    - reports/lokalise_keys.csv: All keys currently in Lokalise
    - config/user_config.json: Lokalise API credentials

Output Files:
    - reports/total_keys_used_by_both.csv: Merged list of used keys
    - reports/ready_to_be_deleted.csv: List of unused keys with IDs

Usage:
    python3 -m lokalise_translation_manager.utils.cleanup_unused_keys

    Or import:
        from lokalise_translation_manager.utils.cleanup_unused_keys import main
        main()

Example Output:
    📦 CLEANUP UNUSED LOKALISE KEYS

    Merged total keys saved to: reports/total_keys_used_by_both.csv
    245 unused keys saved to: reports/ready_to_be_deleted.csv

    Found 245 keys that are NOT used in your iOS/Android projects.

    | Key ID    | Key Name                    |
    |-----------|-----------------------------|
    | 123456    | old_unused_key              |
    | 789012    | deprecated_label            |
    ...

    ⚠️ WARNING: These keys will be permanently removed from your Lokalise project.
    ⚠️ This action is NOT reversible from this tool.

    👉 Do you want to proceed with deleting these unused keys from Lokalise? (y/n): n

    ❌ Deletion aborted by user. No keys were deleted.

API Endpoint:
    DELETE https://api.lokalise.com/api2/projects/{project_id}/keys
    Headers: X-Api-Token: {api_key}
    Payload: {"keys": [key_id1, key_id2, ...]}

Security Notes:
    - Requires valid Lokalise API token
    - Deletion is permanent and cannot be undone from this tool
    - Manual recovery may be possible from Lokalise web UI
    - Always review the list carefully before confirming
"""

import os
import csv
import json
import requests
from pathlib import Path
from typing import Set, List, Tuple
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

def print_colored(text: str, color=None) -> None:
    """
    Print colored text to console with colorama fallback.

    Args:
        text: Text to print
        color: Colorama color code (Fore.RED, Fore.GREEN, etc.)

    Note:
        If colorama is not available, prints plain text without colors.
    """
    if color_enabled and color:
        print(color + text + Style.RESET_ALL)
    else:
        print(text)

def load_keys(file_path: Path) -> Set[str]:
    """
    Load translation keys from a CSV file.

    Args:
        file_path: Path to the CSV file containing keys

    Returns:
        Set[str]: Set of unique key names (first column of CSV)

    Note:
        - Uses automatic CSV delimiter detection
        - Returns empty set if file doesn't exist
        - Keys are stripped of whitespace
    """
    keys = set()
    if file_path.exists():
        delimiter = detect_csv_delimiter(file_path)
        with file_path.open('r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=delimiter)
            for row in reader:
                keys.add(row[0].strip())
    return keys

def merge_keys() -> bool:
    """
    Merge iOS and Android keys into a single unified list.

    Loads keys from both platform scanners and creates a union of all keys
    actually used in the codebase. This merged list is then compared against
    Lokalise to identify unused keys.

    Returns:
        bool: True if merge successful, False if no keys found

    Output:
        Creates reports/total_keys_used_by_both.csv with sorted unique keys

    Example:
        If iOS has: ["key1", "key2", "common"]
        And Android has: ["key3", "common"]
        Result: ["common", "key1", "key2", "key3"] (sorted)
    """
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

def filter_lokalise_keys() -> List[Tuple[str, str]]:
    """
    Identify keys in Lokalise that are not used in the codebase.

    Compares all keys in Lokalise against the merged list of keys actually
    used in iOS/Android code. Keys present in Lokalise but not in code are
    considered unused and candidates for deletion.

    Returns:
        List[Tuple[str, str]]: List of (key_id, key_name) tuples for unused keys

    Output:
        Creates reports/ready_to_be_deleted.csv with:
        - key_id: Lokalise key ID (for API deletion)
        - key_name: Human-readable key name

    Algorithm:
        1. Load all keys used in code (from merged file)
        2. Load all keys from Lokalise with their IDs
        3. Find keys in Lokalise not in code: unused = lokalise - code
        4. Return list of (ID, name) tuples

    Example:
        Code uses: ["key1", "key2"]
        Lokalise has: ["key1", "key2", "old_key", "unused_key"]
        Result: [("123", "old_key"), ("456", "unused_key")]
    """
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

def delete_keys_from_lokalise(keys_to_delete: List[Tuple[str, str]]) -> None:
    """
    Delete unused keys from Lokalise via API.

    Makes a DELETE request to the Lokalise API to permanently remove the
    specified keys from the project. This operation cannot be undone from
    this tool.

    Args:
        keys_to_delete: List of (key_id, key_name) tuples to delete

    API Endpoint:
        DELETE https://api.lokalise.com/api2/projects/{project_id}/keys

    Request:
        Headers: X-Api-Token: {api_key}
        Body: {"keys": [key_id1, key_id2, ...]}

    Response:
        200: Success - keys deleted
        4xx/5xx: Error - keys not deleted

    Raises:
        requests.RequestException: If API request fails

    Security:
        - Requires valid Lokalise API token
        - Requires project_id in config
        - Deletion is permanent
        - Manual recovery may be possible from Lokalise web UI

    Example:
        keys_to_delete = [("123456", "old_key"), ("789012", "unused_key")]
        delete_keys_from_lokalise(keys_to_delete)
        # Output: ✅ Keys successfully deleted from Lokalise.
    """
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

def main() -> None:
    """
    Main function to orchestrate the cleanup process.

    Workflow:
        1. Merge iOS and Android used keys
        2. Identify unused keys in Lokalise
        3. Display unused keys to user
        4. Prompt for confirmation
        5. Delete keys if confirmed

    User Interaction:
        - Shows total count of unused keys
        - Displays table of keys (PrettyTable if available)
        - Shows warning about irreversibility
        - Requires explicit 'y' confirmation
        - Saves CSV report regardless of deletion

    Exit Conditions:
        - No keys in iOS/Android reports: Exits with error
        - No unused keys found: Exits with success message
        - User declines deletion: Exits without deleting

    Output Files:
        - reports/total_keys_used_by_both.csv: Always created
        - reports/ready_to_be_deleted.csv: Always created
    """
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
