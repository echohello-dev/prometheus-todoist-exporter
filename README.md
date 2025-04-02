![](./docs/images/todoist.webp)

# Prometheus Todoist Exporter

Extract Todoist API metrics via Prometheus with this exporter.

> [!IMPORTANT]
> This project is not affiliated with Todoist. It is a community-driven project.

![](docs/images/todoist-grafana.jpeg)

## Features

- Collects metrics from the Todoist API using the [official Python client](https://github.com/Doist/todoist-api-python)
- Exposes these metrics in Prometheus format
- Provides comprehensive task, project, collaborator, section, and comment metrics
- Tracks completed tasks through the Todoist Sync API
- Monitors tasks by labels, sections, and due dates
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
| `todoist_tasks_completed_today` | Number of tasks completed today | project_name, project_id |
| `todoist_tasks_completed_week` | Number of tasks completed in the last N days | project_name, project_id, days |
| `todoist_tasks_completed_hours` | Number of tasks completed in the last N hours | project_name, project_id, hours |
| `todoist_section_tasks` | Number of tasks in a section | project_name, project_id, section_name, section_id |
| `todoist_label_tasks` | Number of tasks with a specific label | label_name |
| `todoist_tasks_with_due_date` | Number of tasks with a due date | project_name, project_id |
| `todoist_recurring_tasks` | Number of recurring tasks | project_name, project_id |
| `todoist_sync_api_completed_tasks` | Number of tasks completed via Sync API | project_name, project_id, timeframe |

## Grafana Dashboard

This project includes a pre-configured Grafana dashboard to visualize the exported metrics. You can find the dashboard definition in `grafana/dashboard.json`.

To import the dashboard into your Grafana instance:

1.  Navigate to your Grafana UI.
2.  Go to `Dashboards` -> `Browse`.
3.  Click the `Import` button (usually in the top right).
4.  Click `Upload JSON file` and select the `grafana/dashboard.json` file from this repository.
5.  Alternatively, you can paste the JSON content directly into the text area.
6.  Configure the dashboard options, such as selecting your Prometheus data source.
7.  Click `Import`.

This dashboard provides panels for visualizing active tasks, completion trends, task breakdowns by project/priority/label, and exporter health metrics.

## Configuration

The exporter can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TODOIST_API_TOKEN` | Todoist API token (required) | - |
| `EXPORTER_PORT` | Port for the HTTP server | 9090 |
| `METRICS_PATH` | HTTP path for metrics | /metrics |
| `COLLECTION_INTERVAL` | Seconds between metric collections | 60 |
| `COMPLETED_TASKS_DAYS` | Number of days to look back for completed tasks | 7 |
| `COMPLETED_TASKS_HOURS` | Number of hours to look back for completed tasks | 24 |

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

### Using Kubernetes

Kubernetes manifests are provided in the `deploy/kubernetes` directory. These can be applied directly or deployed with Kustomize.

1. Create the namespace:
   ```bash
   kubectl create namespace monitoring
   ```

2. Create a Secret with your Todoist API token:
   ```bash
   TODOIST_API_TOKEN_B64=$(echo -n 'your-todoist-api-token' | base64)
   sed "s/<BASE64_ENCODED_API_TOKEN>/$TODOIST_API_TOKEN_B64/" deploy/kubernetes/secret.yaml | kubectl apply -f -
   ```

   Or create the Secret manually:
   ```bash
   kubectl create secret generic todoist-secret -n monitoring --from-literal=api-token=your-todoist-api-token
   ```

3. Deploy with Kustomize:
   ```bash
   kubectl apply -k deploy/kubernetes
   ```

4. To access the metrics endpoint:
   ```bash
   kubectl port-forward -n monitoring service/prometheus-todoist-exporter 9090:9090
   ```

5. View the metrics at http://localhost:9090/metrics

### Using Helm

A Helm chart is available in the `deploy/helm/prometheus-todoist-exporter` directory.

1. Deploy the chart:
   ```bash
   helm install todoist-exporter ./deploy/helm/prometheus-todoist-exporter \
     --namespace monitoring --create-namespace \
     --set todoist.apiToken="your-todoist-api-token"
   ```

2. Configure with custom values:
   ```bash
   helm install todoist-exporter ./deploy/helm/prometheus-todoist-exporter \
     --namespace monitoring --create-namespace \
     --set todoist.apiToken="your-todoist-api-token" \
     --set exporter.collectionInterval=30 \
     --set service.type=NodePort
   ```

3. Using a custom values file:
   ```bash
   # Create a values.yaml file with your custom configuration
   cat > my-values.yaml << EOF
   todoist:
     apiToken: "your-todoist-api-token"
   exporter:
     collectionInterval: 30
   serviceMonitor:
     enabled: true
   EOF

   # Install with custom values
   helm install todoist-exporter ./deploy/helm/prometheus-todoist-exporter \
     --namespace monitoring --create-namespace \
     --values my-values.yaml
   ```

4. To upgrade the deployment:
   ```bash
   helm upgrade todoist-exporter ./deploy/helm/prometheus-todoist-exporter \
     --namespace monitoring \
     --reuse-values \
     --set exporter.completedTasksDays=14
   ```

5. To uninstall:
   ```bash
   helm uninstall todoist-exporter --namespace monitoring
   ```

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
   - Install pre-commit hooks

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

## Pre-commit Hooks

This project uses pre-commit to enforce code quality and standards. The hooks ensure that all code commits meet the project's requirements.

To install the pre-commit hooks:

```bash
task pre-commit-install
```

To manually run the pre-commit checks:

```bash
task pre-commit-run
```

The following checks are included:
- Code formatting with Ruff
- Linting with Ruff
- Basic file checks (trailing whitespace, YAML validation, etc.)
- Poetry configuration verification
- Running tests

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

# Install pre-commit hooks
task pre-commit-install

# Run pre-commit checks on all files
task pre-commit-run

# Update pre-commit hooks to latest versions
task pre-commit-update

# Build Docker image
task docker-build

# Run Docker container
task docker-run

# Start services with docker-compose
task docker-compose-up

# Stop services with docker-compose
task docker-compose-down

# Deploy to Kubernetes with kustomize
task k8s-deploy

# Delete Kubernetes deployment
task k8s-delete

# Deploy with Helm
task helm-deploy

# Delete Helm deployment
task helm-delete

# Lint Helm chart
task helm-lint

# Generate Kubernetes manifests from Helm chart
task helm-template

# Run all quality checks (format, lint, test)
task all
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
   - `POETRY_PYPI_TOKEN_PYPI`: A PyPI API token with upload permissions

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

## Helm Chart Management

The project includes a Helm chart in the `deploy/helm/prometheus-todoist-exporter` directory. When making changes to the Helm chart, follow these guidelines:

### Chart Versioning

1. The Helm chart follows semantic versioning (`major.minor.patch`)
2. Chart version is specified in `deploy/helm/prometheus-todoist-exporter/Chart.yaml`
3. When updating the chart:
   - For non-breaking changes, increment the patch version
   - For new features (non-breaking), increment the minor version
   - For breaking changes, increment the major version

### Testing Chart Changes

Before committing chart changes:

1. Lint the chart:
   ```bash
   task helm-lint
   ```

2. Test template rendering:
   ```bash
   task helm-template
   ```

3. Test installation in a dev environment:
   ```bash
   task helm-deploy
   ```

### Chart Documentation

Keep the chart documentation in `deploy/helm/prometheus-todoist-exporter/README.md` synchronized with any changes to:
- Chart parameters and defaults
- Required Kubernetes versions
- Examples

### Release Process

When a new version of the exporter is released, the chart's `appVersion` should be updated to match the released version.
