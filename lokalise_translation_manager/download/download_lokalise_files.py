# download_lokalise_files.py - Downloads and extracts Lokalise project files

import os
import time
import json
import requests
import zipfile
import itertools
import sys
import threading
from pathlib import Path

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


def download_file(download_url, save_path):
    response = requests.get(download_url, stream=True)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_zip(file_path, extract_to):
    print(f"{Fore.YELLOW if use_colors else ''}Extracting {file_path} to {extract_to}...")
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(file_path)
    print(f"{Fore.MAGENTA if use_colors else ''}Extraction complete. Deleted {file_path}.")

def prompt_with_timeout(prompt, timeout=10, default='n'):
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

def fetch_lokalise_file(project_id, api_key, platform, format, save_dir):
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

def main():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("user_config.json not found. Please run setup via run.py")

    with CONFIG_PATH.open() as f:
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
            with CONFIG_PATH.open('w') as f:
                json.dump(config, f, indent=4)
            return

    ios_dir = fetch_lokalise_file(project_id, api_key, "iOS", "strings", str(ios_path))
    android_dir = fetch_lokalise_file(project_id, api_key, "Android", "xml", str(android_path))

    config["lokalise_paths"] = {
        "ios": ios_dir,
        "android": android_dir
    }

    with CONFIG_PATH.open('w') as f:
        json.dump(config, f, indent=4)

    print(f"\n{Fore.GREEN if use_colors else ''}All files downloaded and Lokalise paths added to config successfully.")


if __name__ == "__main__":
    main()
