"""
Test Suite for Lokalise Translation Manager Tool

This package contains comprehensive tests for all components of the tool:
- Unit tests: Test individual functions and classes in isolation
- Integration tests: Test complete workflows and component interactions
- Fixtures: Reusable test data and configurations
- Mocks: Mock objects for external API calls (Lokalise, OpenAI)

Test Organization:
- tests/unit/: Unit tests for individual modules
- tests/integration/: End-to-end workflow tests
- tests/fixtures/: CSV files and test data
- tests/mocks/: Mock implementations of external services

Running Tests:
    # Run all tests
    pytest tests/

    # Run specific test suite
    pytest tests/unit/
    pytest tests/integration/

    # Run with coverage
    pytest --cov=lokalise_translation_manager tests/

    # Run with verbose output
    pytest -v tests/
"""

__version__ = "1.0.0"
