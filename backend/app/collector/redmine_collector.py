"""Redmine → raw_redmine_* 수집기."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.connectors.redmine.connector import RedmineConnector

log = logging.getLogger(__name__)


def _last_synced_at(db: Session, resource_type: str) -> datetime | None:
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


def _upsert_projects(db: Session, items: list[dict]) -> int:
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


def _upsert_users(db: Session, items: list[dict]) -> int:
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
            "id":        item["id"],
            "login":     item.get("login", ""),
            "firstname": item.get("firstname", ""),
            "lastname":  item.get("lastname", ""),
            "mail":      item.get("mail", ""),
            "status":    item.get("status", 1),
            "created_on": item.get("created_on"),
            "updated_on": item.get("updated_on"),
            "payload":   json.dumps(item),
        })
    db.commit()
    return len(items)


def _upsert_issues(db: Session, items: list[dict]) -> int:
    journal_count = 0
    for item in items:
        status_id  = item.get("status",   {}).get("id")
        priority_id = item.get("priority", {}).get("id")
        author_id  = item.get("author",   {}).get("id")
        assignee_id = item.get("assigned_to", {}).get("id")
        project_id = item.get("project",  {}).get("id")
        tracker_id = item.get("tracker",  {}).get("id")
        version_id = item.get("fixed_version", {}).get("id")
        parent_id  = item.get("parent",   {}).get("id")

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

        # 저널 upsert
        for j in item.get("journals", []):
            db.execute(text("""
                INSERT INTO raw_redmine_journals
                    (id, journalized_id, user_id, notes, created_on, private_notes, payload)
                VALUES (:id, :issue_id, :user_id, :notes, :created_on, :private_notes, :payload)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id":            j["id"],
                "issue_id":      item["id"],
                "user_id":       j.get("user", {}).get("id"),
                "notes":         j.get("notes", ""),
                "created_on":    j.get("created_on"),
                "private_notes": j.get("private_notes", False),
                "payload":       json.dumps(j),
            })
            journal_count += 1

    db.commit()
    return len(items)


def sync_redmine(config: dict, db: Session) -> dict:
    """Redmine 전체 수집 (증분 포함)."""
    connector = RedmineConnector()
    now = datetime.now(timezone.utc)
    since = _last_synced_at(db, "issues")

    log.info("Redmine sync 시작 (since=%s)", since)

    projects = connector.fetch_resource("projects", config)
    p_count = _upsert_projects(db, projects)
    _update_sync_state(db, "projects", now)

    users = connector.fetch_resource("users", config)
    u_count = _upsert_users(db, users)
    _update_sync_state(db, "users", now)

    issues = connector.fetch_resource("issues", config, since=since)
    i_count = _upsert_issues(db, issues)
    _update_sync_state(db, "issues", now)

    result = {
        "projects": p_count,
        "users":    u_count,
        "issues":   i_count,
        "synced_at": now.isoformat(),
    }
    log.info("Redmine sync 완료: %s", result)
    return result
