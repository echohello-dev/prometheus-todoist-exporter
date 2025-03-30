import os
import time
from datetime import UTC, datetime
from typing import Any

from prometheus_client import Counter, Gauge, start_http_server
from todoist_api_python.api import TodoistAPI

# Configuration from environment variables
TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", "9090"))
METRICS_PATH = os.environ.get("METRICS_PATH", "/metrics")
COLLECTION_INTERVAL = int(os.environ.get("COLLECTION_INTERVAL", "60"))

# Initialize the Todoist API client
api = TodoistAPI(TODOIST_API_TOKEN) if TODOIST_API_TOKEN else None

# Define metrics
TODOIST_TASKS_TOTAL = Gauge(
    "todoist_tasks_total",
    "Total number of active tasks",
    ["project_name", "project_id"],
)
TODOIST_TASKS_OVERDUE = Gauge(
    "todoist_tasks_overdue", "Number of overdue tasks", ["project_name", "project_id"]
)
TODOIST_TASKS_DUE_TODAY = Gauge(
    "todoist_tasks_due_today",
    "Number of tasks due today",
    ["project_name", "project_id"],
)
TODOIST_TASKS_COMPLETED = Counter(
    "todoist_tasks_completed",
    "Number of completed tasks",
    ["project_name", "project_id"],
)
TODOIST_PROJECT_COLLABORATORS = Gauge(
    "todoist_project_collaborators",
    "Number of collaborators per project",
    ["project_name", "project_id"],
)
TODOIST_SECTIONS_TOTAL = Gauge(
    "todoist_sections_total",
    "Number of sections per project",
    ["project_name", "project_id"],
)
TODOIST_COMMENTS_TOTAL = Gauge(
    "todoist_comments_total",
    "Number of comments",
    ["project_name", "project_id"],
)
TODOIST_PRIORITY_TASKS = Gauge(
    "todoist_priority_tasks",
    "Number of tasks by priority",
    ["project_name", "project_id", "priority"],
)
TODOIST_API_ERRORS = Counter(
    "todoist_api_errors", "Number of API errors encountered", ["endpoint"]
)
TODOIST_SCRAPE_DURATION = Gauge(
    "todoist_scrape_duration_seconds", "Time taken to collect Todoist metrics"
)


def collect_projects() -> dict[str, dict[str, Any]]:
    """Collect projects and return a dict mapping project_id to project details."""
    projects_dict = {}
    try:
        projects = api.get_projects()
        for project in projects:
            projects_dict[project.id] = {
                "id": project.id,
                "name": project.name,
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            }
    except Exception as error:
        print(f"Error fetching projects: {error}")
        TODOIST_API_ERRORS.labels(endpoint="get_projects").inc()
    return projects_dict


def collect_tasks(projects_dict: dict[str, dict[str, Any]]) -> None:
    """Collect tasks and organize them by project."""
    try:
        tasks = api.get_tasks()
        for task in tasks:
            project_id = task.project_id
            if project_id in projects_dict:
                projects_dict[project_id]["tasks"].append(task)
    except Exception as error:
        print(f"Error fetching tasks: {error}")
        TODOIST_API_ERRORS.labels(endpoint="get_tasks").inc()


def collect_collaborators(projects_dict: dict[str, dict[str, Any]]) -> None:
    """Collect collaborators for each project."""
    for project_id, project_data in projects_dict.items():
        try:
            collaborators = api.get_collaborators(project_id=project_id)
            project_data["collaborators"] = collaborators
        except Exception as error:
            print(f"Error fetching collaborators for project {project_id}: {error}")
            TODOIST_API_ERRORS.labels(endpoint="get_collaborators").inc()


def collect_sections(projects_dict: dict[str, dict[str, Any]]) -> None:
    """Collect sections for each project."""
    try:
        all_sections = api.get_sections()
        for section in all_sections:
            project_id = section.project_id
            if project_id in projects_dict:
                projects_dict[project_id]["sections"].append(section)
    except Exception as error:
        print(f"Error fetching sections: {error}")
        TODOIST_API_ERRORS.labels(endpoint="get_sections").inc()


def collect_comments(projects_dict: dict[str, dict[str, Any]]) -> None:
    """Collect comments for each project."""
    for project_id, project_data in projects_dict.items():
        try:
            project_comments = api.get_comments(project_id=project_id)
            project_data["comments"] = project_comments
        except Exception as error:
            print(f"Error fetching comments for project {project_id}: {error}")
            TODOIST_API_ERRORS.labels(endpoint="get_comments").inc()


def collect_metrics():
    """Collect and expose all Todoist metrics."""
    with TODOIST_SCRAPE_DURATION.time():
        if not api:
            print("Error: No Todoist API token provided")
            return

        # Reset metrics
        TODOIST_TASKS_TOTAL.clear()
        TODOIST_TASKS_OVERDUE.clear()
        TODOIST_TASKS_DUE_TODAY.clear()
        TODOIST_PROJECT_COLLABORATORS.clear()
        TODOIST_SECTIONS_TOTAL.clear()
        TODOIST_COMMENTS_TOTAL.clear()
        TODOIST_PRIORITY_TASKS.clear()
        # Collect data from Todoist API
        projects_dict = collect_projects()
        if not projects_dict:
            return

        collect_tasks(projects_dict)
        collect_collaborators(projects_dict)
        collect_sections(projects_dict)
        collect_comments(projects_dict)

        # Calculate metrics from collected data
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        for project_id, project_data in projects_dict.items():
            project_name = project_data["name"]

            # Task metrics
            tasks = project_data["tasks"]
            TODOIST_TASKS_TOTAL.labels(
                project_name=project_name, project_id=project_id
            ).set(len(tasks))

            # Priority metrics
            priority_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            overdue_count = 0
            due_today_count = 0

            for task in tasks:
                # Count by priority
                priority = task.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Check for overdue tasks
                if task.due and task.due.date and task.due.date < today:
                    overdue_count += 1

                # Check for tasks due today
                if task.due and task.due.date and task.due.date == today:
                    due_today_count += 1

            # Set priority metrics
            for priority, count in priority_counts.items():
                TODOIST_PRIORITY_TASKS.labels(
                    project_name=project_name,
                    project_id=project_id,
                    priority=str(priority),
                ).set(count)

            # Set other metrics
            TODOIST_TASKS_OVERDUE.labels(
                project_name=project_name, project_id=project_id
            ).set(overdue_count)

            TODOIST_TASKS_DUE_TODAY.labels(
                project_name=project_name, project_id=project_id
            ).set(due_today_count)

            TODOIST_PROJECT_COLLABORATORS.labels(
                project_name=project_name, project_id=project_id
            ).set(len(project_data["collaborators"]))

            TODOIST_SECTIONS_TOTAL.labels(
                project_name=project_name, project_id=project_id
            ).set(len(project_data["sections"]))

            TODOIST_COMMENTS_TOTAL.labels(
                project_name=project_name, project_id=project_id
            ).set(len(project_data["comments"]))


def main():
    """Main function to run the exporter."""
    # Start up the server to expose the metrics.
    start_http_server(EXPORTER_PORT)
    print(
        f"Todoist Prometheus exporter started on port {EXPORTER_PORT} "
        f"with metrics at {METRICS_PATH}"
    )

    if not TODOIST_API_TOKEN:
        print(
            "Warning: TODOIST_API_TOKEN environment variable is not set. "
            "Exporter will not collect metrics."
        )

    # Collect metrics on a schedule
    while True:
        collect_metrics()
        print(f"Metrics collected. Next collection in {COLLECTION_INTERVAL} seconds.")
        time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
    main()
