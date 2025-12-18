#!/usr/bin/env python3
"""
Example usage of CSV utilities for automatic delimiter detection

This module demonstrates how to use the new csv_utils functionality
for robust CSV handling with automatic delimiter detection.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lokalise_translation_manager.utils.csv_utils import (
    detect_csv_delimiter,
    open_csv_reader,
    read_csv_rows
)


def example_1_detect_delimiter():
    """Example 1: Detect delimiter from a CSV file"""
    print("=" * 60)
    print("Example 1: Detecting CSV Delimiter")
    print("=" * 60)

    csv_file = BASE_DIR / "reports" / "translation_done.csv"

    if csv_file.exists():
        delimiter = detect_csv_delimiter(csv_file)
        print(f"File: {csv_file.name}")
        print(f"Detected delimiter: '{delimiter}'")
        print()
    else:
        print(f"File not found: {csv_file}")
        print("Run the tool first to generate reports.\n")


def example_2_read_with_detection():
    """Example 2: Read CSV with automatic delimiter detection"""
    print("=" * 60)
    print("Example 2: Reading CSV with Auto-Detection")
    print("=" * 60)

    csv_file = BASE_DIR / "reports" / "lokalise_keys.csv"

    if csv_file.exists():
        rows = read_csv_rows(csv_file)
        print(f"File: {csv_file.name}")
        print(f"Total rows: {len(rows)}")
        if rows:
            print(f"Columns: {list(rows[0].keys())}")
            print(f"First row: {rows[0]}")
        print()
    else:
        print(f"File not found: {csv_file}")
        print("Run the tool first to generate reports.\n")


def example_3_manual_reading():
    """Example 3: Manual CSV reading with delimiter detection"""
    print("=" * 60)
    print("Example 3: Manual Reading with Custom Processing")
    print("=" * 60)

    csv_file = BASE_DIR / "reports" / "en_translations.csv"

    if csv_file.exists():
        f, reader = open_csv_reader(csv_file)

        print(f"File: {csv_file.name}")
        print("Reading first 5 rows:\n")

        for i, row in enumerate(reader):
            if i >= 5:
                break
            print(f"Row {i+1}: {row}")

        f.close()
        print()
    else:
        print(f"File not found: {csv_file}")
        print("Run the tool first to generate reports.\n")


def example_4_handle_different_delimiters():
    """Example 4: Create and detect different delimiter formats"""
    print("=" * 60)
    print("Example 4: Testing Different Delimiters")
    print("=" * 60)

    # Create test files with different delimiters
    test_dir = Path("/tmp")

    test_files = {
        "test_comma.csv": "name,age,city\nJohn,30,NYC\nJane,25,LA",
        "test_semicolon.csv": "name;age;city\nJohn;30;NYC\nJane;25;LA",
        "test_tab.csv": "name\tage\tcity\nJohn\t30\tNYC\nJane\t25\tLA",
        "test_pipe.csv": "name|age|city\nJohn|30|NYC\nJane|25|LA"
    }

    for filename, content in test_files.items():
        filepath = test_dir / filename
        filepath.write_text(content)

        delimiter = detect_csv_delimiter(filepath)
        delimiter_name = {
            ',': 'comma',
            ';': 'semicolon',
            '\t': 'tab',
            '|': 'pipe'
        }.get(delimiter, 'unknown')

        print(f"{filename:25} → delimiter: '{delimiter}' ({delimiter_name})")

        # Clean up
        filepath.unlink()

    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("CSV UTILS - USAGE EXAMPLES")
    print("=" * 60 + "\n")

    example_1_detect_delimiter()
    example_2_read_with_detection()
    example_3_manual_reading()
    example_4_handle_different_delimiters()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
