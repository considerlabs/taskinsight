from app.connectors.base import BaseConnector
from app.connectors.redmine.connector import RedmineConnector

CONNECTORS: dict[str, type[BaseConnector]] = {
    "redmine": RedmineConnector,
    # "jira": JiraConnector,      # coming_soon
    # "asana": AsanaConnector,    # coming_soon
}

COMING_SOON = [
    {"connector_type": "jira",      "display_name": "Jira",      "category": "task_management", "status": "coming_soon"},
    {"connector_type": "asana",     "display_name": "Asana",     "category": "task_management", "status": "coming_soon"},
    {"connector_type": "clickup",   "display_name": "ClickUp",   "category": "task_management", "status": "coming_soon"},
    {"connector_type": "notion",    "display_name": "Notion",    "category": "task_management", "status": "coming_soon"},
]


def get_connector(connector_type: str) -> BaseConnector:
    cls = CONNECTORS.get(connector_type)
    if not cls:
        raise ValueError(f"지원하지 않는 connector_type: {connector_type}")
    return cls()
