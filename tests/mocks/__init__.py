"""
Mock implementations for external services

This module provides mock implementations for:
- Lokalise API (download translations, upload translations, manage keys)
- OpenAI API (translation requests)
- File system operations

These mocks allow testing without making actual API calls or
modifying the real file system.
"""

from .lokalise_mock import MockLokaliseAPI
from .openai_mock import MockOpenAIAPI

__all__ = ['MockLokaliseAPI', 'MockOpenAIAPI']
