"""
CSV Utilities for Lokalise Translation Manager

This module provides robust CSV handling utilities with automatic delimiter detection.
It solves the common problem of CSV files using different delimiters (comma, semicolon,
tab, etc.) across different regions and tools.

PROBLEM SOLVED:
---------------
CSV (Comma-Separated Values) files don't always use commas. Different regions and
tools use different delimiters:
- English-speaking countries: Usually comma (',')
- European countries (e.g., Italy, Germany): Often semicolon (';')
- Tab-delimited files: Tab character ('\\t')
- Pipe-delimited files: Pipe character ('|')

This module automatically detects the delimiter so code doesn't need to hardcode it.

DETECTION STRATEGY:
-------------------
The module uses a two-stage detection approach:

Stage 1: Python's csv.Sniffer (intelligent detection)
    - Analyzes sample of file content
    - Uses statistical analysis to detect delimiter
    - Handles complex cases with quoted fields

Stage 2: Manual fallback (count-based detection)
    - Counts occurrences of common delimiters in first line
    - Returns the most common delimiter
    - More reliable for simple files

Stage 3: Final fallback
    - Returns comma (',') if all detection methods fail

SUPPORTED DELIMITERS:
---------------------
The module detects these common delimiters:
- Comma: ','
- Semicolon: ';'
- Tab: '\\t'
- Pipe: '|'

USAGE PATTERNS:
---------------
1. Simple delimiter detection:
    delimiter = detect_csv_delimiter('/path/to/file.csv')
    with open('/path/to/file.csv', 'r') as f:
        reader = csv.DictReader(f, delimiter=delimiter)

2. Open CSV with automatic detection:
    f, reader = open_csv_reader('/path/to/file.csv')
    for row in reader:
        print(row)
    f.close()

3. Read all rows at once:
    rows = read_csv_rows('/path/to/file.csv')
    for row in rows:
        print(row['column_name'])

BENEFITS:
---------
- No hardcoded delimiters in application code
- Works across different regional CSV formats
- Graceful fallback if detection fails
- Simple API for common CSV operations

USE CASES IN THIS PROJECT:
--------------------------
1. Reading translation CSV files from Lokalise
   - May use comma or semicolon depending on language
   - Automatic detection ensures compatibility

2. Reading scanner output CSV files
   - iOS/Android scanners generate CSV reports
   - User may open and save in different tools changing delimiter

3. Reading plugin-generated CSV files
   - Plugins may generate CSV with different delimiters
   - Core code doesn't need to know which delimiter was used

DEPENDENCIES:
-------------
- csv: Standard library CSV module
- pathlib: Standard library path handling

AUTHORS:
--------
Part of the Lokalise Translation Manager Tool
Enhanced with comprehensive documentation
"""

import csv
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union, IO

def detect_csv_delimiter(
    file_path: Union[str, Path],
    sample_size: int = 1024
) -> str:
    """
    Automatically detect the CSV delimiter by analyzing file content.

    Uses a multi-stage detection approach:
    1. Try Python's csv.Sniffer for intelligent detection
    2. Fallback to counting delimiter occurrences in first line
    3. Final fallback to comma (',')

    This function handles various edge cases:
    - Empty files (returns ',')
    - Files with quoted fields containing delimiters
    - Files too small for reliable detection
    - Encoding issues

    Args:
        file_path: Path to the CSV file (string or Path object)
        sample_size: Number of bytes to analyze for detection (default: 1024)
                    Larger samples are more accurate but slower

    Returns:
        str: Detected delimiter character (one of: ',', ';', '\\t', '|')
             Returns ',' if detection fails or file doesn't exist

    Detection Algorithm:
        Stage 1 - csv.Sniffer:
            - Reads first sample_size bytes of file
            - Uses statistical analysis to detect delimiter
            - Best for complex CSV with quoted fields

        Stage 2 - Manual counting:
            - Counts occurrences of common delimiters in first line
            - Returns most common delimiter
            - Best for simple CSV files

        Stage 3 - Final fallback:
            - Returns comma (',') if all else fails

    Error Handling:
        - File doesn't exist: Returns ','
        - File is empty: Returns ','
        - File is too small (<2 bytes): Returns ','
        - Encoding errors: Returns ','
        - Any exception during detection: Returns ','

    Example:
        # Detect delimiter and use it
        delimiter = detect_csv_delimiter('/path/to/file.csv')
        with open('/path/to/file.csv', 'r') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                print(row)

        # Works with Path objects
        from pathlib import Path
        csv_file = Path('/path/to/file.csv')
        delimiter = detect_csv_delimiter(csv_file)

        # Custom sample size for large files
        delimiter = detect_csv_delimiter('/path/to/huge.csv', sample_size=4096)

    Performance:
        - Fast: O(1) with default sample_size
        - Reads only first 1KB by default (configurable)
        - No need to load entire file into memory
    """
    # Convert string path to Path object if needed
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    # File doesn't exist → return default
    if not file_path.exists():
        return ','

    try:
        # Stage 1: Try csv.Sniffer (intelligent detection)
        with file_path.open('r', encoding='utf-8') as f:
            sample = f.read(sample_size)

            # If file is empty or too small, return default
            if not sample or len(sample) < 2:
                return ','

            # Use csv.Sniffer to detect delimiter
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            return delimiter

    except Exception:
        # Stage 2: Fallback to manual detection if Sniffer fails
        try:
            with file_path.open('r', encoding='utf-8') as f:
                first_line = f.readline().strip()

                # Count occurrences of common delimiters
                delimiters = [',', ';', '\t', '|']
                counts = {d: first_line.count(d) for d in delimiters}

                # Return the most common delimiter, or ',' if none found
                detected = max(counts, key=counts.get)
                return detected if counts[detected] > 0 else ','

        except Exception:
            # Stage 3: Final fallback
            return ','


