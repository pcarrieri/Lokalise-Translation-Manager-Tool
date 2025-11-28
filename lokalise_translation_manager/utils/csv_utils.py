# lokalise_translation_manager/utils/csv_utils.py
# Utility functions for robust CSV handling

import csv
from pathlib import Path

def detect_csv_delimiter(file_path, sample_size=1024):
    """
    Automatically detect the CSV delimiter by analyzing the first few lines.

    Args:
        file_path: Path to the CSV file
        sample_size: Number of bytes to sample (default: 1024)

    Returns:
        str: Detected delimiter (default: ',')

    Example:
        delimiter = detect_csv_delimiter('/path/to/file.csv')
        with open('/path/to/file.csv', 'r') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
    """
    if not isinstance(file_path, Path):
        file_path = Path(file_path)

    if not file_path.exists():
        return ','  # Default fallback

    try:
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
        # Fallback to manual detection if Sniffer fails
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
            return ','  # Final fallback


def open_csv_reader(file_path, **kwargs):
    """
    Open a CSV file with automatic delimiter detection.

    Args:
        file_path: Path to the CSV file
        **kwargs: Additional arguments to pass to csv.DictReader

    Returns:
        tuple: (file_object, csv.DictReader)

    Example:
        f, reader = open_csv_reader('/path/to/file.csv')
        for row in reader:
            print(row)
        f.close()
    """
    delimiter = detect_csv_delimiter(file_path)
    file_obj = open(file_path, 'r', encoding='utf-8')
    reader = csv.DictReader(file_obj, delimiter=delimiter, **kwargs)
    return file_obj, reader


def read_csv_rows(file_path, **kwargs):
    """
    Read all rows from a CSV file with automatic delimiter detection.

    Args:
        file_path: Path to the CSV file
        **kwargs: Additional arguments to pass to csv.DictReader

    Returns:
        list: List of dictionaries (rows)

    Example:
        rows = read_csv_rows('/path/to/file.csv')
        for row in rows:
            print(row['column_name'])
    """
    delimiter = detect_csv_delimiter(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=delimiter, **kwargs)
        return list(reader)
