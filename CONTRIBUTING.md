# Contributing to SiteShare

Thank you for considering contributing to SiteShare! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in the Issues section
- Use the bug report template when creating a new issue
- Include detailed steps to reproduce the bug
- Mention your operating system and Python version

### Suggesting Enhancements

- Check if the enhancement has already been suggested in the Issues section
- Use the feature request template when creating a new issue
- Explain why this enhancement would be useful to most SiteShare users

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests if available
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

1. Clone your fork of the repository
2. Navigate to the directory (`cd siteshare`)
3. Create a virtual environment (optional but recommended)
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install development dependencies
   ```
   pip install -e .
   ```

## Style Guidelines

- Follow PEP 8 style guide for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep lines under 100 characters when possible

## Testing

- Add tests for new features
- Ensure all tests pass before submitting a pull request

## Documentation

- Update the README.md if necessary
- Add comments to explain complex code sections
- Update docstrings for modified functions

Thank you for contributing to SiteShare!
