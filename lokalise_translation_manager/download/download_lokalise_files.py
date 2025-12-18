"""
Lokalise Files Downloader Module

This module downloads translation files from Lokalise API for iOS and Android
platforms. It handles asynchronous download requests, polling, extraction, and
configuration management.

Workflow:
    1. Check if files already exist locally
    2. Prompt user for re-download (with timeout)
    3. Request async download from Lokalise API
    4. Poll process status until completion
    5. Download ZIP file when ready
    6. Extract files and cleanup
    7. Update config with lokalise_paths

Features:
    - Asynchronous download with polling
    - Cross-platform user prompt with timeout (Windows/Unix)
    - Automatic ZIP extraction
    - Configuration management
    - Progress spinner with status updates
    - Exponential backoff on slow responses
    - Colorama support for enhanced output

Platforms Supported:
    - iOS: Downloads .strings files
    - Android: Downloads .xml files

API Details:
    - Endpoint (Request): POST /api2/projects/{project_id}/files/async-download
    - Endpoint (Status): GET /api2/projects/{project_id}/processes/{process_id}
    - Authentication: X-Api-Token header
    - Response: Async process with download URL when ready

Download Process:
    1. POST request initiates async export
    2. Receive process_id
    3. Poll GET request every 5-7.5 seconds
    4. Monitor status: queued → processing → finished
    5. Extract download_url from finished process
    6. Download ZIP file with streaming
    7. Extract and delete ZIP

Input Files:
    - config/user_config.json: Lokalise API credentials

Output Files:
    - lokalise_translation_manager/lokalise_files/ios/*.strings
    - lokalise_translation_manager/lokalise_files/android/*.xml
    - config/user_config.json: Updated with lokalise_paths

Configuration Update:
    Adds lokalise_paths to user_config.json:
    {
        "lokalise": {...},
        "openai": {...},
        "project_paths": {...},
        "lokalise_paths": {
            "ios": "/absolute/path/to/lokalise_files/ios",
            "android": "/absolute/path/to/lokalise_files/android"
        }
    }

Usage:
    python3 -m lokalise_translation_manager.download.download_lokalise_files

    Or import:
        from lokalise_translation_manager.download.download_lokalise_files import main
        main()

Example Output:
    Files already exist. Do you want to re-download them? (y/n) [default: n] n
    No input received in 10 seconds. Defaulting to 'n'.
    Using existing local files.

    OR

    Fetching iOS... / Attempt 5 - Status: processing
    Fetching iOS... | Attempt 8 - Status: finished
    iOS file downloaded to lokalise_translation_manager/lokalise_files/ios/ios_strings.zip
    Extracting lokalise_files/ios/ios_strings.zip to lokalise_files/ios...
    Extraction complete. Deleted ios_strings.zip.
    All files downloaded and Lokalise paths added to config successfully.

Timeout Prompt:
    - Windows: Uses msvcrt for keyboard input
    - Unix/Linux/Mac: Uses select for stdin monitoring
    - Default timeout: 10 seconds
    - Default response: 'n' (no re-download)

Error Handling:
    - Missing config: Raises FileNotFoundError
    - API errors: Raises requests.HTTPError
    - Timeout: Raises TimeoutError after 30 attempts
    - Extraction errors: Propagates zipfile exceptions
"""

import os
import time
import json
import requests
import zipfile
import itertools
import sys
import threading
from pathlib import Path
from typing import Optional

if os.name == 'nt':
    import msvcrt
else:
    import select

try:
    from colorama import init, Fore
    init(autoreset=True)
    use_colors = True
except ImportError:
    use_colors = False

CONFIG_PATH = Path("config/user_config.json")


def download_file(download_url: str, save_path: Path) -> None:
    """
    Download a file from URL with streaming.

    Downloads the file in chunks to handle large files efficiently without
    loading the entire file into memory.

    Args:
        download_url: URL of the file to download
        save_path: Path where the file should be saved

    Raises:
        requests.HTTPError: If the download request fails

    Note:
        - Uses streaming to handle large files
        - Chunk size: 8192 bytes (8 KB)
        - Automatically raises for HTTP errors (4xx, 5xx)

    Example:
        download_file(
            "https://api.lokalise.com/download/123.zip",
            Path("output/file.zip")
        )
    """
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_zip(file_path: Path, extract_to: Path) -> None:
    """
    Extract ZIP file and delete the archive.

    Extracts all contents of a ZIP file to the specified directory and
    removes the ZIP file after successful extraction.

    Args:
        file_path: Path to the ZIP file to extract
        extract_to: Directory where contents should be extracted

    Raises:
        zipfile.BadZipFile: If the file is not a valid ZIP
        PermissionError: If unable to delete the ZIP file

    Note:
        - Extracts all files in the ZIP archive
        - Preserves directory structure
        - Automatically deletes ZIP after extraction
        - Prints colored status messages

    Example:
        extract_zip(
            Path("downloads/ios_strings.zip"),
            Path("lokalise_files/ios")
        )
        # Extracts all files and deletes the ZIP
    """
    print(f"{Fore.YELLOW if use_colors else ''}Extracting {file_path} to {extract_to}...")
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(file_path)
    print(f"{Fore.MAGENTA if use_colors else ''}Extraction complete. Deleted {file_path}.")

