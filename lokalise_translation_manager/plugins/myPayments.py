# lokalise_translation_manager/plugins/myPayments.py

# [EXTENSION]
import os
import csv
import re
import sys
import threading
from pathlib import Path
from colorama import init, Fore, Style

init(autoreset=True)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports"
TRANSLATION_DONE_FILE = REPORTS_DIR / "translation_done.csv"
SOFTPOS_TRANSLATIONS_FILE = REPORTS_DIR / "softpos_translations.csv"
URL_TRANSLATIONS_FILE = REPORTS_DIR / "url_translations.csv"

def print_colored(text, color=None):
    print(color + text + Style.RESET_ALL if color else text)

def filter_translations():
    softpos_count = 0
    url_count = 0
    softpos_rows = []
    url_rows = []

    try:
        with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            with SOFTPOS_TRANSLATIONS_FILE.open('w', newline='', encoding='utf-8') as softpos_file, \
                 URL_TRANSLATIONS_FILE.open('w', newline='', encoding='utf-8') as url_file:

                softpos_writer = csv.DictWriter(softpos_file, fieldnames=fieldnames)
                url_writer = csv.DictWriter(url_file, fieldnames=fieldnames)

                softpos_writer.writeheader()
                url_writer.writeheader()

                for row in reader:
                    translation_texts = [row.get('translated', ''), row.get('translation', '')]

                    if any(re.search(r'soft[-]?pos', text, re.IGNORECASE) for text in translation_texts):
                        softpos_writer.writerow(row)
                        softpos_rows.append(row)
                        softpos_count += 1

                    if any(re.search(r'http[s]?://', text) for text in translation_texts):
                        url_writer.writerow(row)
                        url_rows.append(row)
                        url_count += 1

        print_colored("\nSummary of myPayments Plugin:", Fore.CYAN)
        print_colored(f"Keys with 'softpos' or 'soft-pos': {softpos_count}", Fore.YELLOW)
        print_colored(f"Keys with URLs: {url_count}", Fore.YELLOW)

        proceed_with_deletion(softpos_rows, url_rows)

    except Exception as e:
        print_colored(f"ERROR: Failed to process translations - {e}", Fore.RED)

def proceed_with_deletion(softpos_rows, url_rows):
    print("IMPORTANT: Press ENTER key within 10 seconds to KEEP the filtered keys in the original file...")
    print("If no key is pressed, the keys will be DELETED automatically.")

    try:
        if os.name == 'nt':  # Windows
            import msvcrt
            start_time = time.time()
            while time.time() - start_time < 10:
                if msvcrt.kbhit():
                    msvcrt.getch()
                    print_colored("Input received. No changes made to the original file.", Fore.GREEN)
                    return
                time.sleep(0.1)
        else:  # Unix / macOS
            import select
            print("Press ENTER to cancel deletion...", end='', flush=True)
            rlist, _, _ = select.select([sys.stdin], [], [], 10)
            if rlist:
                sys.stdin.readline()
                print_colored("\nInput received. No changes made to the original file.", Fore.GREEN)
                return
    except Exception as e:
        print_colored(f"Error while waiting for input: {e}", Fore.RED)

    print_colored("\nNo input received. Proceeding to delete the keys.\n", Fore.RED)
    delete_keys(softpos_rows, url_rows)


def delete_keys(softpos_rows, url_rows):
    try:
        with TRANSLATION_DONE_FILE.open('r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            rows = list(reader)

        rows_to_delete = softpos_rows + url_rows
        remaining_rows = [row for row in rows if row not in rows_to_delete]

        with TRANSLATION_DONE_FILE.open('w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(remaining_rows)

        print_colored(f"Deleted {len(rows_to_delete)} keys from the original file.", Fore.RED)
        print_colored("The filtered keys were saved in the following files:", Fore.CYAN)
        print_colored(f"- SoftPOS related keys: {SOFTPOS_TRANSLATIONS_FILE}", Fore.YELLOW)
        print_colored(f"- URL related keys: {URL_TRANSLATIONS_FILE}", Fore.YELLOW)
        print_colored("You can review and manage them manually. These keys will not be uploaded to Lokalise.", Fore.GREEN)

    except Exception as e:
        print_colored(f"ERROR: Failed to delete keys - {e}", Fore.RED)

def main():
    filter_translations()

if __name__ == "__main__":
    main()