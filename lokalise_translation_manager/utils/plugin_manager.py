"""
Plugin Configuration Manager

This module manages plugin configuration and discovery for the Lokalise Translation
Manager Tool. It provides functionality to enable/disable plugins without deleting
files, auto-discover new plugins, and synchronize configuration.

Features:
    - Enable/disable plugins via configuration file
    - Auto-discover new plugins in the plugins directory
    - Synchronize config with actual plugins present
    - Validate plugin configuration
    - Provide plugin status information

Plugin Types:
    - ACTION: Execute before translation, can bypass OpenAI
    - EXTENSION: Process translated data after translation
    - PROMPT: Modify translation prompts (handled in translator)

Configuration File:
    Location: config/plugins_config.json
    Format:
        {
            "plugins": {
                "plugin_name.py": {
                    "enabled": true,
                    "type": "ACTION",
                    "description": "Plugin description",
                    "auto_discovered": true
                }
            },
            "settings": {
                "auto_discover_new_plugins": true,
                "warn_on_disabled_plugins": true,
                "fail_on_plugin_error": false
            }
        }

Usage:
    from lokalise_translation_manager.utils.plugin_manager import (
        load_plugin_config,
        is_plugin_enabled,
        sync_plugin_config
    )

    # Load configuration
    config = load_plugin_config()

    # Check if plugin is enabled
    if is_plugin_enabled("myPayments.py", config):
        # Execute plugin
        pass

    # Sync configuration with discovered plugins
    sync_plugin_config()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from colorama import Fore
    color_enabled = True
except ImportError:
    color_enabled = False
    class Fore:
        CYAN = ''
        GREEN = ''
        YELLOW = ''
        RED = ''

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "plugins_config.json"
PLUGINS_DIR = BASE_DIR / "lokalise_translation_manager" / "plugins"

DEFAULT_CONFIG = {
    "_comment": "Plugin Configuration File - Enable/Disable plugins without deleting them",
    "_info": {
        "description": "This file controls which plugins are active in the translation workflow",
        "plugin_types": {
            "ACTION": "Execute before translation, can bypass OpenAI translation",
            "EXTENSION": "Process translated data after translation completes",
            "PROMPT": "Modify translation prompts (handled in translator module)"
        },
        "usage": "Set 'enabled' to false to disable a plugin without deleting the file"
    },
    "plugins": {},
    "settings": {
        "auto_discover_new_plugins": True,
        "warn_on_disabled_plugins": True,
        "fail_on_plugin_error": False
    }
}


def print_colored(text: str, color: str) -> None:
    """Print colored text with colorama fallback."""
    print(color + text if color_enabled else text)


def load_plugin_config() -> Dict:
    """
    Load plugin configuration from config/plugins_config.json.

    Returns:
        Dict: Plugin configuration dictionary

    Note:
        - Creates default config if file doesn't exist
        - Returns default config on parse errors
        - Always returns a valid dictionary
    """
    if not CONFIG_FILE.exists():
        print_colored(
            f"Plugin config not found. Creating default: {CONFIG_FILE}",
            Fore.YELLOW
        )
        save_plugin_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with CONFIG_FILE.open('r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        print_colored(
            f"Error loading plugin config: {e}. Using defaults.",
            Fore.RED
        )
        return DEFAULT_CONFIG


def save_plugin_config(config: Dict) -> None:
    """
    Save plugin configuration to config/plugins_config.json.

    Args:
        config: Plugin configuration dictionary to save

    Note:
        - Creates config directory if it doesn't exist
        - Writes with UTF-8 encoding and indentation
        - Handles errors gracefully
    """
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print_colored(f"Error saving plugin config: {e}", Fore.RED)


def is_plugin_enabled(plugin_name: str, config: Optional[Dict] = None) -> bool:
    """
    Check if a plugin is enabled in the configuration.

    Args:
        plugin_name: Name of the plugin file (e.g., "myPayments.py")
        config: Plugin configuration (loads if not provided)

    Returns:
        bool: True if plugin is enabled, False otherwise

    Note:
        - Returns True if plugin not in config and auto_discover is enabled
        - Returns False if plugin explicitly disabled
        - Returns True by default for backward compatibility
    """
    if config is None:
        config = load_plugin_config()

    plugins = config.get("plugins", {})
    settings = config.get("settings", {})

    if plugin_name not in plugins:
        # Plugin not in config - check auto_discover setting
        auto_discover = settings.get("auto_discover_new_plugins", True)
        return auto_discover

    # Plugin in config - check enabled status
    return plugins[plugin_name].get("enabled", True)


def detect_plugin_type(plugin_path: Path) -> Optional[str]:
    """
    Detect plugin type by scanning for marker comments.

    Args:
        plugin_path: Path to the plugin file

    Returns:
        Optional[str]: Plugin type ("ACTION", "EXTENSION", "PROMPT") or None

    Note:
        - Scans file content for [ACTION], [EXTENSION], or [PROMPT] markers
        - Returns first marker found
        - Returns None if no marker found or file unreadable
    """
    try:
        content = plugin_path.read_text(encoding='utf-8')
        if '[ACTION]' in content:
            return 'ACTION'
        elif '[EXTENSION]' in content:
            return 'EXTENSION'
        elif '[PROMPT]' in content:
            return 'PROMPT'
    except Exception:
        pass
    return None


def discover_all_plugins() -> Dict[str, str]:
    """
    Discover all plugins in the plugins directory.

    Returns:
        Dict[str, str]: Dictionary mapping plugin names to types
                       e.g., {"myPayments.py": "EXTENSION"}

    Note:
        - Scans all .py files in plugins directory
        - Excludes __init__.py files
        - Detects plugin type by marker
        - Returns empty dict if plugins directory doesn't exist
    """
    discovered = {}

    if not PLUGINS_DIR.exists():
        return discovered

    for plugin_file in PLUGINS_DIR.glob('*.py'):
        if plugin_file.name == '__init__.py':
            continue

        plugin_type = detect_plugin_type(plugin_file)
        if plugin_type:
            discovered[plugin_file.name] = plugin_type

    return discovered


def sync_plugin_config() -> Tuple[List[str], List[str]]:
    """
    Synchronize plugin configuration with discovered plugins.

    Updates config/plugins_config.json to include newly discovered plugins
    and marks missing plugins. Does not delete entries for missing plugins
    to preserve user settings.

    Returns:
        Tuple[List[str], List[str]]: (new_plugins, missing_plugins)

    Workflow:
        1. Load current configuration
        2. Discover all plugins in directory
        3. Add new plugins to config (if auto_discover enabled)
        4. Mark missing plugins in config
        5. Save updated configuration

    Example:
        new, missing = sync_plugin_config()
        print(f"Added {len(new)} new plugins")
        print(f"Found {len(missing)} missing plugins")
    """
    config = load_plugin_config()
    discovered = discover_all_plugins()
    settings = config.get("settings", {})

    new_plugins = []
    missing_plugins = []

    # Add newly discovered plugins
    if settings.get("auto_discover_new_plugins", True):
        for plugin_name, plugin_type in discovered.items():
            if plugin_name not in config.get("plugins", {}):
                config.setdefault("plugins", {})[plugin_name] = {
                    "enabled": True,
                    "type": plugin_type,
                    "description": f"Auto-discovered {plugin_type} plugin",
                    "auto_discovered": True
                }
                new_plugins.append(plugin_name)

    # Mark missing plugins (but don't delete entries)
    for plugin_name in config.get("plugins", {}).keys():
        if plugin_name not in discovered:
            missing_plugins.append(plugin_name)
            # Optionally mark as missing
            config["plugins"][plugin_name]["_missing"] = True

    # Remove _missing flag for plugins that are present
    for plugin_name in discovered.keys():
        if plugin_name in config.get("plugins", {}):
            config["plugins"][plugin_name].pop("_missing", None)

    save_plugin_config(config)

    return new_plugins, missing_plugins


def get_enabled_plugins_by_type(plugin_type: str) -> List[str]:
    """
    Get list of enabled plugins of a specific type.

    Args:
        plugin_type: Type of plugins to retrieve ("ACTION", "EXTENSION", "PROMPT")

    Returns:
        List[str]: List of enabled plugin filenames

    Note:
        - Only returns plugins that exist in the directory
        - Only returns plugins that are enabled in config
        - Respects auto_discover setting for unlisted plugins

    Example:
        action_plugins = get_enabled_plugins_by_type("ACTION")
        for plugin in action_plugins:
            print(f"Executing {plugin}")
    """
    config = load_plugin_config()
    discovered = discover_all_plugins()
    enabled = []

    for plugin_name, discovered_type in discovered.items():
        if discovered_type == plugin_type:
            if is_plugin_enabled(plugin_name, config):
                enabled.append(plugin_name)

    return enabled


def print_plugin_status() -> None:
    """
    Print plugin configuration status to console.

    Displays:
        - Total plugins discovered
        - Enabled vs disabled plugins
        - Plugin types
        - Missing plugins (in config but not in directory)

    Note:
        - Uses colored output if colorama available
        - Provides detailed plugin information
        - Useful for debugging plugin issues
    """
    config = load_plugin_config()
    discovered = discover_all_plugins()

    print_colored("\n📦 Plugin Configuration Status:", Fore.CYAN)
    print_colored(f"  Config file: {CONFIG_FILE}", Fore.CYAN)
    print_colored(f"  Plugins directory: {PLUGINS_DIR}\n", Fore.CYAN)

    # Discovered plugins
    print_colored(f"Discovered Plugins: {len(discovered)}", Fore.GREEN)
    for plugin_name, plugin_type in discovered.items():
        enabled = is_plugin_enabled(plugin_name, config)
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        color = Fore.GREEN if enabled else Fore.YELLOW
        print_colored(f"  {status} [{plugin_type}] {plugin_name}", color)

    # Missing plugins (in config but not discovered)
    config_plugins = config.get("plugins", {})
    missing = [p for p in config_plugins.keys() if p not in discovered]

    if missing:
        print_colored(f"\nMissing Plugins (in config but not found): {len(missing)}", Fore.YELLOW)
        for plugin_name in missing:
            plugin_info = config_plugins[plugin_name]
            plugin_type = plugin_info.get("type", "UNKNOWN")
            print_colored(f"  ⚠️  [{plugin_type}] {plugin_name}", Fore.YELLOW)

    # Settings
    settings = config.get("settings", {})
    print_colored("\nSettings:", Fore.CYAN)
    print_colored(f"  Auto-discover new plugins: {settings.get('auto_discover_new_plugins', True)}", Fore.CYAN)
    print_colored(f"  Warn on disabled plugins: {settings.get('warn_on_disabled_plugins', True)}", Fore.CYAN)
    print_colored(f"  Fail on plugin error: {settings.get('fail_on_plugin_error', False)}", Fore.CYAN)


if __name__ == "__main__":
    # Run sync and print status when executed directly
    print_colored("🔄 Synchronizing plugin configuration...", Fore.CYAN)
    new, missing = sync_plugin_config()

    if new:
        print_colored(f"\n✅ Added {len(new)} new plugin(s) to configuration:", Fore.GREEN)
        for plugin in new:
            print_colored(f"  - {plugin}", Fore.GREEN)

    if missing:
        print_colored(f"\n⚠️  {len(missing)} plugin(s) in config but not found:", Fore.YELLOW)
        for plugin in missing:
            print_colored(f"  - {plugin}", Fore.YELLOW)

    print_plugin_status()