def prompt_with_timeout(prompt: str, timeout: int = 10, default: str = 'n') -> str:
    """
    Prompt user for input with automatic timeout.

    Cross-platform implementation that prompts the user for y/n input and
    automatically returns the default value if no input is received within
    the timeout period.

    Args:
        prompt: Question to display to the user
        timeout: Seconds to wait for input (default: 10)
        default: Default response if timeout occurs (default: 'n')

    Returns:
        str: User input (lowercase) or default value

    Platform Differences:
        Windows (os.name == 'nt'):
            - Uses msvcrt.kbhit() and msvcrt.getche()
            - Supports backspace for editing
            - Polls every 0.1 seconds

        Unix/Linux/Mac:
            - Uses select.select() on sys.stdin
            - Reads entire line at once
            - More efficient than Windows implementation

    Note:
        - Input is automatically converted to lowercase
        - Empty input returns default value
        - Displays countdown message on timeout
        - Flushes output for immediate display

    Example:
        response = prompt_with_timeout(
            "Do you want to continue?",
            timeout=10,
            default='n'
        )
        if response == 'y':
            print("Continuing...")
        # Output if timeout:
        # Do you want to continue? (y/n) [default: n]
        # No input received in 10 seconds. Defaulting to 'n'.
    """
    print(f"{prompt} (y/n) [default: {default}] ", end='', flush=True)
    start_time = time.time()

    if os.name == 'nt':  # Windows
        input_str = ''
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getche()
                if char in [b'\r', b'\n']:  # Enter
                    break
                elif char == b'\x08':  # Backspace
                    input_str = input_str[:-1]
                    print('\b \b', end='', flush=True)
                else:
                    input_str += char.decode()
            if (time.time() - start_time) > timeout:
                print(f"\nNo input received in {timeout} seconds. Defaulting to '{default}'.")
                return default
            time.sleep(0.1)
        print()  # new line after input
        return input_str.strip().lower() or default
    else:  # Unix-like
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            input_str = sys.stdin.readline().strip()
            return input_str.lower() or default
        else:
            print(f"\nNo input received in {timeout} seconds. Defaulting to '{default}'.")
            return default

