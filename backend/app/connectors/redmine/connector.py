from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.connectors.base import BaseConnector


class RedmineConnector(BaseConnector):
    connector_type = "redmine"
    display_name = "Redmine"
    category = "task_management"
    status = "active"

    def test_connection(self, config: dict) -> dict:
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")
        if not base_url or not api_key:
            return {"ok": False, "error": "base_url과 api_key가 필요합니다."}

        try:
            resp = httpx.get(
                f"{base_url}/users/current.json",
                headers={"X-Redmine-API-Key": api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                user = resp.json().get("user", {})
                return {"ok": True, "user": user.get("login", "")}
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_resource(
        self,
        resource_type: str,
        config: dict,
        since: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        base_url = config.get("base_url", "").rstrip("/")
        api_key = config.get("api_key", "")
        headers = {"X-Redmine-API-Key": api_key}

        fetchers = {
            "issues": self._fetch_issues,
            "journals": self._fetch_journals,
            "users": self._fetch_users,
            "projects": self._fetch_projects,
            "time_entries": self._fetch_time_entries,
        }
        fetcher = fetchers.get(resource_type)
        if not fetcher:
            raise ValueError(f"알 수 없는 resource_type: {resource_type}")

        return fetcher(base_url, headers, since)

    def _paginate(
        self,
        base_url: str,
        headers: dict,
        path: str,
        params: dict,
        root_key: str,
    ) -> list[dict]:
        results = []
        offset = 0
        limit = 100
        while True:
            params.update({"offset": offset, "limit": limit})
            resp = httpx.get(f"{base_url}/{path}", headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            batch = data.get(root_key, [])
            results.extend(batch)
            total = data.get("total_count", len(batch))
            offset += limit
            if offset >= total:
                break
        return results

    def _fetch_issues(self, base_url: str, headers: dict, since: Optional[datetime]) -> list:
        params: dict = {"status_id": "*", "include": "journals"}
        if since:
            params["updated_on"] = f">={since.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        return self._paginate(base_url, headers, "issues.json", params, "issues")

    def _fetch_journals(self, base_url: str, headers: dict, since: Optional[datetime]) -> list:
        # 저널은 이슈 include로 수집하므로 직접 호출 불필요 (빈 반환)
        return []

    def _fetch_users(self, base_url: str, headers: dict, since: Optional[datetime]) -> list:
        # status 파라미터 없음 → 관리자 권한이면 활성 사용자 반환, 없으면 빈 배열
        # (status=0은 일부 Redmine 버전에서 anonymous users만 반환)
        try:
            return self._paginate(base_url, headers, "users.json", {}, "users")
        except Exception:
            return []

    def _fetch_projects(self, base_url: str, headers: dict, since: Optional[datetime]) -> list:
        return self._paginate(base_url, headers, "projects.json", {}, "projects")

    def _fetch_time_entries(self, base_url: str, headers: dict, since: Optional[datetime]) -> list:
        params: dict = {}
        if since:
            params["from"] = since.strftime("%Y-%m-%d")
        return self._paginate(base_url, headers, "time_entries.json", params, "time_entries")
