"""
Mock Connectors package for MARK XLVIII / FLOW.
"""

from connectors.mock.base import BaseMockConnector
from connectors.mock.mock_slack import mock_slack, MockSlackConnector
from connectors.mock.mock_jira import mock_jira, MockJiraConnector
from connectors.mock.mock_gmail import mock_gmail, MockGmailConnector
from connectors.mock.mock_calendar import mock_calendar, MockCalendarConnector
from connectors.mock.mock_github import mock_github, MockGitHubConnector


def reset_all_mock_connectors() -> None:
    """Reset all mock connectors to clean initial state."""
    mock_slack.reset()
    mock_jira.reset()
    mock_gmail.reset()
    mock_calendar.reset()
    mock_github.reset()


__all__ = [
    "BaseMockConnector",
    "mock_slack",
    "MockSlackConnector",
    "mock_jira",
    "MockJiraConnector",
    "mock_gmail",
    "MockGmailConnector",
    "mock_calendar",
    "MockCalendarConnector",
    "mock_github",
    "MockGitHubConnector",
    "reset_all_mock_connectors",
]