def open_csv_reader(
    file_path: Union[str, Path],
    **kwargs: Any
) -> Tuple[IO, csv.DictReader]:
    """
    Open a CSV file with automatic delimiter detection.

    This is a convenience function that combines delimiter detection with
    file opening. It returns both the file object and the CSV reader, allowing
    the caller to close the file when done.

    Important: The caller is responsible for closing the returned file object.

    Args:
        file_path: Path to the CSV file (string or Path object)
        **kwargs: Additional arguments to pass to csv.DictReader
                 Common options:
                 - fieldnames: Specify custom column names
                 - restkey: Key for extra fields
                 - restval: Default value for missing fields

    Returns:
        Tuple[IO, csv.DictReader]: A tuple containing:
            - File object (must be closed by caller)
            - csv.DictReader object configured with detected delimiter

    Usage Pattern:
        # Open, use, and close
        f, reader = open_csv_reader('/path/to/file.csv')
        try:
            for row in reader:
                print(row)
        finally:
            f.close()

        # Better: Use context manager pattern
        f, reader = open_csv_reader('/path/to/file.csv')
        with f:
            for row in reader:
                print(row)

    Example:
        # Basic usage
        f, reader = open_csv_reader('/path/to/translations.csv')
        for row in reader:
            print(f"Key: {row['key']}, Value: {row['value']}")
        f.close()

        # With custom fieldnames
        f, reader = open_csv_reader(
            '/path/to/no-header.csv',
            fieldnames=['col1', 'col2', 'col3']
        )
        for row in reader:
            print(row['col1'])
        f.close()

    Why Return File Object:
        Returning the file object gives caller control over:
        - When to close the file
        - Exception handling during file operations
        - Resource cleanup timing

    Alternative:
        If you don't need fine-grained control, use read_csv_rows() instead
        which handles file closing automatically.
    """
    delimiter = detect_csv_delimiter(file_path)
    file_obj = open(file_path, 'r', encoding='utf-8')
    reader = csv.DictReader(file_obj, delimiter=delimiter, **kwargs)
    return file_obj, reader


def read_csv_rows(
    file_path: Union[str, Path],
    **kwargs: Any
) -> List[Dict[str, str]]:
    """
    Read all rows from a CSV file with automatic delimiter detection.

    This is the simplest way to read a CSV file. It automatically detects
    the delimiter, reads all rows, and closes the file. The entire CSV
    is loaded into memory as a list of dictionaries.

    Args:
        file_path: Path to the CSV file (string or Path object)
        **kwargs: Additional arguments to pass to csv.DictReader
                 Common options:
                 - fieldnames: Specify custom column names
                 - restkey: Key for extra fields
                 - restval: Default value for missing fields

    Returns:
        List[Dict[str, str]]: List of dictionaries where each dictionary
                             represents one row with column names as keys

    Memory Considerations:
        This function loads the entire CSV into memory. For very large files:
        - Consider using open_csv_reader() for streaming
        - Each row becomes a dictionary in memory
        - ~1MB CSV = ~1-2MB in memory (depends on structure)

    Error Handling:
        - File doesn't exist: Raises FileNotFoundError
        - Encoding errors: Raises UnicodeDecodeError
        - Malformed CSV: May raise csv.Error

    Example:
        # Basic usage
        rows = read_csv_rows('/path/to/translations.csv')
        print(f"Loaded {len(rows)} rows")
        for row in rows:
            print(f"Key: {row['key']}, Value: {row['value']}")

        # With custom fieldnames (for CSV without header)
        rows = read_csv_rows(
            '/path/to/no-header.csv',
            fieldnames=['id', 'name', 'value']
        )
        for row in rows:
            print(f"ID: {row['id']}, Name: {row['name']}")

        # Filter rows after loading
        rows = read_csv_rows('/path/to/translations.csv')
        italian_rows = [row for row in rows if row['language'] == 'it']
        print(f"Found {len(italian_rows)} Italian translations")

    Use Cases:
        - Load translation data for processing
        - Read scanner output files
        - Load plugin-generated reports
        - Read configuration from CSV

    When to Use:
        ✅ File size is reasonable (<100MB)
        ✅ Need to process all rows
        ✅ Need random access to rows
        ✅ Need to count/filter/sort rows

    When NOT to Use:
        ❌ Very large files (>100MB)
        ❌ Only need to process rows once sequentially
        ❌ Memory is constrained
        → Use open_csv_reader() for these cases
    """
    delimiter = detect_csv_delimiter(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter, **kwargs)
        return list(reader)
