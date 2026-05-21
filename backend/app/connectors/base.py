from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional


class BaseConnector(ABC):
    connector_type: str
    display_name: str
    category: str   # "task_management" | "code_repo" | "messaging"
    status: str     # "active" | "coming_soon"

    @abstractmethod
    def test_connection(self, config: dict) -> dict:
        """연결 테스트. 성공: {"ok": True}, 실패: {"ok": False, "error": str}"""
        ...

    @abstractmethod
    def fetch_resource(
        self,
        resource_type: str,
        config: dict,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """리소스 수집. resource_type: issues | journals | users | projects | time_entries"""
        ...
