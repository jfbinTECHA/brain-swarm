# Contributing to Cortex AI

Thank you for your interest in contributing to Cortex AI! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.12+ (for local development)

### Quick Start
```bash
# Clone the repository
git clone https://github.com/jfbinTECHA/brain-swarm.git
cd brain-swarm

# Start development environment
make up

# Run tests
make test

# Check code quality
make lint
```

## Development Workflow

### Branch Strategy
- `main`: Stable releases (protected branch)
- `develop`: Next version features
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `hotfix/*`: Emergency fixes

### Commit Messages
Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Requests
1. Create a feature branch from `develop`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Create a pull request to `develop`
7. Wait for CI checks to pass
8. Request review from maintainers

## Code Quality

### Python Standards
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions small and focused (single responsibility)

### Testing
- Write unit tests for all new functionality
- Aim for >90% code coverage
- Test both happy path and error conditions
- Use descriptive test names

### Linting and Formatting
```bash
# Run all quality checks
make lint

# Format code
ruff format .
```

## Documentation

### Code Documentation
- Use docstrings for all public APIs
- Keep comments up-to-date with code changes
- Document complex algorithms and design decisions

### User Documentation
- Update README.md for user-facing changes
- Add examples for new features
- Update API documentation

## Security

### Best Practices
- Never commit secrets or sensitive data
- Use environment variables for configuration
- Validate all inputs
- Follow principle of least privilege

### Reporting Security Issues
Please report security vulnerabilities by emailing security@brainswarm.ai (placeholder) instead of creating public issues.

## Community

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn and contribute
- Maintain professional communication

### Getting Help
- Check existing issues and documentation first
- Use GitHub Discussions for questions
- Join our community chat (when available)

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- GitHub repository contributors list
- Project documentation

Thank you for contributing to Cortex AI! 🚀