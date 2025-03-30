import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from prometheus_client import REGISTRY

from prometheus_todoist_exporter import exporter


class TestTodoistExporter(unittest.TestCase):
    def setUp(self):
        # Reset metrics before each test
        for metric in list(REGISTRY._names_to_collectors.values()):
            try:
                REGISTRY.unregister(metric)
            except KeyError:
                # Skip metrics that aren't properly registered
                pass

        # Re-register metrics
        self.tasks_total = exporter.TODOIST_TASKS_TOTAL
        self.tasks_overdue = exporter.TODOIST_TASKS_OVERDUE
        self.tasks_due_today = exporter.TODOIST_TASKS_DUE_TODAY
        self.tasks_completed = exporter.TODOIST_TASKS_COMPLETED
        self.project_collaborators = exporter.TODOIST_PROJECT_COLLABORATORS
        self.sections_total = exporter.TODOIST_SECTIONS_TOTAL
        self.comments_total = exporter.TODOIST_COMMENTS_TOTAL
        self.priority_tasks = exporter.TODOIST_PRIORITY_TASKS
        self.api_errors = exporter.TODOIST_API_ERRORS
        self.scrape_duration = exporter.TODOIST_SCRAPE_DURATION

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
        self.assertEqual(len(result), 1)
        self.assertEqual(result["123456"]["name"], "Test Project")
        mock_api.get_projects.assert_called_once()

    @patch("prometheus_todoist_exporter.exporter.api")
    def test_collect_projects_with_error(self, mock_api):
        # Mock error
        mock_api.get_projects.side_effect = Exception("API Error")

        # Test function
        result = exporter.collect_projects()

        # Verify results
        self.assertEqual(len(result), 0)
        mock_api.get_projects.assert_called_once()
        self.assertEqual(
            self.api_errors.labels(endpoint="get_projects")._value.get(), 1
        )

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
        self.assertEqual(len(projects_dict["123456"]["tasks"]), 1)
        self.assertEqual(projects_dict["123456"]["tasks"][0].id, "789")
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
        self.assertEqual(len(projects_dict["123456"]["tasks"]), 0)
        mock_api.get_tasks.assert_called_once()
        self.assertEqual(self.api_errors.labels(endpoint="get_tasks")._value.get(), 1)

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
        self.assertEqual(len(projects_dict["123456"]["collaborators"]), 1)
        mock_api.get_collaborators.assert_called_once_with(project_id="123456")

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
        mock_task.due = MagicMock()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        mock_task.due.date = today
        mock_api.get_tasks.return_value = [mock_task]

        # Mock collaborators
        mock_collaborator = MagicMock()
        mock_api.get_collaborators.return_value = [mock_collaborator, mock_collaborator]

        # Mock sections
        mock_section = MagicMock()
        mock_section.project_id = "123456"
        mock_api.get_sections.return_value = [mock_section, mock_section, mock_section]

        # Mock comments
        mock_comment = MagicMock()
        mock_api.get_comments.return_value = [mock_comment, mock_comment]

        # Run collection
        exporter.collect_metrics()

        # Verify metrics
        self.assertEqual(
            self.tasks_total.labels(
                project_name="Test Project", project_id="123456"
            )._value.get(),
            1,
        )
        self.assertEqual(
            self.tasks_due_today.labels(
                project_name="Test Project", project_id="123456"
            )._value.get(),
            1,
        )
        self.assertEqual(
            self.priority_tasks.labels(
                project_name="Test Project", project_id="123456", priority="4"
            )._value.get(),
            1,
        )
        self.assertEqual(
            self.project_collaborators.labels(
                project_name="Test Project", project_id="123456"
            )._value.get(),
            2,
        )
        self.assertEqual(
            self.sections_total.labels(
                project_name="Test Project", project_id="123456"
            )._value.get(),
            3,
        )
        self.assertEqual(
            self.comments_total.labels(
                project_name="Test Project", project_id="123456"
            )._value.get(),
            2,
        )


if __name__ == "__main__":
    unittest.main()
