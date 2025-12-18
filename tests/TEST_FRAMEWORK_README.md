# Test Framework Documentation

## Overview

This testing framework provides comprehensive test coverage for the Lokalise Translation Manager Tool. It includes mocked external services, test fixtures, and both unit and integration tests.

## Structure

```
tests/
├── __init__.py                     # Test package initialization
├── unit/                           # Unit tests (individual components)
│   ├── test_csv_utils.py
│   ├── test_ios_scanner.py
│   ├── test_android_scanner.py
│   ├── test_translator.py
│   └── test_plugins.py
├── integration/                    # Integration tests (full workflows)
│   ├── test_full_workflow.py
│   ├── test_plugin_integration.py
│   └── test_api_integration.py
├── mocks/                          # Mock implementations
│   ├── __init__.py
│   ├── lokalise_mock.py           # Mock Lokalise API
│   └── openai_mock.py             # Mock OpenAI API
├── fixtures/                       # Test data
│   ├── __init__.py
│   ├── sample_translations.csv
│   ├── sample_keys.csv
│   └── config/
│       └── test_config.json
└── TEST_FRAMEWORK_README.md       # This file
```

## Running Tests

### Prerequisites

Install testing dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

### Run All Tests

```bash
# Using the test runner script
python3 run_tests.py

# Or directly with pytest
pytest tests/
```

### Run Specific Test Suites

```bash
# Unit tests only
python3 run_tests.py --unit
pytest tests/unit/

# Integration tests only
python3 run_tests.py --integration
pytest tests/integration/

# Specific test file
pytest tests/unit/test_csv_utils.py

# Specific test function
pytest tests/unit/test_csv_utils.py::test_detect_delimiter
```

### With Coverage

```bash
# Generate coverage report
python3 run_tests.py --coverage

# Or with pytest
pytest --cov=lokalise_translation_manager --cov-report=html tests/
```

Coverage report will be generated in `htmlcov/index.html`.

### Verbose Output

```bash
python3 run_tests.py --verbose
pytest -v tests/
```

## Mock Services

### Lokalise API Mock

The `MockLokaliseAPI` class simulates the Lokalise API without making actual HTTP requests.

**Features:**
- Download translations with pagination
- List translation keys
- Update translations
- Delete keys
- Simulate API failures (for error handling tests)
- Track API request count (for rate limiting tests)

**Usage in tests:**
```python
from tests.mocks import MockLokaliseAPI

def test_download_translations():
    mock_api = MockLokaliseAPI()

    # Download translations for Italian
    result = mock_api.download_translations(
        project_id="test-project",
        locale="it",
        page=1,
        limit=100
    )

    assert "translations" in result
    assert len(result["translations"]) > 0
```

**Simulating failures:**
```python
def test_api_error_handling():
    mock_api = MockLokaliseAPI()
    mock_api.set_failure_mode(True)

    # This will raise an exception
    with pytest.raises(Exception):
        mock_api.download_translations("test-project", "it")
```

### OpenAI API Mock

The `MockOpenAIAPI` class simulates OpenAI's translation API.

**Features:**
- Predefined translations for common phrases
- Rule-based translation generation
- Token counting and cost estimation
- Various failure modes (rate limit, timeout, connection error)
- Batch translation support

**Usage in tests:**
```python
from tests.mocks import MockOpenAIAPI

def test_translation():
    mock_api = MockOpenAIAPI()

    # Translate text
    result = mock_api.translate("Hello", "it")
    assert result == "Ciao"

    # Check stats
    stats = mock_api.get_stats()
    assert stats["request_count"] == 1
```

**Adding custom translations:**
```python
def test_custom_translation():
    mock_api = MockOpenAIAPI()
    mock_api.add_translation("Custom text", "it", "Testo personalizzato")

    result = mock_api.translate("Custom text", "it")
    assert result == "Testo personalizzato"
```

**Simulating rate limits:**
```python
def test_rate_limit_handling():
    mock_api = MockOpenAIAPI()
    mock_api.set_failure_mode(True, "rate_limit")

    with pytest.raises(Exception, match="Rate limit"):
        mock_api.translate("Hello", "it")
```

## Writing Tests

### Unit Test Example

```python
"""Test CSV utilities"""

import pytest
from lokalise_translation_manager.utils.csv_utils import detect_csv_delimiter
from pathlib import Path

def test_detect_comma_delimiter(tmp_path):
    """Test detection of comma delimiter"""
    # Create test CSV with comma delimiter
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("col1,col2,col3\nval1,val2,val3\n")

    # Detect delimiter
    delimiter = detect_csv_delimiter(csv_file)

    # Assert
    assert delimiter == ","

def test_detect_semicolon_delimiter(tmp_path):
    """Test detection of semicolon delimiter"""
    # Create test CSV with semicolon delimiter
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("col1;col2;col3\nval1;val2;val3\n")

    # Detect delimiter
    delimiter = detect_csv_delimiter(csv_file)

    # Assert
    assert delimiter == ";"
```

### Integration Test Example