def fetch_lokalise_file(project_id: str, api_key: str, platform: str,
                         format: str, save_dir: str) -> str:
    """
    Fetch and download translation files from Lokalise API.

    Initiates an asynchronous export request, polls the status until complete,
    downloads the resulting ZIP file, extracts it, and returns the directory path.

    Args:
        project_id: Lokalise project ID
        api_key: Lokalise API token
        platform: Platform name for display ("iOS" or "Android")
        format: File format to download ("strings" for iOS, "xml" for Android)
        save_dir: Directory where files should be saved

    Returns:
        str: Absolute path to the directory containing extracted files

    Raises:
        requests.HTTPError: If API request fails
        TimeoutError: If download doesn't complete after 30 attempts
        KeyError: If API response is missing expected fields

    API Workflow:
        1. POST /files/async-download → Receive process_id
        2. Poll GET /processes/{process_id} every 5-7.5 seconds
        3. Wait for status: queued → processing → finished
        4. Extract download_url from finished process
        5. Download ZIP file
        6. Extract and cleanup

    Polling Strategy:
        - Initial wait: 5 seconds
        - If status unchanged: wait *= 1.5 (exponential backoff)
        - If status changed: reset to 5 seconds
        - Max wait: ~7.5 seconds
        - Max attempts: 30
        - Total max time: ~3-5 minutes

    Progress Display:
        - Spinner animation: - / | \
        - Shows attempt number
        - Shows current status
        - Example: "Fetching iOS... / Attempt 5 - Status: processing"

    Example:
        ios_dir = fetch_lokalise_file(
            project_id="abc123.xyz",
            api_key="your_api_key",
            platform="iOS",
            format="strings",
            save_dir="lokalise_files/ios"
        )
        # Returns: "/absolute/path/to/lokalise_files/ios"
    """
    url = f"https://api.lokalise.com/api2/projects/{project_id}/files/async-download"
    payload = {"format": format, "all_platforms": True}
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Token": api_key
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    process_id = response.json().get("process_id")

    spinner = itertools.cycle(['-', '/', '|', '\\'])
    max_attempts = 30
    wait_seconds = 5.0  # starting wait 5 seconds
    old_status = ""

    for attempt in range(1, max_attempts + 1):
        status_url = f"https://api.lokalise.com/api2/projects/{project_id}/processes/{process_id}"
        response = requests.get(status_url, headers=headers)
        if response.status_code == 200:
            process_info = response.json().get("process", {})
            status = process_info.get("status")
            message = process_info.get("message", "No message")
            sys.stdout.write(f"\r{Fore.CYAN if use_colors else ''}Fetching {platform}... {next(spinner)} Attempt {attempt} - Status: {status}")
            sys.stdout.flush()
            if status == "finished":
                download_url = process_info.get("details", {}).get("download_url")
                if download_url:
                    Path(save_dir).mkdir(parents=True, exist_ok=True)
                    file_name = f"{platform}_strings.zip"
                    save_path = os.path.join(save_dir, file_name)
                    download_file(download_url, save_path)
                    print(f"\n{Fore.GREEN if use_colors else ''}{platform} file downloaded to {save_path}")
                    extract_zip(save_path, save_dir)
                    return os.path.abspath(save_dir)
        else:
            print(f"\n{Fore.RED if use_colors else ''}Attempt {attempt}: Unexpected status code {response.status_code}")

        if status == old_status:
            wait_seconds *= 1.5  # progressively increase the waiting time
        else:
            wait_seconds = 5.0
        old_status = status
        time.sleep(wait_seconds)

    raise TimeoutError(f"\n{Fore.RED if use_colors else ''}Failed to download {platform} file after {attempt} attempts.")

def main() -> None:
    """
    Main entry point for Lokalise files downloader.

    Orchestrates the complete download workflow:
    1. Load configuration from user_config.json
    2. Check if files already exist
    3. Prompt user for re-download (with timeout)
    4. Download iOS and Android files from Lokalise
    5. Update config with lokalise_paths

    Configuration Required:
        config/user_config.json must contain:
        - lokalise.project_id
        - lokalise.api_key

    Output Directories:
        - lokalise_translation_manager/lokalise_files/ios/
        - lokalise_translation_manager/lokalise_files/android/

    Configuration Update:
        Adds "lokalise_paths" section to config:
        {
            "lokalise_paths": {
                "ios": "/absolute/path/to/ios",
                "android": "/absolute/path/to/android"
            }
        }

    User Interaction:
        - If files exist: Prompts for re-download (10 second timeout)
        - Default: 'n' (keep existing files)
        - Response 'y': Re-downloads all files

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If config is missing required fields
        requests.HTTPError: If API requests fail
        TimeoutError: If download doesn't complete in time

    Example:
        main()
        # Output:
        # Files already exist. Do you want to re-download them? (y/n) [default: n] n
        # Using existing local files.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("user_config.json not found. Please run setup via run.py")

    with CONFIG_PATH.open(encoding='utf-8') as f:
        config = json.load(f)

    project_id = config["lokalise"]["project_id"]
    api_key = config["lokalise"]["api_key"]

    ios_path = Path("lokalise_translation_manager/lokalise_files/ios")
    android_path = Path("lokalise_translation_manager/lokalise_files/android")

    ios_exists = ios_path.exists() and any(ios_path.glob("*"))
    android_exists = android_path.exists() and any(android_path.glob("*"))

    if ios_exists or android_exists:
        response = prompt_with_timeout("Files already exist. Do you want to re-download them?", timeout=10, default='n')
        if response != 'y':
            print(f"{Fore.GREEN if use_colors else ''}Using existing local files.")
            config["lokalise_paths"] = {
                "ios": str(ios_path.resolve()),
                "android": str(android_path.resolve())
            }
            with CONFIG_PATH.open('w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return

    ios_dir = fetch_lokalise_file(project_id, api_key, "iOS", "strings", str(ios_path))
    android_dir = fetch_lokalise_file(project_id, api_key, "Android", "xml", str(android_path))

    config["lokalise_paths"] = {
        "ios": ios_dir,
        "android": android_dir
    }

    with CONFIG_PATH.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

    print(f"\n{Fore.GREEN if use_colors else ''}All files downloaded and Lokalise paths added to config successfully.")


if __name__ == "__main__":
    main()
