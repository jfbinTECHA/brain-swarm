# Developer Guide

Welcome to Brain-Swarm! This guide helps you get started with development and maintenance using our automated control panel.

## VSCode Tasks Control Panel

Brain-Swarm includes a comprehensive set of VSCode tasks for streamlined development workflows. Access them via `Ctrl+Shift+P` → `Run Task` → Select from the list below.

### Maintenance Tasks

- **🧹 Clean cache & backup files**: Removes `__pycache__`, `.pytest_cache`, database files, logs, and save files. Commits the cleanup.
- **🧱 Reorganize repository structure**: Ensures proper folder structure (docs/, infra/, tests/, .github/workflows/). Moves docker-compose.yml to infra/.
- **🧩 Set up CI & test scaffold**: Creates basic CI workflow and test placeholder if missing.

### Development Tasks

- **🏗️ Run Full Build**: Starts the swarm stack (`make up`), runs tests (`pytest`), then shuts down (`make down`). Validates end-to-end functionality.
- **🔒 Generate SBOM & Scan**: Creates Software Bill of Materials and security scan reports in `reports/` directory.
- **📖 Docs Preview**: Launches local documentation server (MkDocs or HTTP server) for previewing docs.

### Automation Tasks

- **🚀 Push & Tag v0.2-prep**: Pushes changes to main/master and creates the v0.2-prep tag for repository milestones.
- **🔍 Verify GitHub Actions pipeline status**: Checks the latest CI/CD run status via GitHub API.

### Full Routine

- **🧰 Full Cleanup Routine**: Runs all tasks sequentially for complete repository maintenance and validation.

## Makefile Targets

Use `make <target>` for common operations:

- `make up`: Start the Docker stack (Grafana, API, Prometheus)
- `make down`: Stop the stack
- `make status`: Check service health
- `make logs`: Follow service logs
- `make test`: Run pytest suite
- `make lint`: Lint with Ruff
- `make sbom`: Generate security scan
- `make metrics`: Display aggregated developer metrics (Redis, FastAPI, Prometheus)
- `make clean`: Rebuild containers with fresh state
- `make help`: Show all available targets

## GitHub Actions Workflows

Automated pipelines trigger on events:

- **CI** (`ci.yml`): Runs on push/PR - builds, lints, tests with Python 3.12
- **Docs** (`docs.yml`): Deploys documentation to GitHub Pages on version tags
- **Release** (`release.yml`): Generates CHANGELOG.md using conventional commits on tags

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Start development: `make up`
4. Run tests: `make test`
5. Use VSCode tasks for maintenance workflows
6. Commit with conventional format for automatic changelog generation

## Conventional Commits

Use these prefixes for automatic changelog categorization:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `perf:` - Performance improvements
- `refactor:` - Code restructuring
- `test:` - Testing
- `chore:` - Maintenance

Example: `git commit -m "feat: add user authentication"`

## Reports and Metrics

- Security reports: `reports/security.txt`, `reports/sbom.txt`
- Metrics: `make metrics` for live system stats
- CHANGELOG: Auto-generated in `CHANGELOG.md` on releases

This control panel ensures consistent, automated development workflows across the team.