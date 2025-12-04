#!/usr/bin/env python3
"""
Test Runner for Lokalise Translation Manager Tool

This script runs the complete test suite including:
- Unit tests (individual components)
- Integration tests (full workflows)
- Mock API tests (Lokalise, OpenAI)
- Plugin tests

Usage:
    # Run all tests
    python3 run_tests.py

    # Run specific test suite
    python3 run_tests.py --unit
    python3 run_tests.py --integration

    # Run with verbose output
    python3 run_tests.py --verbose

    # Run with coverage report
    python3 run_tests.py --coverage

Requirements:
    pip install pytest pytest-cov pytest-mock
"""

import sys
import argparse
import subprocess
from pathlib import Path


class TestRunner:
    """
    Main test runner class

    Handles test execution, coverage reporting, and result formatting.
    """

    def __init__(self, verbose: bool = False, coverage: bool = False):
        """
        Initialize the test runner

        Args:
            verbose: Enable verbose output
            coverage: Enable coverage reporting
        """
        self.verbose = verbose
        self.coverage = coverage
        self.base_dir = Path(__file__).parent
        self.tests_dir = self.base_dir / "tests"

    def run_all_tests(self) -> int:
        """
        Run all test suites

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        print("=" * 70)
        print("Running ALL tests for Lokalise Translation Manager Tool")
        print("=" * 70)
        print()

        cmd = self._build_pytest_command("tests/")
        return self._execute_command(cmd)

    def run_unit_tests(self) -> int:
        """
        Run only unit tests

        Returns:
            Exit code
        """
        print("=" * 70)
        print("Running UNIT tests")
        print("=" * 70)
        print()

        cmd = self._build_pytest_command("tests/unit/")
        return self._execute_command(cmd)

    def run_integration_tests(self) -> int:
        """
        Run only integration tests

        Returns:
            Exit code
        """
        print("=" * 70)
        print("Running INTEGRATION tests")
        print("=" * 70)
        print()

        cmd = self._build_pytest_command("tests/integration/")
        return self._execute_command(cmd)

    def _build_pytest_command(self, path: str) -> list:
        """
        Build the pytest command with appropriate flags

        Args:
            path: Path to test directory or file

        Returns:
            Command as list of strings
        """
        cmd = [sys.executable, "-m", "pytest", path]

        if self.verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")

        if self.coverage:
            cmd.extend([
                "--cov=lokalise_translation_manager",
                "--cov-report=html",
                "--cov-report=term"
            ])

        # Add useful pytest options
        cmd.extend([
            "--tb=short",  # Shorter traceback format
            "-ra"          # Show summary of all test outcomes
        ])

        return cmd

    def _execute_command(self, cmd: list) -> int:
        """
        Execute a shell command and return exit code

        Args:
            cmd: Command as list of strings

        Returns:
            Exit code
        """
        try:
            result = subprocess.run(cmd, cwd=self.base_dir)
            return result.returncode
        except FileNotFoundError:
            print("\n❌ ERROR: pytest not found!")
            print("Please install pytest: pip install pytest pytest-cov pytest-mock")
            return 1
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return 1

    def check_dependencies(self) -> bool:
        """
        Check if all required testing dependencies are installed

        Returns:
            True if all dependencies are available, False otherwise
        """
        required = ["pytest", "pytest_cov", "pytest_mock"]
        missing = []

        for module in required:
            try:
                __import__(module)
            except ImportError:
                missing.append(module.replace("_", "-"))

        if missing:
            print("❌ Missing required dependencies:")
            for dep in missing:
                print(f"   - {dep}")
            print("\nInstall with: pip install " + " ".join(missing))
            return False

        return True


def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description="Run tests for Lokalise Translation Manager Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_tests.py                    # Run all tests
  python3 run_tests.py --unit             # Run only unit tests
  python3 run_tests.py --integration      # Run only integration tests
  python3 run_tests.py --verbose          # Verbose output
  python3 run_tests.py --coverage         # Generate coverage report
        """
    )

    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = TestRunner(verbose=args.verbose, coverage=args.coverage)

    # Check dependencies
    if not runner.check_dependencies():
        return 1

    # Run requested tests
    if args.unit:
        exit_code = runner.run_unit_tests()
    elif args.integration:
        exit_code = runner.run_integration_tests()
    else:
        exit_code = runner.run_all_tests()

    # Print summary
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ All tests PASSED")
    else:
        print("❌ Some tests FAILED")
    print("=" * 70)

    if args.coverage:
        print("\n📊 Coverage report generated in htmlcov/index.html")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
