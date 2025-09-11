# Contributing to Broken Links Finder

Thank you for your interest in contributing to the Broken Links Finder project! This document provides guidelines for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment
4. Create a new branch for your feature or bug fix
5. Make your changes
6. Test your changes
7. Submit a pull request

## How to Contribute

### Types of Contributions

We welcome several types of contributions:

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new functionality
- **Code Contributions**: Implement new features or fix bugs
- **Documentation**: Improve or add documentation
- **Testing**: Add or improve test coverage

### What We're Looking For

- Bug fixes
- Performance improvements
- New features that align with the project's goals
- Documentation improvements
- Test coverage improvements
- Code quality improvements

## Development Setup

### Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

### Installation

1. Clone your fork:
   ```bash
   git clone git@github.com:herclogon/broken-links-finder.git
   cd broken-links-finder
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r test_requirements.txt
   ```

### Project Structure

```
broken-links-finder/
├── broken_links_finder.py    # Main script
├── requirements.txt          # Production dependencies
├── test_requirements.txt     # Test dependencies
├── test_broken_links_finder.py  # Test suite
├── run_tests.py             # Test runner
├── pytest.ini              # Pytest configuration
├── README.md                # Project documentation
├── CONTRIBUTING.md          # This file
├── LICENSE                  # MIT License
├── .gitignore              # Git ignore rules
└── Makefile                # Build automation
```

## Testing

### Running Tests

We use pytest for testing. To run the test suite:

```bash
# Run all tests
python run_tests.py

# Run tests with pytest directly
pytest

# Run tests with coverage
pytest --cov=broken_links_finder

# Run specific test
pytest test_broken_links_finder.py::TestBrokenLinksFinder::test_specific_function
```

### Writing Tests

- Write tests for new functionality
- Ensure existing tests pass
- Aim for good test coverage
- Use descriptive test names
- Follow the existing test patterns

### Test Guidelines

- Tests should be independent and not rely on external resources
- Use mocking for external dependencies (HTTP requests, file system)
- Test both success and failure scenarios
- Include edge cases in your tests

## Submitting Changes

### Pull Request Process

1. **Create a Branch**: Create a feature branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**: Implement your changes with clear, focused commits

3. **Test**: Ensure all tests pass and add new tests if needed

4. **Commit**: Write clear commit messages
   ```bash
   git commit -m "Add feature: brief description of what you added"
   ```

5. **Push**: Push your branch to your fork
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Pull Request**: Create a pull request with:
   - Clear title and description
   - Reference to any related issues
   - Description of changes made
   - Any breaking changes noted

### Commit Message Guidelines

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Add comments for complex logic

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Detailed steps to reproduce the bug
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: Python version, OS, etc.
- **Error Messages**: Full error messages and stack traces
- **Additional Context**: Any other relevant information

### Feature Requests

When requesting features, please include:

- **Description**: Clear description of the feature
- **Use Case**: Why this feature would be useful
- **Proposed Solution**: How you think it should work
- **Alternatives**: Any alternative solutions you've considered

### Issue Labels

We use labels to categorize issues:

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed

## Development Guidelines

### Adding New Features

1. Check if the feature aligns with project goals
2. Create an issue to discuss the feature first
3. Implement the feature with tests
4. Update documentation as needed
5. Submit a pull request

### Code Review Process

- All submissions require review
- Reviewers will check for:
  - Code quality and style
  - Test coverage
  - Documentation
  - Compatibility
  - Performance implications

### Release Process

- We follow semantic versioning (SemVer)
- Releases are tagged and include release notes
- Breaking changes are clearly documented

## Getting Help

If you need help:

- Check existing issues and documentation
- Create a new issue with the `question` label
- Be specific about what you're trying to do
- Include relevant code snippets or error messages

## Recognition

Contributors will be recognized in:

- The project's README
- Release notes for significant contributions
- GitHub's contributor statistics

Thank you for contributing to Broken Links Finder!
