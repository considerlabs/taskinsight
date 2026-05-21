"""Redmine → raw_redmine_* 수집기."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.connectors.redmine.connector import RedmineConnector

log = logging.getLogger(__name__)


def _last_synced_at(db: Session, resource_type: str) -> Optional[datetime]:
    row = db.execute(
        text("SELECT last_synced_at FROM sync_state WHERE resource_type = :rt"),
        {"rt": resource_type},
    ).fetchone()
    return row.last_synced_at if row else None


def _update_sync_state(db: Session, resource_type: str, synced_at: datetime) -> None:
    db.execute(text("""
        INSERT INTO sync_state (resource_type, last_synced_at, status, updated_at)
        VALUES (:rt, :ts, 'ok', NOW())
        ON CONFLICT (resource_type) DO UPDATE SET
            last_synced_at = EXCLUDED.last_synced_at,
            status         = 'ok',
            updated_at     = NOW()
    """), {"rt": resource_type, "ts": synced_at})
    db.commit()


def _upsert_projects(db: Session, items: list) -> int:
    for item in items:
        db.execute(text("""
            INSERT INTO raw_redmine_projects
                (id, identifier, name, description, status, is_public, created_on, updated_on, payload)
            VALUES (:id, :identifier, :name, :description, :status, :is_public, :created_on, :updated_on, :payload)
            ON CONFLICT (id) DO UPDATE SET
                name        = EXCLUDED.name,
                description = EXCLUDED.description,
                status      = EXCLUDED.status,
                updated_on  = EXCLUDED.updated_on,
                payload     = EXCLUDED.payload,
                _synced_at  = NOW()
        """), {
            "id":          item["id"],
            "identifier":  item.get("identifier", ""),
            "name":        item.get("name", ""),
            "description": item.get("description", ""),
            "status":      item.get("status", 1),
            "is_public":   item.get("is_public", True),
            "created_on":  item.get("created_on"),
            "updated_on":  item.get("updated_on"),
            "payload":     json.dumps(item),
        })
    db.commit()
    return len(items)


def _upsert_users(db: Session, items: list) -> int:
    for item in items:
        db.execute(text("""
            INSERT INTO raw_redmine_users
                (id, login, firstname, lastname, mail, status, created_on, updated_on, payload)
            VALUES (:id, :login, :firstname, :lastname, :mail, :status, :created_on, :updated_on, :payload)
            ON CONFLICT (id) DO UPDATE SET
                login      = EXCLUDED.login,
                firstname  = EXCLUDED.firstname,
                lastname   = EXCLUDED.lastname,
                status     = EXCLUDED.status,
                updated_on = EXCLUDED.updated_on,
                payload    = EXCLUDED.payload,
                _synced_at = NOW()
        """), {
            "id":         item["id"],
            "login":      item.get("login", ""),
            "firstname":  item.get("firstname", ""),
            "lastname":   item.get("lastname", ""),
            "mail":       item.get("mail", ""),
            "status":     item.get("status", 1),
            "created_on": item.get("created_on"),
            "updated_on": item.get("updated_on"),
            "payload":    json.dumps(item),
        })
    db.commit()
    return len(items)


def _upsert_issues(db: Session, items: list) -> int:
    for item in items:
        status_id   = item.get("status",       {}).get("id")
        priority_id = item.get("priority",     {}).get("id")
        author_id   = item.get("author",       {}).get("id")
        assignee_id = item.get("assigned_to",  {}).get("id")
        project_id  = item.get("project",      {}).get("id")
        tracker_id  = item.get("tracker",      {}).get("id")
        version_id  = item.get("fixed_version",{}).get("id")
        parent_id   = item.get("parent",       {}).get("id")

        db.execute(text("""
            INSERT INTO raw_redmine_issues
                (id, project_id, tracker_id, status_id, priority_id, author_id,
                 assigned_to_id, fixed_version_id, parent_id, subject, description,
                 start_date, due_date, done_ratio, estimated_hours, spent_hours,
                 created_on, updated_on, closed_on, payload)
            VALUES (
                :id, :project_id, :tracker_id, :status_id, :priority_id, :author_id,
                :assigned_to_id, :fixed_version_id, :parent_id, :subject, :description,
                :start_date, :due_date, :done_ratio, :estimated_hours, :spent_hours,
                :created_on, :updated_on, :closed_on, :payload
            )
            ON CONFLICT (id) DO UPDATE SET
                status_id       = EXCLUDED.status_id,
                assigned_to_id  = EXCLUDED.assigned_to_id,
                subject         = EXCLUDED.subject,
                done_ratio      = EXCLUDED.done_ratio,
                spent_hours     = EXCLUDED.spent_hours,
                updated_on      = EXCLUDED.updated_on,
                closed_on       = EXCLUDED.closed_on,
                payload         = EXCLUDED.payload,
                _synced_at      = NOW()
        """), {
            "id":               item["id"],
            "project_id":       project_id,
            "tracker_id":       tracker_id,
            "status_id":        status_id,
            "priority_id":      priority_id,
            "author_id":        author_id,
            "assigned_to_id":   assignee_id,
            "fixed_version_id": version_id,
            "parent_id":        parent_id,
            "subject":          item.get("subject", ""),
            "description":      item.get("description", ""),
            "start_date":       item.get("start_date"),
            "due_date":         item.get("due_date"),
            "done_ratio":       item.get("done_ratio", 0),
            "estimated_hours":  item.get("estimated_hours"),
            "spent_hours":      item.get("spent_hours"),
            "created_on":       item.get("created_on"),
            "updated_on":       item.get("updated_on"),
            "closed_on":        item.get("closed_on"),
            "payload":          json.dumps(item),
        })

        # 저널이 이슈 payload에 포함된 경우 즉시 upsert
        for j in item.get("journals", []):
            _upsert_single_journal(db, item["id"], j)

    db.commit()
    return len(items)


def _upsert_single_journal(db: Session, issue_id: int, j: dict) -> None:
    db.execute(text("""
        INSERT INTO raw_redmine_journals
            (id, journalized_id, user_id, notes, created_on, private_notes, payload)
        VALUES (:id, :issue_id, :user_id, :notes, :created_on, :private_notes, :payload)
        ON CONFLICT (id) DO NOTHING
    """), {
        "id":            j["id"],
        "issue_id":      issue_id,
        "user_id":       j.get("user", {}).get("id"),
        "notes":         j.get("notes", ""),
        "created_on":    j.get("created_on"),
        "private_notes": j.get("private_notes", False),
        "payload":       json.dumps(j),
    })


def _collect_journals(db: Session, config: dict, max_issues: int = 200) -> int:
    """Per-issue journal 수집 (list endpoint가 include=journals를 무시하므로 개별 GET).
    오픈 이슈 중 저널이 없는 것부터 최근 업데이트 순으로 수집.
    """
    base_url = config.get("base_url", "").rstrip("/")
    api_key  = config.get("api_key", "")
    headers  = {"X-Redmine-API-Key": api_key}

    # 저널 없는 오픈 이슈 우선, 그 다음 최근 업데이트된 이슈
    rows = db.execute(text("""
        SELECT i.id
        FROM raw_redmine_issues i
        LEFT JOIN (
            SELECT DISTINCT journalized_id FROM raw_redmine_journals
        ) j ON j.journalized_id = i.id
        WHERE j.journalized_id IS NULL
        ORDER BY i.closed_on IS NOT NULL, i.updated_on DESC
        LIMIT :limit
    """), {"limit": max_issues}).fetchall()

    issue_ids = [r.id for r in rows]
    if not issue_ids:
        log.info("저널 수집 대상 없음 (모두 이미 수집됨)")
        return 0

    log.info("저널 수집 시작: %d개 이슈", len(issue_ids))
    journal_count = 0

    for issue_id in issue_ids:
        try:
            resp = httpx.get(
                f"{base_url}/issues/{issue_id}.json",
                headers=headers,
                params={"include": "journals"},
                timeout=30,
            )
            resp.raise_for_status()
            journals = resp.json().get("issue", {}).get("journals", [])
            for j in journals:
                _upsert_single_journal(db, issue_id, j)
                journal_count += 1
        except Exception as e:
            log.warning("저널 수집 실패 (issue=%s): %s", issue_id, e)

    db.commit()
    log.info("저널 수집 완료: %d건 (이슈 %d개)", journal_count, len(issue_ids))
    return journal_count


def _extract_users_from_issues(db: Session) -> int:
    """이슈 payload의 author/assigned_to에서 사용자 추출 (admin 권한 없을 때 폴백)."""
    # author 추출 — DISTINCT ON으로 json 타입 equality 문제 우회
    db.execute(text("""
        INSERT INTO raw_redmine_users (id, login, firstname, lastname, mail, status, created_on, updated_on, payload)
        SELECT DISTINCT ON (uid)
            uid                                              AS id,
            name                                             AS login,
            SPLIT_PART(name, ' ', 1)                        AS firstname,
            SPLIT_PART(name, ' ', 2)                        AS lastname,
            ''                                               AS mail,
            1                                                AS status,
            NOW()                                            AS created_on,
            NOW()                                            AS updated_on,
            (payload->'author')::jsonb                       AS payload
        FROM (
            SELECT
                (payload->'author'->>'id')::int AS uid,
                payload->'author'->>'name'      AS name,
                payload
            FROM raw_redmine_issues
            WHERE payload->'author'->>'id' IS NOT NULL
              AND (payload->'author'->>'id')::int > 0
        ) sub
        ON CONFLICT (id) DO NOTHING
    """))

    # assigned_to 추출
    db.execute(text("""
        INSERT INTO raw_redmine_users (id, login, firstname, lastname, mail, status, created_on, updated_on, payload)
        SELECT DISTINCT ON (uid)
            uid                                              AS id,
            name                                             AS login,
            SPLIT_PART(name, ' ', 1)                        AS firstname,
            SPLIT_PART(name, ' ', 2)                        AS lastname,
            ''                                               AS mail,
            1                                                AS status,
            NOW()                                            AS created_on,
            NOW()                                            AS updated_on,
            (payload->'assigned_to')::jsonb                  AS payload
        FROM (
            SELECT
                (payload->'assigned_to'->>'id')::int AS uid,
                payload->'assigned_to'->>'name'      AS name,
                payload
            FROM raw_redmine_issues
            WHERE payload->'assigned_to'->>'id' IS NOT NULL
              AND (payload->'assigned_to'->>'id')::int > 0
        ) sub
        ON CONFLICT (id) DO NOTHING
    """))

    db.commit()
    count = db.execute(text("SELECT COUNT(*) FROM raw_redmine_users")).scalar()
    return count or 0


def sync_redmine(config: dict, db: Session) -> dict:
    """Redmine 전체 수집 (증분 포함)."""
    connector = RedmineConnector()
    now   = datetime.now(timezone.utc)
    since = _last_synced_at(db, "issues")

    log.info("Redmine sync 시작 (since=%s)", since)

    # ── 프로젝트 ──
    projects  = connector.fetch_resource("projects", config)
    p_count   = _upsert_projects(db, projects)
    _update_sync_state(db, "projects", now)

    # ── 사용자: admin API 시도, 0건이면 이슈 payload에서 추출 ──
    users   = connector.fetch_resource("users", config)
    u_count = _upsert_users(db, users)
    _update_sync_state(db, "users", now)

    if u_count == 0:
        log.info("사용자 API 반환 0건 → 이슈 payload에서 사용자 추출")
        u_count = _extract_users_from_issues(db)

    # ── 이슈 (증분) ──
    issues  = connector.fetch_resource("issues", config, since=since)
    i_count = _upsert_issues(db, issues)
    _update_sync_state(db, "issues", now)

    # ── 저널 (per-issue, 미수집 이슈 우선) ──
    # UI 동기화: 200건 / 야간 배치: run_nightly_etl에서 별도 호출 가능
    j_count = _collect_journals(db, config, max_issues=200)

    # ── DB 누적 집계 ──
    db_issues   = db.execute(text("SELECT COUNT(*) FROM raw_redmine_issues")).scalar()   or 0
    db_users    = db.execute(text("SELECT COUNT(*) FROM raw_redmine_users")).scalar()    or 0
    db_journals = db.execute(text("SELECT COUNT(*) FROM raw_redmine_journals")).scalar() or 0

    result = {
        "projects":      p_count,
        "users":         u_count,
        "issues_new":    i_count,
        "journals_new":  j_count,
        "db_issues":     db_issues,
        "db_users":      db_users,
        "db_journals":   db_journals,
        "synced_at":     now.isoformat(),
        # 하위 호환 (프론트엔드 기존 필드)
        "issues":        i_count,
        "users_total":   u_count,
    }
    log.info("Redmine sync 완료: %s", result)
    return result
