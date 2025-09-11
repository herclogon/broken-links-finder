#!/usr/bin/env python3
"""
Test runner script for the Broken Link Checker

This script provides various test execution options:
- Run all tests
- Run specific test categories
- Generate coverage reports
- Run performance tests
"""

import sys
import subprocess
import argparse
import os


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install -r test_requirements.txt")
        return False


def install_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    return run_command([
        sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"
    ], "Installing test dependencies")


def run_unit_tests():
    """Run unit tests only"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "test_broken_link_checker.py::TestBrokenLinkChecker",
        "-v"
    ], "Unit tests")


def run_integration_tests():
    """Run integration tests only"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "test_broken_link_checker.py::TestIntegration",
        "-v"
    ], "Integration tests")


def run_cli_tests():
    """Run CLI tests only"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "test_broken_link_checker.py::TestMainFunction",
        "-v"
    ], "CLI tests")


def run_all_tests():
    """Run all tests with coverage"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "test_broken_link_checker.py",
        "-v",
        "--cov=broken_link_checker",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov"
    ], "All tests with coverage")


def run_quick_tests():
    """Run tests without coverage for quick feedback"""
    return run_command([
        sys.executable, "-m", "pytest", 
        "test_broken_link_checker.py",
        "-v",
        "--tb=short"
    ], "Quick tests (no coverage)")


def run_specific_test(test_name):
    """Run a specific test"""
    return run_command([
        sys.executable, "-m", "pytest", 
        f"test_broken_link_checker.py::{test_name}",
        "-v", "-s"
    ], f"Specific test: {test_name}")


def lint_code():
    """Run code linting"""
    print("Running code linting...")
    
    # Check if flake8 is available
    try:
        subprocess.run([sys.executable, "-m", "flake8", "--version"], 
                      check=True, capture_output=True)
        return run_command([
            sys.executable, "-m", "flake8", 
            "broken_link_checker.py", "test_broken_link_checker.py",
            "--max-line-length=100",
            "--ignore=E501,W503"
        ], "Code linting with flake8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  flake8 not available, skipping linting")
        print("Install with: pip install flake8")
        return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test runner for Broken Link Checker")
    parser.add_argument("--install", action="store_true", 
                       help="Install test dependencies")
    parser.add_argument("--unit", action="store_true", 
                       help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", 
                       help="Run integration tests only")
    parser.add_argument("--cli", action="store_true", 
                       help="Run CLI tests only")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick tests without coverage")
    parser.add_argument("--lint", action="store_true", 
                       help="Run code linting")
    parser.add_argument("--test", type=str, 
                       help="Run specific test (e.g., TestBrokenLinkChecker::test_init)")
    parser.add_argument("--all", action="store_true", 
                       help="Run all tests with coverage (default)")
    
    args = parser.parse_args()
    
    # If no specific arguments, run all tests
    if not any([args.install, args.unit, args.integration, args.cli, 
                args.quick, args.lint, args.test]):
        args.all = True
    
    success = True
    
    if args.install:
        success &= install_dependencies()
    
    if args.lint:
        success &= lint_code()
    
    if args.unit:
        success &= run_unit_tests()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.cli:
        success &= run_cli_tests()
    
    if args.quick:
        success &= run_quick_tests()
    
    if args.test:
        success &= run_specific_test(args.test)
    
    if args.all:
        success &= run_all_tests()
    
    # Final summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All operations completed successfully!")
        if args.all or (not any([args.unit, args.integration, args.cli, args.quick, args.test])):
            print("\n📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Some operations failed!")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
