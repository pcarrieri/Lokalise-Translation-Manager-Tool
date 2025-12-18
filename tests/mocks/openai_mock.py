"""
Mock implementation of OpenAI API

This module provides a mock OpenAI API client that simulates translation
responses without making actual API calls to OpenAI.

Features:
- Simulated translations (rule-based, not actual AI)
- Token counting
- Cost estimation
- Error simulation (rate limits, timeouts, etc.)
- Retry behavior testing

Usage:
    from tests.mocks import MockOpenAIAPI

    mock_api = MockOpenAIAPI()
    translation = mock_api.translate("Hello", "it")
    # Returns: "Ciao"
"""

import time
from typing import Dict, Optional, List
import random


class MockOpenAIAPI:
    """
    Mock implementation of the OpenAI API client

    This class simulates the behavior of OpenAI's GPT models for translation
    tasks. It uses a simple rule-based system to generate predictable
    translations for testing.

    Attributes:
        request_count (int): Counter for API requests
        total_tokens (int): Total tokens used across all requests
        should_fail (bool): Flag to simulate API failures
        failure_type (str): Type of failure to simulate
        translation_map (Dict): Predefined translations for testing
    """

    # Predefined translations for common test phrases
    TRANSLATION_MAP = {
        ("Hello", "it"): "Ciao",
        ("Hello", "de"): "Hallo",
        ("Hello", "fr"): "Bonjour",
        ("Hello", "es"): "Hola",
        ("Goodbye", "it"): "Arrivederci",
        ("Goodbye", "de"): "Auf Wiedersehen",
        ("Goodbye", "fr"): "Au revoir",
        ("Thank you", "it"): "Grazie",
        ("Thank you", "de"): "Danke",
        ("Thank you", "fr"): "Merci",
        ("Welcome", "it"): "Benvenuto",
        ("Welcome", "de"): "Willkommen",
        ("Welcome", "fr"): "Bienvenue",
    }

    def __init__(self):
        """Initialize the mock API"""
        self.request_count: int = 0
        self.total_tokens: int = 0
        self.should_fail: bool = False
        self.failure_type: str = "generic"
        self.translation_map: Dict[tuple, str] = self.TRANSLATION_MAP.copy()

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
        model: str = "gpt-4o-mini",
        temperature: float = 0.2
    ) -> str:
        """
        Simulate translating text using OpenAI

        Args:
            text: The text to translate
            target_language: Target language code (e.g., 'it', 'de')
            source_language: Source language code (default: 'en')
            model: OpenAI model to use (for mock, just stored)
            temperature: Temperature parameter (for mock, just stored)

        Returns:
            Translated text

        Raises:
            Exception: If should_fail is True (simulates API errors)
        """
        self.request_count += 1
        time.sleep(0.05)  # Simulate API latency

        # Simulate various failure modes
        if self.should_fail:
            if self.failure_type == "rate_limit":
                raise Exception("Rate limit exceeded. Please try again later.")
            elif self.failure_type == "timeout":
                raise TimeoutError("Request timed out")
            elif self.failure_type == "connection":
                raise ConnectionError("Connection failed")
            else:
                raise Exception("API error occurred")

        # Estimate tokens (rough approximation)
        tokens = len(text.split()) * 2  # Approximate: 2 tokens per word
        self.total_tokens += tokens

        # Check if we have a predefined translation
        key = (text, target_language)
        if key in self.translation_map:
            return self.translation_map[key]

        # Generate a mock translation for unknown phrases
        # Format: "[LANG:xx] Original text"
        return f"[LANG:{target_language}] {text}"

    def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: str = "en",
        model: str = "gpt-4o-mini"
    ) -> List[str]:
        """
        Simulate batch translation

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code
            model: OpenAI model to use

        Returns:
            List of translated texts
        """
        return [
            self.translate(text, target_language, source_language, model)
            for text in texts
        ]

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        timeout: int = 90
    ) -> Dict:
        """
        Simulate the OpenAI chat completion API

        This method simulates the full OpenAI API response structure,
        matching the actual API format.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            temperature: Temperature parameter
            timeout: Request timeout in seconds

        Returns:
            Dict matching OpenAI API response structure
        """
        self.request_count += 1
        time.sleep(0.05)

        if self.should_fail:
            if self.failure_type == "rate_limit":
                raise Exception("Rate limit exceeded")
            elif self.failure_type == "timeout":
                raise TimeoutError("Request timed out")
            else:
                raise Exception("API error")

        # Extract the user message (last message with role='user')
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        if not user_message:
            user_message = "No translation available"

        # Try to extract target language from system message
        target_lang = "unknown"
        for msg in messages:
            if msg.get('role') == 'system':
                content = msg.get('content', '')
                # Look for language code pattern
                if "into **" in content:
                    # Extract from "into **Language** (language code: `xx`)"
                    import re
                    match = re.search(r'language code: `(\w+)`', content)
                    if match:
                        target_lang = match.group(1)
                break

        # Generate translation
        translation = self.translate(user_message, target_lang)

        # Calculate tokens
        prompt_tokens = sum(len(msg.get('content', '').split()) * 2 for msg in messages)
        completion_tokens = len(translation.split()) * 2
        total_tokens = prompt_tokens + completion_tokens

        self.total_tokens += total_tokens

        return {
            "id": f"chatcmpl-mock-{self.request_count}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": translation
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
        }

    def add_translation(self, text: str, language: str, translation: str):
        """
        Add a custom translation to the mock database (helper for tests)

        Args:
            text: Original text
            language: Target language code
            translation: Translated text
        """
        self.translation_map[(text, language)] = translation

    def reset(self):
        """Reset the mock API to initial state"""
        self.request_count = 0
        self.total_tokens = 0
        self.should_fail = False
        self.failure_type = "generic"
        self.translation_map = self.TRANSLATION_MAP.copy()

    def set_failure_mode(self, should_fail: bool, failure_type: str = "generic"):
        """
        Enable or disable failure mode for testing error handling

        Args:
            should_fail: If True, API calls will raise exceptions
            failure_type: Type of failure ('rate_limit', 'timeout', 'connection', 'generic')
        """
        self.should_fail = should_fail
        self.failure_type = failure_type

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about API usage

        Returns:
            Dict with request_count and total_tokens
        """
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_tokens * 0.00001  # Mock pricing
        }
