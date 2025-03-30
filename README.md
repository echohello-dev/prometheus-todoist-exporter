# Prometheus Todoist Exporter

Extract Todoist API metrics via Prometheus with this exporter.

## Features

- Collects metrics from the Todoist API using the [official Python client](https://github.com/Doist/todoist-api-python)
- Exposes these metrics in Prometheus format
- Provides comprehensive task, project, collaborator, section, and comment metrics
- Configurable through environment variables
- Includes Docker support for easy deployment
- Uses Poetry for dependency management
- Includes Taskfile for command orchestration
- Manages tool versions with asdf
- Uses Ruff for lightning-fast Python linting and formatting

## Metrics

The exporter provides the following metrics:

| Metric | Description | Labels |
|--------|-------------|--------|
| `todoist_tasks_total` | Total number of active tasks | project_name, project_id |
| `todoist_tasks_overdue` | Number of overdue tasks | project_name, project_id |
| `todoist_tasks_due_today` | Number of tasks due today | project_name, project_id |
| `todoist_tasks_completed` | Number of completed tasks (counter) | project_name, project_id |
| `todoist_project_collaborators` | Number of collaborators per project | project_name, project_id |
| `todoist_sections_total` | Number of sections per project | project_name, project_id |
| `todoist_comments_total` | Number of comments | project_name, project_id |
| `todoist_priority_tasks` | Number of tasks by priority | project_name, project_id, priority |
| `todoist_api_errors` | Number of API errors encountered | endpoint |
| `todoist_scrape_duration_seconds` | Time taken to collect Todoist metrics | - |

## Configuration

The exporter can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TODOIST_API_TOKEN` | Todoist API token (required) | - |
| `EXPORTER_PORT` | Port for the HTTP server | 9090 |
| `METRICS_PATH` | HTTP path for metrics | /metrics |
| `COLLECTION_INTERVAL` | Seconds between metric collections | 60 |

## Installation

### Using Docker

Pull the latest image from GitHub Container Registry:

```bash
docker pull ghcr.io/echohello-dev/prometheus-todoist-exporter:latest
```

Run the exporter:

```bash
docker run -p 9090:9090 -e TODOIST_API_TOKEN=your_api_token ghcr.io/echohello-dev/prometheus-todoist-exporter:latest
```

### Using Docker Compose

1. Copy the example environment file and edit it with your API token:

```bash
cp .env.example .env
# Edit .env with your Todoist API token
```

2. Then start the services:

```bash
docker-compose up -d
```

This will start both the Todoist exporter and a Prometheus instance configured to scrape metrics from the exporter.

### Using Poetry

1. Install Poetry (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install the package:
   ```bash
   poetry add prometheus-todoist-exporter
   ```

3. Set up your environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Todoist API token
   ```

4. Run the exporter:
   ```bash
   source .env && poetry run todoist-exporter
   ```

## Local Development

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/echohello-dev/prometheus-todoist-exporter.git
   cd prometheus-todoist-exporter
   ```

2. Set up development environment:
   ```bash
   task setup-dev
   ```
   
   This will:
   - Copy `.env.example` to `.env` (if it doesn't exist)
   - Install dependencies via Poetry

3. Edit the `.env` file with your Todoist API token:
   ```bash
   # Edit .env with your preferred editor
   nano .env
   ```

4. Run the exporter:
   ```bash
   source .env && task run
   ```

### Using asdf for tool version management

This project uses [asdf](https://asdf-vm.com/) to manage tool versions (Python, Poetry, Task).

1. Install asdf following the [installation instructions](https://asdf-vm.com/guide/getting-started.html).

2. Clone the repository:
   ```bash
   git clone https://github.com/echohello-dev/prometheus-todoist-exporter.git
   cd prometheus-todoist-exporter
   ```

3. Install the required tools with asdf:
   ```bash
   task setup
   ```
   
   This will install the correct versions of Python, Poetry, and Task as specified in `.tool-versions`, and set up your development environment.

4. Run the exporter:
   ```bash
   source .env && task run
   ```

5. Run tests:
   ```bash
   task test
   ```

## Using Taskfile

This project includes a Taskfile for easy command orchestration. You need to have [Task](https://taskfile.dev/installation/) installed, or you can use the version installed by asdf.

Available tasks:

```bash
# Set up local development environment (copy .env.example to .env and install deps)
task setup-dev

# Set up asdf with all required tools
task setup

# Install dependencies
task install

# Format the code with Ruff
task format

# Run linting with Ruff
task lint

# Run linting and fix issues with Ruff
task lint-fix

# Run tests
task test

# Run the exporter
task run

# Build Docker image
task docker-build

# Run Docker container
task docker-run

# Run all quality checks (format, lint, test)
task all

# Start services with docker-compose
task docker-compose-up

# Stop services with docker-compose
task docker-compose-down
```

## Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/echohello-dev/prometheus-todoist-exporter.git
   cd prometheus-todoist-exporter
   ```

2. Install tools and dependencies (requires asdf):
   ```bash
   task setup-asdf
   task install
   ```

3. Build the Docker image:
   ```bash
   task docker-build
   ```

## License

This project is licensed under the MIT License. 

## GitHub Workflow Setup

This repository uses GitHub Actions workflows for continuous integration, release management, and container publishing.

### Workflow Overview

1. **CI Workflow** (ci.yml)
   - Runs linting and tests for every push and pull request
   - Ensures code quality and functionality

2. **Release Please Workflow** (release-please.yml)
   - Automates versioning and release creation
   - Creates a PR with version bump and changelog updates
   - When merged, creates a GitHub release with appropriate tags

3. **PyPI Publish Workflow** (publish-pypi.yml)
   - Triggered when Release Please creates a new release
   - Builds and publishes the Python package to PyPI

4. **Docker Publish Workflow** (docker-publish.yml)
   - Builds and tests the Docker image
   - Publishes the image to GitHub Container Registry (ghcr.io)
   - Tags the image with:
     - Latest release version
     - Latest tag (for release only)
     - Branch name (for non-release builds)
     - Git SHA

### Required Secrets

To enable these workflows, ensure the following secrets are set in your repository:

1. For PyPI publishing:
   - `PYPI_API_TOKEN`: A PyPI API token with upload permissions

2. For Docker publishing:
   - GitHub Token with `packages:write` permission (automatic)

### Development to Production Workflow

1. **Local Development**
   - Set up local environment using:
     ```bash
     cp .env.example .env  # Add your Todoist API token
     task setup-dev  # Install dependencies
     ```
   - Make code changes and test locally with:
     ```bash
     source .env && task run
     ```

2. **Submit Changes**
   - Create a pull request with your changes
   - CI will run tests to ensure quality

3. **Release Process**
   - Release Please will automatically create a release PR when changes are merged to main
   - When the release PR is merged:
     - A GitHub release is created
     - The PyPI package is published
     - The Docker container is built and published to GHCR

4. **Using the Released Version**
   - Pull the latest container image:
     ```bash
     docker pull ghcr.io/echohello-dev/prometheus-todoist-exporter:latest
     ```
   - Or run with docker-compose:
     ```bash
     cp .env.example .env  # Add your Todoist API token
     docker-compose up -d
     ``` 