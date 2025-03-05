# Contributing to ExtensityAI

First off, thank you for considering contributing to ExtensityAI! It's people like you that make ExtensityAI such a great company.

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

### Issues

We use GitHub issues to track public bugs and feature requests. Please ensure your description is clear and has sufficient instructions to be able to reproduce the issue.

### Coding Style

* We use Black for Python code formatting
* We use ESLint for TypeScript code formatting
* Please maintain consistent typing annotations in both Python and TypeScript

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ExtensityAI/PyFlow.ts.git
cd PyFlow.ts

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Testing

We use pytest for testing. Please write tests for new code you create:

```bash
pytest
```

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to making participation in our project and our community a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a professional setting

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