```python
"""Test full translation workflow"""

import pytest
from tests.mocks import MockLokaliseAPI, MockOpenAIAPI
from lokalise_translation_manager import core

def test_full_workflow_with_mocks(tmp_path, monkeypatch):
    """Test complete workflow with mocked APIs"""
    # Setup mocks
    lokalise_mock = MockLokaliseAPI()
    openai_mock = MockOpenAIAPI()

    # Monkeypatch API clients
    monkeypatch.setattr(
        "lokalise_translation_manager.download.lokalise_api",
        lokalise_mock
    )
    monkeypatch.setattr(
        "lokalise_translation_manager.translator.openai_api",
        openai_mock
    )

    # Run workflow
    # ... test code ...

    # Assertions
    assert lokalise_mock.request_count > 0
    assert openai_mock.request_count > 0
```

## Test Fixtures

Test fixtures are reusable test data located in `tests/fixtures/`.

### Using Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_translations_csv():
    """Provide path to sample translations CSV"""
    return Path(__file__).parent.parent / "fixtures" / "sample_translations.csv"

def test_with_fixture(sample_translations_csv):
    """Test using a fixture"""
    assert sample_translations_csv.exists()
    # ... use the fixture ...
```

### Temporary Files

Use pytest's `tmp_path` fixture for temporary files:

```python
def test_with_temp_file(tmp_path):
    """Test that creates temporary files"""
    test_file = tmp_path / "test.csv"
    test_file.write_text("test,data\n1,2\n")

    # ... test code ...

    # File is automatically cleaned up after test
```

## Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
# ✅ GOOD: Test is self-contained
def test_independent():
    data = create_test_data()
    result = process(data)
    assert result == expected

# ❌ BAD: Test depends on previous test
shared_state = {}

def test_step_1():
    shared_state['data'] = create_data()

def test_step_2():
    # Depends on test_step_1
    result = process(shared_state['data'])
```

### 2. Use Descriptive Names

```python
# ✅ GOOD: Clear what is being tested
def test_csv_delimiter_detection_with_comma():
    ...

def test_csv_delimiter_detection_with_semicolon():
    ...

# ❌ BAD: Unclear test purpose
def test_csv_1():
    ...

def test_csv_2():
    ...
```

### 3. Use Mocks for External Services

```python
# ✅ GOOD: Uses mock, no actual API calls
def test_translation_with_mock():
    mock_api = MockOpenAIAPI()
    result = translate_with_api(mock_api, "Hello", "it")
    assert result == "Ciao"

# ❌ BAD: Makes actual API calls (slow, costly, unreliable)
def test_translation_real_api():
    api = OpenAI(api_key="real-key")
    result = translate_with_api(api, "Hello", "it")
```

### 4. Test Edge Cases

```python
def test_empty_input():
    """Test behavior with empty input"""
    result = process_csv([])
    assert result == []

def test_malformed_data():
    """Test behavior with invalid data"""
    with pytest.raises(ValueError):
        process_csv("invalid,data,")

def test_large_dataset():
    """Test with large amount of data"""
    data = generate_large_dataset(10000)
    result = process_csv(data)
    assert len(result) == 10000
```

### 5. Use Assertions Effectively

```python
# ✅ GOOD: Specific assertions with clear error messages
def test_translation_count():
    result = translate_batch(["Hello", "Goodbye"], "it")
    assert len(result) == 2, "Expected 2 translations"
    assert result[0] == "Ciao", "First translation incorrect"
    assert result[1] == "Arrivederci", "Second translation incorrect"

# ❌ BAD: Generic assertion
def test_translation_count():
    result = translate_batch(["Hello", "Goodbye"], "it")
    assert result  # Too vague
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock

    - name: Run tests
      run: |
        python3 run_tests.py --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

**1. Import Errors**

```
ModuleNotFoundError: No module named 'lokalise_translation_manager'
```

**Solution:** Make sure you're running tests from the project root directory.

**2. Missing Dependencies**

```
ModuleNotFoundError: No module named 'pytest'
```

**Solution:** Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

**3. Tests Pass Locally But Fail in CI**

**Possible causes:**
- Environment-specific paths (use `Path` objects, not strings)
- Missing test dependencies in CI config
- Different Python versions

### Getting Help

- Check test output with `-v` flag for detailed information
- Run specific failing tests: `pytest tests/path/to/test.py::test_function -v`
- Use `pytest --pdb` to drop into debugger on failure

## Adding New Tests

### 1. Create Test File

```bash
# For unit tests
touch tests/unit/test_new_module.py

# For integration tests
touch tests/integration/test_new_workflow.py
```

### 2. Write Tests

```python
"""
Tests for new_module

This module tests the functionality of...
"""

import pytest
from lokalise_translation_manager import new_module

def test_basic_functionality():
    """Test basic function works correctly"""
    result = new_module.function()
    assert result == expected_value

def test_error_handling():
    """Test error cases are handled"""
    with pytest.raises(ValueError):
        new_module.function(invalid_input)
```

### 3. Run Tests

```bash
pytest tests/unit/test_new_module.py -v
```

### 4. Verify Coverage

```bash
pytest --cov=lokalise_translation_manager.new_module tests/unit/test_new_module.py
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
