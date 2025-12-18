"""
Language Configuration Loader Module

This module provides centralized access to supported language configurations
for the Lokalise Translation Manager Tool. It loads language definitions from
config/supported_languages.json and provides utility functions to access
language names and Lokalise code mappings.

Features:
    - Load language configuration from JSON file
    - Get language names for OpenAI prompts
    - Get Lokalise code mappings for normalization
    - Fallback to default configuration if file not found
    - Cache configuration for performance

Configuration File:
    Location: config/supported_languages.json
    Format:
        {
            "languages": {
                "en": {
                    "name": "English",
                    "lokalise_code": "en"
                },
                "de": {
                    "name": "German",
                    "lokalise_code": "de"
                },
                ...
            }
        }

Usage:
    from lokalise_translation_manager.utils.language_config import (
        get_language_names,
        get_lokalise_mappings,
        get_supported_languages
    )

    # Get language code to name mapping (for OpenAI prompts)
    names = get_language_names()
    # Returns: {"en": "English", "de": "German", "lt_LT": "Lithuanian", ...}

    # Get short code to Lokalise code mapping (for normalization)
    mappings = get_lokalise_mappings()
    # Returns: {"en": "en", "de": "de", "lt": "lt_LT", ...}

    # Get list of supported language codes
    langs = get_supported_languages()
    # Returns: ["en", "de", "fr", ...]
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from colorama import Fore
    color_enabled = True
except ImportError:
    color_enabled = False
    class Fore:
        CYAN = ''
        YELLOW = ''
        RED = ''

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "supported_languages.json"

# Cache for loaded configuration
_config_cache: Optional[Dict] = None

# Default configuration (fallback if file not found)
DEFAULT_LANGUAGES = {
    "en": {"name": "English", "lokalise_code": "en"},
    "de": {"name": "German", "lokalise_code": "de"},
    "fr": {"name": "French", "lokalise_code": "fr"},
    "it": {"name": "Italian", "lokalise_code": "it"},
    "pl": {"name": "Polish", "lokalise_code": "pl"},
    "sv": {"name": "Swedish", "lokalise_code": "sv"},
    "nb": {"name": "Norwegian (Bokmal)", "lokalise_code": "nb"},
    "da": {"name": "Danish", "lokalise_code": "da"},
    "fi": {"name": "Finnish", "lokalise_code": "fi"},
    "lt": {"name": "Lithuanian", "lokalise_code": "lt_LT"},
    "lv": {"name": "Latvian", "lokalise_code": "lv_LV"},
    "et": {"name": "Estonian", "lokalise_code": "et_EE"},
    "tr": {"name": "Turkish", "lokalise_code": "tr_TR"},
    "ar": {"name": "Arabic", "lokalise_code": "ar"},
    "el": {"name": "Greek", "lokalise_code": "el"}
}


def print_colored(text: str, color: str) -> None:
    """Print colored text with colorama fallback."""
    print(color + text if color_enabled else text)


def load_language_config(force_reload: bool = False) -> Dict:
    """
    Load language configuration from JSON file.

    Loads the supported languages configuration from config/supported_languages.json.
    Uses caching to avoid repeated file reads. Falls back to default configuration
    if the file doesn't exist or is malformed.

    Args:
        force_reload: If True, bypass cache and reload from file

    Returns:
        Dict: Language configuration dictionary with structure:
              {"languages": {"code": {"name": "...", "lokalise_code": "..."}, ...}}

    Note:
        - Creates default config if file doesn't exist
        - Returns cached config on subsequent calls
        - Falls back to defaults on parse errors
    """
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    if not CONFIG_FILE.exists():
        print_colored(
            f"Language config not found at {CONFIG_FILE}. Using defaults.",
            Fore.YELLOW
        )
        _config_cache = {"languages": DEFAULT_LANGUAGES}
        return _config_cache

    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = json.load(f)
            _config_cache = config
            return config
    except Exception as e:
        print_colored(
            f"Error loading language config: {e}. Using defaults.",
            Fore.RED
        )
        _config_cache = {"languages": DEFAULT_LANGUAGES}
        return _config_cache


def get_language_names() -> Dict[str, str]:
    """
    Get mapping of language codes to human-readable names.

    Returns a dictionary mapping both short codes and Lokalise codes to
    language names. This is used by the translation engine to provide
    clear language context in OpenAI prompts.

    Returns:
        Dict[str, str]: Mapping of language codes to names
                       e.g., {"en": "English", "de": "German", "lt_LT": "Lithuanian"}

    Note:
        - Includes both short codes (e.g., "lt") and Lokalise codes (e.g., "lt_LT")
        - This allows looking up names using either code format

    Example:
        names = get_language_names()
        print(names.get("de"))      # "German"
        print(names.get("lt_LT"))   # "Lithuanian"
    """
    config = load_language_config()
    languages = config.get("languages", DEFAULT_LANGUAGES)

    names = {}
    for code, data in languages.items():
        name = data.get("name", code)
        lokalise_code = data.get("lokalise_code", code)

        # Map short code to name
        names[code] = name

        # Also map Lokalise code to name (for codes like lt_LT)
        if lokalise_code != code:
            names[lokalise_code] = name

    return names


def get_lokalise_mappings() -> Dict[str, str]:
    """
    Get mapping of short language codes to Lokalise codes.

    Returns a dictionary mapping language short codes to their corresponding
    Lokalise API codes. This is used during normalization to convert codes
    like "lt" to "lt_LT".

    Returns:
        Dict[str, str]: Mapping of short codes to Lokalise codes
                       e.g., {"en": "en", "lt": "lt_LT", "tr": "tr_TR"}

    Example:
        mappings = get_lokalise_mappings()
        print(mappings.get("lt"))   # "lt_LT"
        print(mappings.get("de"))   # "de"
    """
    config = load_language_config()
    languages = config.get("languages", DEFAULT_LANGUAGES)

    mappings = {}
    for code, data in languages.items():
        lokalise_code = data.get("lokalise_code", code)
        mappings[code] = lokalise_code

    return mappings


def get_supported_languages() -> List[str]:
    """
    Get list of supported language codes.

    Returns a list of all configured language short codes that the tool
    can translate to.

    Returns:
        List[str]: List of language codes, e.g., ["en", "de", "fr", ...]

    Example:
        langs = get_supported_languages()
        if "de" in langs:
            print("German is supported")
    """
    config = load_language_config()
    languages = config.get("languages", DEFAULT_LANGUAGES)
    return list(languages.keys())


def get_language_name(code: str) -> str:
    """
    Get the human-readable name for a language code.

    Args:
        code: Language code (short or Lokalise format)

    Returns:
        str: Human-readable language name, or the code itself if not found

    Example:
        print(get_language_name("de"))      # "German"
        print(get_language_name("lt_LT"))   # "Lithuanian"
        print(get_language_name("xx"))      # "xx" (unknown code)
    """
    names = get_language_names()
    return names.get(code, code)


def get_lokalise_code(short_code: str) -> str:
    """
    Get the Lokalise API code for a short language code.

    Args:
        short_code: Short language code (e.g., "lt", "tr")

    Returns:
        str: Lokalise code (e.g., "lt_LT", "tr_TR"), or original code if no mapping

    Example:
        print(get_lokalise_code("lt"))   # "lt_LT"
        print(get_lokalise_code("de"))   # "de"
    """
    mappings = get_lokalise_mappings()
    return mappings.get(short_code, short_code)


def reload_config() -> None:
    """
    Force reload of language configuration from file.

    Clears the cache and reloads configuration. Useful when the config
    file has been modified during runtime.

    Example:
        # After editing config/supported_languages.json
        reload_config()
        names = get_language_names()  # Will have updated values
    """
    global _config_cache
    _config_cache = None
    load_language_config(force_reload=True)


if __name__ == "__main__":
    # Display current configuration when run directly
    print_colored("\n=== Language Configuration ===\n", Fore.CYAN)

    names = get_language_names()
    mappings = get_lokalise_mappings()

    print(f"Config file: {CONFIG_FILE}")
    print(f"Total languages: {len(get_supported_languages())}\n")

    print("Language Names:")
    for code in sorted(get_supported_languages()):
        lokalise_code = mappings.get(code, code)
        name = names.get(code, code)
        if lokalise_code != code:
            print(f"  {code} ({lokalise_code}): {name}")
        else:
            print(f"  {code}: {name}")
