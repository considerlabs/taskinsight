"""ETL: raw_redmine_* → fct_* / dim_* 마트 테이블 채우기."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


# ─── dim 테이블 ──────────────────────────────────────────────────────────────

def populate_dim_project(db: Session) -> int:
    result = db.execute(text("""
        INSERT INTO dim_project (project_id, identifier, name, is_active)
        SELECT id, identifier, name, (status = 1)
        FROM raw_redmine_projects
        ON CONFLICT (project_id) DO UPDATE SET
            identifier = EXCLUDED.identifier,
            name       = EXCLUDED.name,
            is_active  = EXCLUDED.is_active
    """))
    db.commit()
    return result.rowcount


def populate_dim_user(db: Session) -> int:
    result = db.execute(text("""
        INSERT INTO dim_user (user_id, login, display_name, is_active)
        SELECT id,
               login,
               TRIM(firstname || ' ' || lastname),
               (status = 1)
        FROM raw_redmine_users
        ON CONFLICT (user_id) DO UPDATE SET
            login        = EXCLUDED.login,
            display_name = EXCLUDED.display_name,
            is_active    = EXCLUDED.is_active
    """))
    db.commit()
    return result.rowcount


# ─── 상태 전환 이력 ────────────────────────────────────────────────────────

def populate_state_transitions(db: Session) -> int:
    """raw_redmine_journals의 payload→details에서 status 변경 추출."""
    db.execute(text("DELETE FROM fct_state_transition"))

    result = db.execute(text("""
        INSERT INTO fct_state_transition
            (issue_id, journal_id, from_status_id, to_status_id,
             from_stage, to_stage, changed_at, changed_by_id)
        SELECT
            j.journalized_id                               AS issue_id,
            j.id                                           AS journal_id,
            (d->>'old_value')::int                         AS from_status_id,
            (d->>'value')::int                             AS to_status_id,
            COALESCE(ds_from.flow_stage, 'unknown')        AS from_stage,
            COALESCE(ds_to.flow_stage,   'unknown')        AS to_stage,
            j.created_on                                   AS changed_at,
            j.user_id                                      AS changed_by_id
        FROM raw_redmine_journals j,
             json_array_elements(j.payload->'details') AS d
        LEFT JOIN dim_status ds_from ON ds_from.status_id = (d->>'old_value')::int
        LEFT JOIN dim_status ds_to   ON ds_to.status_id   = (d->>'value')::int
        WHERE d->>'name' = 'status_id'
          AND (d->>'old_value') ~ '^[0-9]+$'
          AND (d->>'value')     ~ '^[0-9]+$'
        ORDER BY j.journalized_id, j.created_on
    """))
    db.commit()
    return result.rowcount


def update_transition_days(db: Session) -> None:
    """각 전환의 days_in_from(이전 단계 체류일) 계산."""
    db.execute(text("""
        UPDATE fct_state_transition t
        SET days_in_from = EXTRACT(EPOCH FROM (
            t.changed_at - LAG(t.changed_at) OVER (
                PARTITION BY t.issue_id ORDER BY t.changed_at
            )
        )) / 86400.0
        WHERE t.days_in_from IS NULL
    """))

    # 첫 번째 전환의 days_in_from = created_on → 첫 전환까지
    db.execute(text("""
        UPDATE fct_state_transition t
        SET days_in_from = EXTRACT(EPOCH FROM (
            t.changed_at - i.created_on
        )) / 86400.0
        FROM raw_redmine_issues i
        WHERE t.issue_id = i.id
          AND t.days_in_from IS NULL
    """))
    db.commit()


# ─── 이슈 스냅샷 ─────────────────────────────────────────────────────────────

def _compute_risk_score(total_days: float, days_in_stage: float, stage: str) -> int:
    """위험점수 0~100. 단순 휴리스틱."""
    score = 0
    if total_days > 365:
        score += 40
    elif total_days > 90:
        score += 20
    elif total_days > 30:
        score += 10

    if days_in_stage > 90:
        score += 40
    elif days_in_stage > 30:
        score += 20
    elif days_in_stage > 14:
        score += 10

    if stage == "blocked":
        score += 20
    elif stage == "review":
        score += 10

    return min(score, 100)


def populate_issue_snapshot(db: Session) -> int:
    """fct_issue_snapshot 전체 재구축."""
    now = datetime.now(timezone.utc)

    db.execute(text("DELETE FROM fct_issue_snapshot"))

    # 현재 단계 체류일: 마지막 전환 이후 현재까지
    db.execute(text(f"""
        INSERT INTO fct_issue_snapshot
            (issue_id, project_id, subject, current_status_id, flow_stage,
             assigned_to_id, created_on, updated_on, closed_on,
             total_days, days_in_stage, risk_score, is_rework, _etl_at)
        SELECT
            i.id                                                         AS issue_id,
            i.project_id,
            i.subject,
            i.status_id                                                  AS current_status_id,
            COALESCE(ds.flow_stage, 'backlog')                           AS flow_stage,
            i.assigned_to_id,
            i.created_on,
            i.updated_on,
            i.closed_on,

            -- total_days: 생성→완료 또는 생성→현재
            EXTRACT(EPOCH FROM (
                COALESCE(i.closed_on, TIMESTAMP WITH TIME ZONE '{now.isoformat()}')
                - i.created_on
            )) / 86400.0                                                 AS total_days,

            -- days_in_stage: 마지막 전환→현재 (또는 생성→현재)
            EXTRACT(EPOCH FROM (
                COALESCE(i.closed_on, TIMESTAMP WITH TIME ZONE '{now.isoformat()}')
                - COALESCE(
                    (SELECT MAX(t.changed_at) FROM fct_state_transition t WHERE t.issue_id = i.id),
                    i.created_on
                )
            )) / 86400.0                                                 AS days_in_stage,

            0                                                            AS risk_score,

            -- is_rework: review → in_progress 전환이 존재하면 TRUE
            EXISTS (
                SELECT 1 FROM fct_state_transition t
                WHERE t.issue_id = i.id
                  AND t.from_stage = 'review'
                  AND t.to_stage   = 'in_progress'
            )                                                            AS is_rework,

            TIMESTAMP WITH TIME ZONE '{now.isoformat()}'                AS _etl_at
        FROM raw_redmine_issues i
        LEFT JOIN dim_status ds ON ds.status_id = i.status_id
    """))
    db.commit()

    # risk_score 업데이트 (Python 계산 대신 SQL 휴리스틱)
    db.execute(text("""
        UPDATE fct_issue_snapshot
        SET risk_score = LEAST(100,
            CASE WHEN total_days   > 365 THEN 40
                 WHEN total_days   > 90  THEN 20
                 WHEN total_days   > 30  THEN 10
                 ELSE 0 END
            +
            CASE WHEN days_in_stage > 90 THEN 40
                 WHEN days_in_stage > 30 THEN 20
                 WHEN days_in_stage > 14 THEN 10
                 ELSE 0 END
            +
            CASE WHEN flow_stage = 'blocked' THEN 20
                 WHEN flow_stage = 'review'  THEN 10
                 ELSE 0 END
        )
    """))
    db.commit()

    count = db.execute(text("SELECT COUNT(*) FROM fct_issue_snapshot")).scalar()
    return count


# ─── 처리량 ───────────────────────────────────────────────────────────────────

def populate_throughput_daily(db: Session) -> int:
    db.execute(text("DELETE FROM fct_throughput_daily"))
    result = db.execute(text("""
        INSERT INTO fct_throughput_daily (date, project_id, completed_count)
        SELECT
            DATE(closed_on AT TIME ZONE 'Asia/Seoul') AS date,
            project_id,
            COUNT(*)                                  AS completed_count
        FROM raw_redmine_issues
        WHERE closed_on IS NOT NULL
        GROUP BY 1, 2
        ON CONFLICT (date, project_id) DO UPDATE SET
            completed_count = EXCLUDED.completed_count
    """))
    db.commit()
    return result.rowcount


# ─── 전체 ETL ────────────────────────────────────────────────────────────────

def run_etl(db: Session) -> dict:
    log.info("ETL 시작")
    results = {}

    results["dim_project"] = populate_dim_project(db)
    results["dim_user"] = populate_dim_user(db)
    results["state_transitions"] = populate_state_transitions(db)
    update_transition_days(db)
    results["issue_snapshot"] = populate_issue_snapshot(db)
    results["throughput_daily"] = populate_throughput_daily(db)

    log.info("ETL 완료: %s", results)
    return results
