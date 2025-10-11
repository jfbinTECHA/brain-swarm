# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup and documentation

## [0.1.0] - 2025-10-11

### Added
- **Core Infrastructure**: Complete Docker Compose stack with FastAPI, Redis, DuckDB, Prometheus, and Grafana
- **API Layer**: FastAPI backend with health checks and Prometheus metrics instrumentation
- **Monitoring**: Grafana dashboards with pre-configured datasources for system monitoring
- **Data Layer**: Redis for caching/sessions, DuckDB for analytical queries
- **Development Tools**: Makefile with common commands, comprehensive test suite
- **CI/CD Pipeline**: GitHub Actions workflows for linting, testing, building, and releasing
- **Security**: Environment variable configuration, .gitignore patterns, pre-commit hooks
- **Documentation**: README, architecture docs, roadmap, and demo script
- **Container Registry**: Automated Docker image building and pushing to GHCR

### Changed
- Repository restructured with clean separation of concerns (backend/, infra/, docs/, tests/)
- Improved developer workflow with linting, formatting, and security scanning

### Technical Details
- **FastAPI**: REST API with automatic OpenAPI documentation
- **Prometheus**: Metrics collection with custom instrumentation
- **Grafana**: Visualization with auto-provisioned dashboards
- **Redis**: In-memory data store with persistence
- **DuckDB**: Embedded analytical database
- **Docker**: Multi-service containerized deployment
- **Python**: Type-safe backend with comprehensive testing

### Security
- No sensitive data committed to repository
- Environment variable configuration for secrets
- Security scanning with Trivy and Bandit
- Pre-commit hooks for code quality

### Documentation
- Comprehensive README with quick start guide
- Architecture documentation with system diagrams
- Development roadmap and contribution guidelines
- Demo script for showcasing functionality

---

## Types of changes
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities

## Versioning
This project uses [Semantic Versioning](https://semver.org/).

Given a version number MAJOR.MINOR.PATCH, increment the:

- MAJOR version when you make incompatible API changes
- MINOR version when you add functionality in a backwards compatible manner
- PATCH version when you make backwards compatible bug fixes

Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.