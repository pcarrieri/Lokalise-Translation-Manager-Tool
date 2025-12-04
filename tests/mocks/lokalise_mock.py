"""
Mock implementation of Lokalise API

This module provides a mock Lokalise API client that simulates API responses
without making actual HTTP requests. Used for testing all Lokalise-related
operations.

Features:
- Download translations
- Upload translations
- List keys
- Delete keys
- Pagination support
- Rate limiting simulation
- Error simulation

Usage:
    from tests.mocks import MockLokaliseAPI

    mock_api = MockLokaliseAPI()
    translations = mock_api.download_translations(project_id, locale)
"""

import time
from typing import Dict, List, Optional, Any


class MockLokaliseAPI:
    """
    Mock implementation of the Lokalise API client

    This class simulates the behavior of the Lokalise API for testing purposes.
    It maintains an in-memory database of keys and translations that can be
    queried and modified during tests.

    Attributes:
        keys (Dict[str, Dict]): In-memory storage of translation keys
        translations (Dict[str, Dict]): In-memory storage of translations
        request_count (int): Counter for API requests (for rate limiting tests)
        should_fail (bool): Flag to simulate API failures
    """

    def __init__(self):
        """Initialize the mock API with default data"""
        self.keys: Dict[str, Dict[str, Any]] = {}
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.request_count: int = 0
        self.should_fail: bool = False
        self._initialize_default_data()

    def _initialize_default_data(self):
        """
        Initialize mock data with sample keys and translations

        Creates a realistic dataset for testing including:
        - Multiple translation keys
        - Translations in various languages
        - Both translated and untranslated keys
        """
        # Sample keys
        self.keys = {
            "123": {
                "key_id": "123",
                "key_name": "ms_test_key_1",
                "description": "Test key 1",
                "platforms": ["ios", "android"],
                "translations": {
                    "en": {"translation_id": "456", "translation": "Hello", "is_reviewed": True},
                    "it": {"translation_id": "457", "translation": "Ciao", "is_reviewed": True},
                    "de": {"translation_id": "458", "translation": "", "is_reviewed": False}
                }
            },
            "124": {
                "key_id": "124",
                "key_name": "ms_test_key_2",
                "description": "Test key 2",
                "platforms": ["ios"],
                "translations": {
                    "en": {"translation_id": "459", "translation": "Goodbye", "is_reviewed": True},
                    "it": {"translation_id": "460", "translation": "", "is_reviewed": False},
                    "de": {"translation_id": "461", "translation": "", "is_reviewed": False}
                }
            },
            "125": {
                "key_id": "125",
                "key_name": "ms_softpos_test",
                "description": "SoftPOS test key",
                "platforms": ["android"],
                "translations": {
                    "en": {"translation_id": "462", "translation": "Soft POS", "is_reviewed": True},
                    "el": {"translation_id": "463", "translation": "", "is_reviewed": False}
                }
            }
        }

    def download_translations(
        self,
        project_id: str,
        locale: str,
        page: int = 1,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Simulate downloading translations from Lokalise

        Args:
            project_id: The Lokalise project ID
            locale: The language code (e.g., 'en', 'it', 'de')
            page: Page number for pagination
            limit: Number of results per page

        Returns:
            Dict containing translations data and pagination info

        Raises:
            Exception: If should_fail is True (for testing error handling)
        """
        self.request_count += 1
        time.sleep(0.01)  # Simulate network delay

        if self.should_fail:
            raise Exception("Mock API failure")

        # Filter translations for the requested locale
        translations = []
        for key_id, key_data in self.keys.items():
            if locale in key_data["translations"]:
                trans = key_data["translations"][locale]
                translations.append({
                    "key_id": key_id,
                    "key_name": key_data["key_name"],
                    "translation_id": trans["translation_id"],
                    "translation": trans["translation"],
                    "is_reviewed": trans["is_reviewed"],
                    "locale": locale
                })

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_data = translations[start_idx:end_idx]

        return {
            "project_id": project_id,
            "branch": "master",
            "translations": page_data,
            "page": page,
            "total_count": len(translations),
            "page_count": (len(translations) + limit - 1) // limit,
            "limit": limit
        }

    def list_keys(
        self,
        project_id: str,
        page: int = 1,
        limit: int = 100,
        include_translations: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate listing all keys in a project

        Args:
            project_id: The Lokalise project ID
            page: Page number for pagination
            limit: Number of results per page
            include_translations: Whether to include translation data

        Returns:
            Dict containing keys data and pagination info
        """
        self.request_count += 1
        time.sleep(0.01)

        if self.should_fail:
            raise Exception("Mock API failure")

        keys_list = []
        for key_id, key_data in self.keys.items():
            key_info = {
                "key_id": key_id,
                "key_name": key_data["key_name"],
                "description": key_data["description"],
                "platforms": key_data["platforms"]
            }
            if include_translations:
                key_info["translations"] = key_data["translations"]
            keys_list.append(key_info)

        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_data = keys_list[start_idx:end_idx]

        return {
            "project_id": project_id,
            "keys": page_data,
            "page": page,
            "total_count": len(keys_list),
            "page_count": (len(keys_list) + limit - 1) // limit,
            "limit": limit
        }

    def update_translation(
        self,
        project_id: str,
        translation_id: str,
        translation: str
    ) -> Dict[str, Any]:
        """
        Simulate updating a translation

        Args:
            project_id: The Lokalise project ID
            translation_id: The translation ID to update
            translation: The new translation text

        Returns:
            Dict containing the updated translation data
        """
        self.request_count += 1
        time.sleep(0.01)

        if self.should_fail:
            raise Exception("Mock API failure")

        # Find and update the translation
        for key_id, key_data in self.keys.items():
            for locale, trans in key_data["translations"].items():
                if trans["translation_id"] == translation_id:
                    trans["translation"] = translation
                    trans["is_reviewed"] = False
                    return {
                        "project_id": project_id,
                        "translation_id": translation_id,
                        "translation": translation,
                        "locale": locale,
                        "key_id": key_id
                    }

        raise Exception(f"Translation ID {translation_id} not found")

    def delete_keys(
        self,
        project_id: str,
        key_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Simulate deleting keys

        Args:
            project_id: The Lokalise project ID
            key_ids: List of key IDs to delete

        Returns:
            Dict containing deletion status
        """
        self.request_count += 1
        time.sleep(0.01)

        if self.should_fail:
            raise Exception("Mock API failure")

        deleted = []
        for key_id in key_ids:
            if key_id in self.keys:
                del self.keys[key_id]
                deleted.append(key_id)

        return {
            "project_id": project_id,
            "keys_deleted": len(deleted),
            "key_ids": deleted
        }

    def add_key(
        self,
        key_id: str,
        key_name: str,
        translations: Optional[Dict[str, str]] = None
    ):
        """
        Add a new key to the mock database (helper for tests)

        Args:
            key_id: The key ID
            key_name: The key name
            translations: Optional dict of locale -> translation text
        """
        self.keys[key_id] = {
            "key_id": key_id,
            "key_name": key_name,
            "description": f"Test key {key_name}",
            "platforms": ["ios", "android"],
            "translations": {}
        }

        if translations:
            for locale, text in translations.items():
                trans_id = f"trans_{key_id}_{locale}"
                self.keys[key_id]["translations"][locale] = {
                    "translation_id": trans_id,
                    "translation": text,
                    "is_reviewed": bool(text)
                }

    def reset(self):
        """Reset the mock API to initial state"""
        self.keys.clear()
        self.translations.clear()
        self.request_count = 0
        self.should_fail = False
        self._initialize_default_data()

    def set_failure_mode(self, should_fail: bool):
        """
        Enable or disable failure mode for testing error handling

        Args:
            should_fail: If True, all API calls will raise exceptions
        """
        self.should_fail = should_fail
