import unittest
from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from prometheus_client import REGISTRY

from prometheus_todoist_exporter import exporter

# Constants for tests
# Using a placeholder value for testing, not a real token
TEST_API_TOKEN = "test_token"  # noqa: S105
EXPECTED_API_CALLS = 3
EXPECTED_TASK_COUNT_WORK = 2
EXPECTED_TASK_COUNT_URGENT = 2
EXPECTED_TASK_COUNT_PERSONAL = 1
EXPECTED_SECTION1_TASKS = 2
EXPECTED_SECTION2_TASKS = 1
EXPECTED_TASKS_WITH_DUE_DATE = 1
EXPECTED_RECURRING_TASKS = 1
EXPECTED_OVERDUE_TASKS = 0


class TestTodoistExporter(unittest.TestCase):
    def setUp(self):
        # Reset metrics before each test
        for metric in list(REGISTRY._names_to_collectors.values()):
            try:  # noqa: SIM105
                REGISTRY.unregister(metric)
            except KeyError:
                # Skip metrics that aren't properly registered
                pass

        # Re-register metrics
        self.tasks_total = exporter.TODOIST_TASKS_TOTAL
        self.tasks_overdue = exporter.TODOIST_TASKS_OVERDUE
        self.tasks_due_today = exporter.TODOIST_TASKS_DUE_TODAY
        self.project_collaborators = exporter.TODOIST_PROJECT_COLLABORATORS
        self.sections_total = exporter.TODOIST_SECTIONS_TOTAL
        self.comments_total = exporter.TODOIST_COMMENTS_TOTAL
        self.priority_tasks = exporter.TODOIST_PRIORITY_TASKS
        self.api_errors = exporter.TODOIST_API_ERRORS
        self.scrape_duration = exporter.TODOIST_SCRAPE_DURATION
        # Register new metrics
        self.tasks_completed_today = exporter.TODOIST_TASKS_COMPLETED_TODAY
        self.tasks_completed_week = exporter.TODOIST_TASKS_COMPLETED_WEEK
        self.tasks_completed_hours = exporter.TODOIST_TASKS_COMPLETED_HOURS
        self.section_tasks = exporter.TODOIST_SECTION_TASKS
        self.label_tasks = exporter.TODOIST_LABEL_TASKS
        self.tasks_with_due_date = exporter.TODOIST_TASKS_WITH_DUE_DATE
        self.recurring_tasks = exporter.TODOIST_RECURRING_TASKS
        self.sync_api_completed_tasks = exporter.TODOIST_SYNC_API_COMPLETED_TASKS

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_projects(self, mock_api):
        # Mock data
        mock_project = MagicMock()
        mock_project.id = "123456"
        mock_project.name = "Test Project"
        mock_api.get_projects.return_value = [mock_project]

        # Test function
        result = exporter.collect_projects()

        # Verify results
        assert len(result) == 1
        assert result["123456"]["name"] == "Test Project"
        mock_api.get_projects.assert_called_once()

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_projects_with_error(self, mock_api):
        # Mock error
        mock_api.get_projects.side_effect = Exception("API Error")

        # Test function
        result = exporter.collect_projects()

        # Verify results
        assert len(result) == 0
        mock_api.get_projects.assert_called_once()
        assert self.api_errors.labels(endpoint="get_projects")._value.get() == 1

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_tasks(self, mock_api):
        # Mock data
        mock_task = MagicMock()
        mock_task.id = "789"
        mock_task.project_id = "123456"
        mock_task.priority = 4
        mock_task.due = MagicMock()
        mock_task.due.date = datetime.now(UTC).strftime("%Y-%m-%d")

        mock_api.get_tasks.return_value = [mock_task]

        # Test data
        projects_dict = {
            "123456": {
                "id": "123456",
                "name": "Test Project",
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            }
        }

        # Test function
        exporter.collect_tasks(projects_dict)

        # Verify results
        assert len(projects_dict["123456"]["tasks"]) == 1
        assert projects_dict["123456"]["tasks"][0].id == "789"
        mock_api.get_tasks.assert_called_once()

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_tasks_with_error(self, mock_api):
        # Mock error
        mock_api.get_tasks.side_effect = Exception("API Error")

        # Test data
        projects_dict = {
            "123456": {
                "id": "123456",
                "name": "Test Project",
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            }
        }

        # Test function
        exporter.collect_tasks(projects_dict)

        # Verify results
        assert len(projects_dict["123456"]["tasks"]) == 0
        mock_api.get_tasks.assert_called_once()
        assert self.api_errors.labels(endpoint="get_tasks")._value.get() == 1

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_collaborators(self, mock_api):
        # Mock data
        mock_collaborator = MagicMock()
        mock_collaborator.id = "user1"
        mock_collaborator.name = "User One"

        mock_api.get_collaborators.return_value = [mock_collaborator]

        # Test data
        projects_dict = {
            "123456": {
                "id": "123456",
                "name": "Test Project",
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            }
        }

        # Test function
        exporter.collect_collaborators(projects_dict)

        # Verify results
        assert len(projects_dict["123456"]["collaborators"]) == 1
        mock_api.get_collaborators.assert_called_once_with(project_id="123456")

    @patch("prometheus_todoist_exporter.exporter.requests.post")
    def test_collect_completed_tasks_sync_api(self, mock_post):
        # Mock the requests response
        mock_response = MagicMock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.return_value = {
            "items": [
                {"project_id": "123456", "completed_at": datetime.now(UTC).isoformat()},
                {"project_id": "123456", "completed_at": datetime.now(UTC).isoformat()},
                {"project_id": "789012", "completed_at": datetime.now(UTC).isoformat()},
            ]
        }
        mock_post.return_value = mock_response

        # Test data
        projects_dict = {
            "123456": {
                "id": "123456",
                "name": "Test Project",
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            },
            "789012": {
                "id": "789012",
                "name": "Another Project",
                "tasks": [],
                "collaborators": [],
                "sections": [],
                "comments": [],
            },
        }

        # Set API token for test
        original_token = exporter.TODOIST_API_TOKEN
        exporter.TODOIST_API_TOKEN = TEST_API_TOKEN

        try:
            # Test function
            exporter.collect_completed_tasks_sync_api(projects_dict)

            # Verify results for today, last N days, and last N hours
            assert mock_post.call_count == EXPECTED_API_CALLS

            # Check that metrics were set
            assert (
                self.sync_api_completed_tasks.labels(
                    project_name="Test Project", project_id="123456", timeframe="today"
                )._value.get()
                == EXPECTED_TASK_COUNT_WORK
            )

            assert (
                self.sync_api_completed_tasks.labels(
                    project_name="Another Project",
                    project_id="789012",
                    timeframe="today",
                )._value.get()
                == 1
            )
        finally:
            # Restore original token
            exporter.TODOIST_API_TOKEN = original_token

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_label_metrics(self, mock_api):
        # Mock data
        mock_task1 = MagicMock()
        mock_task1.labels = ["work", "urgent"]

        mock_task2 = MagicMock()
        mock_task2.labels = ["personal", "urgent"]

        mock_task3 = MagicMock()
        mock_task3.labels = ["work"]

        mock_api.get_tasks.return_value = [mock_task1, mock_task2, mock_task3]

        # Test function
        exporter.collect_label_metrics()

        # Verify results
        assert (
            self.label_tasks.labels(label_name="work")._value.get()
            == EXPECTED_TASK_COUNT_WORK
        )
        assert (
            self.label_tasks.labels(label_name="urgent")._value.get()
            == EXPECTED_TASK_COUNT_URGENT
        )
        assert (
            self.label_tasks.labels(label_name="personal")._value.get()
            == EXPECTED_TASK_COUNT_PERSONAL
        )

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_section_tasks(self, mock_api):
        # Mock section data
        mock_section1 = MagicMock()
        mock_section1.id = "section1"
        mock_section1.name = "To Do"
        mock_section1.project_id = "123456"

        mock_section2 = MagicMock()
        mock_section2.id = "section2"
        mock_section2.name = "In Progress"
        mock_section2.project_id = "123456"

        # Mock task data
        mock_task1 = MagicMock()
        mock_task1.section_id = "section1"

        mock_task2 = MagicMock()
        mock_task2.section_id = "section1"

        mock_task3 = MagicMock()
        mock_task3.section_id = "section2"

        mock_task4 = MagicMock()
        mock_task4.section_id = None

        mock_api.get_tasks.return_value = [
            mock_task1,
            mock_task2,
            mock_task3,
            mock_task4,
        ]

        # Test data
        projects_dict = {
            "123456": {
                "id": "123456",
                "name": "Test Project",
                "tasks": [],
                "collaborators": [],
                "sections": [mock_section1, mock_section2],
                "comments": [],
            }
        }

        # Test function
        exporter.collect_section_tasks(projects_dict)

        # Verify results
        assert (
            self.section_tasks.labels(
                project_name="Test Project",
                project_id="123456",
                section_name="To Do",
                section_id="section1",
            )._value.get()
            == EXPECTED_SECTION1_TASKS
        )

        assert (
            self.section_tasks.labels(
                project_name="Test Project",
                project_id="123456",
                section_name="In Progress",
                section_id="section2",
            )._value.get()
            == EXPECTED_SECTION2_TASKS
        )

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_metrics_complete(self, mock_api):
        # Mock projects
        mock_project = MagicMock()
        mock_project.id = "123456"
        mock_project.name = "Test Project"
        mock_api.get_projects.return_value = [mock_project]

        # Mock tasks
        mock_task = MagicMock()
        mock_task.id = "789"
        mock_task.project_id = "123456"
        mock_task.priority = 4
        mock_task.labels = ["work", "urgent"]
        mock_task.due = MagicMock()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        mock_task.due.date = today
        mock_task.due.is_recurring = True
        mock_task.section_id = "section1"

        mock_api.get_tasks.return_value = [mock_task]

        # Mock collaborators
        mock_collaborator = MagicMock()
        mock_api.get_collaborators.return_value = [mock_collaborator, mock_collaborator]

        # Mock sections
        mock_section = MagicMock()
        mock_section.project_id = "123456"
        mock_section.id = "section1"
        mock_section.name = "To Do"
        mock_api.get_sections.return_value = [mock_section, mock_section, mock_section]

        # Mock comments
        mock_comment = MagicMock()
        mock_api.get_comments.return_value = [mock_comment, mock_comment]

        # Mock requests
        with patch("prometheus_todoist_exporter.exporter.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = HTTPStatus.OK
            mock_response.json.return_value = {
                "items": [
                    {
                        "project_id": "123456",
                        "completed_at": datetime.now(UTC).isoformat(),
                    },
                    {
                        "project_id": "123456",
                        "completed_at": datetime.now(UTC).isoformat(),
                    },
                ]
            }
            mock_post.return_value = mock_response

            # Set API token for test
            original_token = exporter.TODOIST_API_TOKEN
            exporter.TODOIST_API_TOKEN = TEST_API_TOKEN

            try:
                # Run collection
                exporter.collect_metrics()

                # Verify metrics
                assert (
                    self.tasks_total.labels(
                        project_name="Test Project", project_id="123456"
                    )._value.get()
                    == 1
                )

                assert (
                    self.tasks_with_due_date.labels(
                        project_name="Test Project", project_id="123456"
                    )._value.get()
                    == EXPECTED_TASKS_WITH_DUE_DATE
                )

                assert (
                    self.recurring_tasks.labels(
                        project_name="Test Project", project_id="123456"
                    )._value.get()
                    == EXPECTED_RECURRING_TASKS
                )

                assert (
                    self.tasks_overdue.labels(
                        project_name="Test Project", project_id="123456"
                    )._value.get()
                    == EXPECTED_OVERDUE_TASKS
                )
            finally:
                # Restore original token
                exporter.TODOIST_API_TOKEN = original_token


if __name__ == "__main__":
    unittest.main()
