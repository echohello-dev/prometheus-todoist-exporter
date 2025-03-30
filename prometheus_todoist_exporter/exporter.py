import os
import time
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

import requests
from prometheus_client import Counter, Gauge, start_http_server
from todoist_api_python.api import TodoistAPI

# Configuration from environment variables
TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
EXPORTER_PORT = int(os.environ.get("EXPORTER_PORT", "9090"))
METRICS_PATH = os.environ.get("METRICS_PATH", "/metrics")
COLLECTION_INTERVAL = int(os.environ.get("COLLECTION_INTERVAL", "60"))
COMPLETED_TASKS_DAYS = int(os.environ.get("COMPLETED_TASKS_DAYS", "7"))
COMPLETED_TASKS_HOURS = int(os.environ.get("COMPLETED_TASKS_HOURS", "24"))

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
# New metrics for completed tasks in time spans (these will be manually tracked)
TODOIST_TASKS_COMPLETED_TODAY = Gauge(
    "todoist_tasks_completed_today",
    "Number of tasks completed today (estimated)",
    ["project_name", "project_id"],
)
TODOIST_TASKS_COMPLETED_WEEK = Gauge(
    "todoist_tasks_completed_week",
    "Number of tasks completed in the last N days (estimated)",
    ["project_name", "project_id", "days"],
)
TODOIST_TASKS_COMPLETED_HOURS = Gauge(
    "todoist_tasks_completed_hours",
    "Number of tasks completed in the last N hours (estimated)",
    ["project_name", "project_id", "hours"],
)
# New metrics for section-specific tasks
TODOIST_SECTION_TASKS = Gauge(
    "todoist_section_tasks",
    "Number of tasks in a section",
    ["project_name", "project_id", "section_name", "section_id"],
)
# New metrics for labels
TODOIST_LABEL_TASKS = Gauge(
    "todoist_label_tasks",
    "Number of tasks with a specific label",
    ["label_name"],
)
# New metric for tasks with due dates
TODOIST_TASKS_WITH_DUE_DATE = Gauge(
    "todoist_tasks_with_due_date",
    "Number of tasks with a due date",
    ["project_name", "project_id"],
)
# New metric for recurring tasks
TODOIST_RECURRING_TASKS = Gauge(
    "todoist_recurring_tasks",
    "Number of recurring tasks",
    ["project_name", "project_id"],
)
# New metric for task activity
TODOIST_SYNC_API_COMPLETED_TASKS = Gauge(
    "todoist_sync_api_completed_tasks",
    "Number of tasks completed via Sync API",
    ["project_name", "project_id", "timeframe"],
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


def collect_completed_tasks_sync_api(projects_dict: dict[str, dict[str, Any]]) -> None:
    """
    Collect completed tasks using the Sync API directly.

    The REST API does not support completed tasks, so we use the Sync API directly.
    """
    if not TODOIST_API_TOKEN:
        return

    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    week_start = today_start - timedelta(days=COMPLETED_TASKS_DAYS)
    hours_start = now - timedelta(hours=COMPLETED_TASKS_HOURS)

    # Format dates for API calls
    since_timestamps = {
        "today": today_start.strftime("%Y-%m-%dT%H:%M:%S"),
        f"{COMPLETED_TASKS_DAYS}_days": week_start.strftime("%Y-%m-%dT%H:%M:%S"),
        f"{COMPLETED_TASKS_HOURS}_hours": hours_start.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Initialize counters for each project and timeframe
    completed_counts = {
        project_id: dict.fromkeys(since_timestamps.keys(), 0)
        for project_id in projects_dict
    }

    # Map project name to ID for quick lookup
    project_names = {
        project_id: data["name"] for project_id, data in projects_dict.items()
    }

    try:
        # Use Sync API directly since REST API doesn't support completed tasks
        for timeframe, since in since_timestamps.items():
            params = {
                "since": since,
                "limit": 200,  # Maximum allowed by the API
            }

            response = requests.post(
                "https://api.todoist.com/sync/v9/completed/get_all",
                headers={"Authorization": f"Bearer {TODOIST_API_TOKEN}"},
                json=params,
                timeout=60,
            )

            if response.status_code == HTTPStatus.OK:
                completed_data = response.json()
                for item in completed_data.get("items", []):
                    project_id = item.get("project_id")
                    if project_id and project_id in completed_counts:
                        completed_counts[project_id][timeframe] += 1
            else:
                print(
                    f"Error fetching completed tasks from Sync API: "
                    f"{response.status_code}"
                )
                TODOIST_API_ERRORS.labels(endpoint="sync_completed_tasks").inc()

        # Set metrics for each project and timeframe
        for project_id, timeframes in completed_counts.items():
            project_name = project_names.get(project_id, "unknown")
            for timeframe, count in timeframes.items():
                TODOIST_SYNC_API_COMPLETED_TASKS.labels(
                    project_name=project_name,
                    project_id=project_id,
                    timeframe=timeframe,
                ).set(count)

                # Also update the traditional metrics for backward compatibility
                if timeframe == "today":
                    TODOIST_TASKS_COMPLETED_TODAY.labels(
                        project_name=project_name, project_id=project_id
                    ).set(count)
                elif timeframe == f"{COMPLETED_TASKS_DAYS}_days":
                    TODOIST_TASKS_COMPLETED_WEEK.labels(
                        project_name=project_name,
                        project_id=project_id,
                        days=str(COMPLETED_TASKS_DAYS),
                    ).set(count)
                elif timeframe == f"{COMPLETED_TASKS_HOURS}_hours":
                    TODOIST_TASKS_COMPLETED_HOURS.labels(
                        project_name=project_name,
                        project_id=project_id,
                        hours=str(COMPLETED_TASKS_HOURS),
                    ).set(count)

    except Exception as error:
        print(f"Error fetching completed tasks from Sync API: {error}")
        TODOIST_API_ERRORS.labels(endpoint="sync_completed_tasks").inc()


def collect_label_metrics() -> None:
    """Collect metrics for tasks with labels."""
    try:
        # Reset metrics
        TODOIST_LABEL_TASKS.clear()

        # Get all tasks
        tasks = api.get_tasks()

        # Count tasks per label
        label_counts = {}
        for task in tasks:
            for label in task.labels:
                if label not in label_counts:
                    label_counts[label] = 0
                label_counts[label] += 1

        # Set metrics for each label
        for label, count in label_counts.items():
            TODOIST_LABEL_TASKS.labels(label_name=label).set(count)

    except Exception as error:
        print(f"Error collecting label metrics: {error}")
        TODOIST_API_ERRORS.labels(endpoint="get_label_metrics").inc()


def collect_section_tasks(projects_dict: dict[str, dict[str, Any]]) -> None:
    """Collect metrics for tasks in each section."""
    try:
        # Reset metrics
        TODOIST_SECTION_TASKS.clear()

        # Get all tasks
        tasks = api.get_tasks()

        # Build section lookup dict
        sections_by_id = {}
        for project_id, project_data in projects_dict.items():
            for section in project_data["sections"]:
                sections_by_id[section.id] = {
                    "project_id": project_id,
                    "project_name": project_data["name"],
                    "section_name": section.name,
                }

        # Count tasks per section
        section_counts = {}
        for task in tasks:
            if task.section_id and task.section_id in sections_by_id:
                if task.section_id not in section_counts:
                    section_counts[task.section_id] = 0
                section_counts[task.section_id] += 1

        # Set metrics for each section
        for section_id, count in section_counts.items():
            section_info = sections_by_id[section_id]
            TODOIST_SECTION_TASKS.labels(
                project_name=section_info["project_name"],
                project_id=section_info["project_id"],
                section_name=section_info["section_name"],
                section_id=section_id,
            ).set(count)

    except Exception as error:
        print(f"Error collecting section task metrics: {error}")
        TODOIST_API_ERRORS.labels(endpoint="get_section_tasks").inc()


def collect_metrics() -> None:
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
        TODOIST_TASKS_COMPLETED_TODAY.clear()
        TODOIST_TASKS_COMPLETED_WEEK.clear()
        TODOIST_TASKS_COMPLETED_HOURS.clear()
        TODOIST_TASKS_WITH_DUE_DATE.clear()
        TODOIST_RECURRING_TASKS.clear()
        TODOIST_SYNC_API_COMPLETED_TASKS.clear()

        # Collect data from Todoist API
        projects_dict = collect_projects()
        if not projects_dict:
            return

        collect_tasks(projects_dict)
        collect_collaborators(projects_dict)
        collect_sections(projects_dict)
        collect_comments(projects_dict)
        collect_completed_tasks_sync_api(projects_dict)
        collect_label_metrics()
        collect_section_tasks(projects_dict)

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
            with_due_date_count = 0
            recurring_count = 0

            for task in tasks:
                # Count by priority
                priority = task.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1

                # Check for tasks with due dates
                if task.due:
                    with_due_date_count += 1

                    # Check for recurring tasks
                    if task.due.is_recurring:
                        recurring_count += 1

                    # Check for overdue tasks
                    if task.due.date and task.due.date < today:
                        overdue_count += 1

                    # Check for tasks due today
                    if task.due.date and task.due.date == today:
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

            # Set due date and recurring task metrics
            TODOIST_TASKS_WITH_DUE_DATE.labels(
                project_name=project_name, project_id=project_id
            ).set(with_due_date_count)

            TODOIST_RECURRING_TASKS.labels(
                project_name=project_name, project_id=project_id
            ).set(recurring_count)


def main() -> None:
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
