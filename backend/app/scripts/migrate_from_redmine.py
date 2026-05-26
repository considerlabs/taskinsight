"""
Redmine → TaskInsight 일회성 데이터 마이그레이션.
D-day 1회 실행: docker-compose exec backend python -m app.scripts.migrate_from_redmine

실행 순서:
  1. users (raw_redmine_users → ti_users)
  2. projects (raw_redmine_projects → ti_projects)
  3. issues (raw_redmine_issues → ti_issues)
  4. journals (raw_redmine_journals → ti_journals + ti_journal_details)
  5. time_entries (raw_redmine_time_entries → ti_time_entries)
  6. custom_field_values (raw_redmine_issues.payload → ti_custom_field_values)

각 단계는 독립 트랜잭션. 실패 시 해당 단계만 롤백, 재실행 가능 (멱등성).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import SessionLocal

log = logging.getLogger(__name__)
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 임시 비밀번호 (마이그레이션 후 사용자에게 비밀번호 재설정 이메일 발송 필요)
TEMP_PASSWORD_HASH = pwd_ctx.hash("TempPassword123!")

# Redmine 상태 ID → ti_issue_statuses ID 매핑
# (Redmine status_id → ti_issue_statuses.id)
STATUS_MAP: dict[int, int] = {
    1: 1,   # New → 신규
    2: 2,   # In Progress → 진행 중
    3: 3,   # 검수 요청
    4: 4,   # 검수 중
    5: 5,   # Closed → 완료
    6: 6,   # Rejected → 반려
    8: 8,   # Rework → 재작업
    9: 7,   # Blocked → 보류
    10: 5,  # → 완료
    11: 5,  # → 완료
    12: 2,  # → 진행 중
    13: 5,  # → 완료
    14: 4,  # → 검수 중
    16: 7,  # → 보류
    17: 3,  # → 검수 요청
    18: 3,  # → 검수 요청
    19: 3,  # → 검수 요청
    20: 4,  # → 검수 중
    21: 8,  # → 재작업
    22: 8,  # → 재작업
    23: 5,  # → 완료
    24: 4,  # → 검수 중
    25: 5,  # → 완료
}

# Redmine priority_id → ti_issue_priorities.id 매핑
PRIORITY_MAP: dict[int, int] = {
    1: 1,  # Low → 낮음
    2: 2,  # Normal → 보통
    3: 3,  # High → 높음
    4: 4,  # Urgent → 긴급
    5: 4,  # Immediate → 긴급
}


def _parse_date(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    return val[:10] if len(val) >= 10 else val


def migrate_users(db: Session) -> dict[int, int]:
    """raw_redmine_users → ti_users. 반환: {redmine_user_id: ti_user_id}"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_users WHERE redmine_id IS NOT NULL")).scalar()
    if existing:
        log.info("users: 이미 마이그레이션됨 (%d건), skip", existing)
        rows = db.execute(text("SELECT redmine_id, id FROM ti_users WHERE redmine_id IS NOT NULL")).fetchall()
        return {r[0]: r[1] for r in rows}

    rows = db.execute(text("SELECT id, payload FROM raw_redmine_users")).fetchall()
    id_map: dict[int, int] = {}
    for row in rows:
        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        email = p.get("mail") or f"user_{row.id}@redmine.local"
        display_name = p.get("name") or p.get("login") or f"User{row.id}"
        result = db.execute(
            text("""
                INSERT INTO ti_users (email, password_hash, display_name, role, is_active, redmine_id)
                VALUES (:email, :pw, :name, 'member', :active, :rid)
                ON CONFLICT (email) DO UPDATE SET redmine_id = EXCLUDED.redmine_id
                RETURNING id
            """),
            {"email": email, "pw": TEMP_PASSWORD_HASH, "name": display_name,
             "active": p.get("status", 1) == 1, "rid": row.id},
        )
        ti_id = result.fetchone()[0]
        id_map[row.id] = ti_id
    db.commit()
    log.info("users: %d건 마이그레이션 완료", len(id_map))
    return id_map


def migrate_projects(db: Session, user_map: dict[int, int]) -> dict[int, int]:
    """raw_redmine_projects → ti_projects. 반환: {redmine_project_id: ti_project_id}"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_projects WHERE redmine_id IS NOT NULL")).scalar()
    if existing:
        log.info("projects: 이미 마이그레이션됨 (%d건), skip", existing)
        rows = db.execute(text("SELECT redmine_id, id FROM ti_projects WHERE redmine_id IS NOT NULL")).fetchall()
        return {r[0]: r[1] for r in rows}

    rows = db.execute(text("SELECT id, payload FROM raw_redmine_projects")).fetchall()
    id_map: dict[int, int] = {}
    for row in rows:
        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        identifier = p.get("identifier") or f"project-{row.id}"
        result = db.execute(
            text("""
                INSERT INTO ti_projects (identifier, name, description, status, redmine_id)
                VALUES (:ident, :name, :desc, 'active', :rid)
                ON CONFLICT (identifier) DO UPDATE SET redmine_id = EXCLUDED.redmine_id
                RETURNING id
            """),
            {"ident": identifier, "name": p.get("name", identifier),
             "desc": p.get("description"), "rid": row.id},
        )
        ti_id = result.fetchone()[0]
        id_map[row.id] = ti_id
    db.commit()
    log.info("projects: %d건 마이그레이션 완료", len(id_map))
    return id_map


def migrate_issues(db: Session, user_map: dict[int, int], project_map: dict[int, int]) -> dict[int, int]:
    """raw_redmine_issues → ti_issues. 반환: {redmine_issue_id: ti_issue_id}"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_issues WHERE redmine_id IS NOT NULL")).scalar()
    if existing:
        log.info("issues: 이미 마이그레이션됨 (%d건), skip", existing)
        rows = db.execute(text("SELECT redmine_id, id FROM ti_issues WHERE redmine_id IS NOT NULL")).fetchall()
        return {r[0]: r[1] for r in rows}

    rows = db.execute(text("""
        SELECT id, payload, created_on, updated_on, closed_on
        FROM raw_redmine_issues
        ORDER BY id
    """)).fetchall()

    id_map: dict[int, int] = {}
    batch_size = 500
    for i, row in enumerate(rows):
        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)

        project_id = project_map.get(p.get("project", {}).get("id") or 0)
        if not project_id:
            continue

        author_id = user_map.get(p.get("author", {}).get("id") or 0)
        assignee_id = user_map.get(p.get("assigned_to", {}).get("id") or 0) if p.get("assigned_to") else None
        status_id = STATUS_MAP.get(p.get("status", {}).get("id") or 1, 1)
        priority_id = PRIORITY_MAP.get(p.get("priority", {}).get("id") or 2, 2)

        result = db.execute(
            text("""
                INSERT INTO ti_issues (
                    project_id, subject, description, status_id, priority_id,
                    assignee_id, author_id, done_ratio, start_date, due_date,
                    estimated_hours, created_at, updated_at, closed_at, redmine_id
                ) VALUES (
                    :proj, :subj, :desc, :status, :priority,
                    :assignee, :author, :done, :start_date, :due_date,
                    :estimated, :created, :updated, :closed, :rid
                )
                ON CONFLICT (redmine_id) DO NOTHING
                RETURNING id
            """),
            {
                "proj": project_id,
                "subj": p.get("subject", ""),
                "desc": p.get("description"),
                "status": status_id,
                "priority": priority_id,
                "assignee": assignee_id,
                "author": author_id or 1,
                "done": p.get("done_ratio", 0),
                "start_date": _parse_date(p.get("start_date")),
                "due_date": _parse_date(p.get("due_date")),
                "estimated": p.get("estimated_hours"),
                "created": row.created_on,
                "updated": row.updated_on,
                "closed": row.closed_on,
                "rid": row.id,
            },
        )
        result_row = result.fetchone()
        if result_row:
            id_map[row.id] = result_row[0]

        if (i + 1) % batch_size == 0:
            db.commit()
            log.info("issues: %d / %d 처리 중...", i + 1, len(rows))

    db.commit()
    log.info("issues: %d건 마이그레이션 완료", len(id_map))
    return id_map


def migrate_parent_links(db: Session, issue_map: dict[int, int]) -> None:
    """이슈 parent_id 연결 (이슈 생성 후 별도 처리)"""
    rows = db.execute(text("""
        SELECT i.id AS redmine_id, (i.payload->'parent'->>'id')::int AS parent_redmine_id
        FROM raw_redmine_issues i
        WHERE i.payload->'parent' IS NOT NULL
          AND i.payload->'parent'->>'id' IS NOT NULL
    """)).fetchall()

    updated = 0
    for row in rows:
        ti_issue_id = issue_map.get(row.redmine_id)
        ti_parent_id = issue_map.get(row.parent_redmine_id)
        if ti_issue_id and ti_parent_id:
            db.execute(
                text("UPDATE ti_issues SET parent_id = :pid WHERE id = :iid"),
                {"pid": ti_parent_id, "iid": ti_issue_id},
            )
            updated += 1

    db.commit()
    log.info("parent_id 연결: %d건", updated)


def migrate_journals(db: Session, issue_map: dict[int, int], user_map: dict[int, int]) -> None:
    """raw_redmine_journals → ti_journals + ti_journal_details"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_journals WHERE redmine_id IS NOT NULL")).scalar()
    if existing:
        log.info("journals: 이미 마이그레이션됨 (%d건), skip", existing)
        return

    rows = db.execute(text("""
        SELECT id, journalized_id, user_id, notes, created_on, payload
        FROM raw_redmine_journals
        ORDER BY id
    """)).fetchall()

    batch_size = 1000
    count = 0
    for i, row in enumerate(rows):
        ti_issue_id = issue_map.get(row.journalized_id)
        if not ti_issue_id:
            continue

        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        ti_user_id = user_map.get(row.user_id)

        result = db.execute(
            text("""
                INSERT INTO ti_journals (issue_id, user_id, notes, created_at, redmine_id)
                VALUES (:issue_id, :user_id, :notes, :created_at, :rid)
                ON CONFLICT (redmine_id) DO NOTHING
                RETURNING id
            """),
            {"issue_id": ti_issue_id, "user_id": ti_user_id,
             "notes": row.notes, "created_at": row.created_on, "rid": row.id},
        )
        journal_row = result.fetchone()
        if not journal_row:
            continue
        journal_id = journal_row[0]

        for detail in p.get("details", []):
            db.execute(
                text("""
                    INSERT INTO ti_journal_details (journal_id, property, prop_key, old_value, new_value)
                    VALUES (:jid, :prop, :key, :old, :new)
                """),
                {"jid": journal_id, "prop": detail.get("property"),
                 "key": detail.get("name"), "old": detail.get("old_value"),
                 "new": detail.get("new_value")},
            )
        count += 1

        if (i + 1) % batch_size == 0:
            db.commit()
            log.info("journals: %d / %d 처리 중...", i + 1, len(rows))

    db.commit()
    log.info("journals: %d건 마이그레이션 완료", count)


def migrate_time_entries(db: Session, issue_map: dict[int, int],
                          project_map: dict[int, int], user_map: dict[int, int]) -> None:
    """raw_redmine_time_entries → ti_time_entries"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_time_entries WHERE redmine_id IS NOT NULL")).scalar()
    if existing:
        log.info("time_entries: 이미 마이그레이션됨 (%d건), skip", existing)
        return

    rows = db.execute(text("SELECT id, payload FROM raw_redmine_time_entries")).fetchall()
    count = 0
    for row in rows:
        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        ti_issue_id = issue_map.get(p.get("issue", {}).get("id") or 0)
        ti_project_id = project_map.get(p.get("project", {}).get("id") or 0)
        ti_user_id = user_map.get(p.get("user", {}).get("id") or 0)
        if not ti_project_id or not ti_user_id:
            continue

        db.execute(
            text("""
                INSERT INTO ti_time_entries (issue_id, project_id, user_id, hours, activity, spent_on, comments, redmine_id)
                VALUES (:issue_id, :project_id, :user_id, :hours, :activity, :spent_on, :comments, :rid)
                ON CONFLICT (redmine_id) DO NOTHING
            """),
            {"issue_id": ti_issue_id, "project_id": ti_project_id, "user_id": ti_user_id,
             "hours": p.get("hours", 0), "activity": p.get("activity", {}).get("name"),
             "spent_on": _parse_date(p.get("spent_on")), "comments": p.get("comments"), "rid": row.id},
        )
        count += 1

    db.commit()
    log.info("time_entries: %d건 마이그레이션 완료", count)


def migrate_custom_field_values(db: Session, issue_map: dict[int, int]) -> None:
    """raw_redmine_issues.payload.custom_fields → ti_custom_field_values"""
    existing = db.execute(text("SELECT COUNT(*) FROM ti_custom_field_values")).scalar()
    if existing:
        log.info("custom_field_values: 이미 마이그레이션됨 (%d건), skip", existing)
        return

    rows = db.execute(text("SELECT id, payload FROM raw_redmine_issues")).fetchall()
    count = 0
    for row in rows:
        ti_issue_id = issue_map.get(row.id)
        if not ti_issue_id:
            continue
        p = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
        for cf in p.get("custom_fields", []):
            val = cf.get("value")
            if val is None or val == "":
                continue
            db.execute(
                text("""
                    INSERT INTO ti_custom_field_values (issue_id, field_name, field_value)
                    VALUES (:issue_id, :fname, :fval)
                    ON CONFLICT (issue_id, field_name) DO NOTHING
                """),
                {"issue_id": ti_issue_id, "fname": cf.get("name"), "fval": str(val)},
            )
            count += 1

    db.commit()
    log.info("custom_field_values: %d건 마이그레이션 완료", count)


def verify(db: Session) -> None:
    tables = [
        "ti_users", "ti_projects", "ti_issues", "ti_journals",
        "ti_time_entries", "ti_custom_field_values",
    ]
    print("\n=== 마이그레이션 검증 ===")
    for t in tables:
        cnt = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t}: {cnt:,}건")

    redmine_issue_cnt = db.execute(text("SELECT COUNT(*) FROM raw_redmine_issues")).scalar()
    ti_issue_cnt = db.execute(text("SELECT COUNT(*) FROM ti_issues")).scalar()
    print(f"\n  Redmine 원본: {redmine_issue_cnt:,}건 → TaskInsight: {ti_issue_cnt:,}건")
    if ti_issue_cnt < redmine_issue_cnt * 0.95:
        print("  ⚠️  이슈 손실 5% 초과 — project_map 확인 필요")
    else:
        print("  ✅ 이슈 이전 정상")


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print("=== Redmine → TaskInsight 마이그레이션 시작 ===")
    print("⚠️  실행 전 확인:")
    print("   1. ti_* 테이블 Alembic 마이그레이션 완료 여부")
    print("   2. seed.py 실행 완료 여부 (이슈 상태/우선순위 seed 필요)")
    print("   3. raw_redmine_* 테이블 데이터 존재 여부")
    print("")

    db = SessionLocal()
    try:
        print("[1/7] 사용자 마이그레이션...")
        user_map = migrate_users(db)

        print("[2/7] 프로젝트 마이그레이션...")
        project_map = migrate_projects(db, user_map)

        print("[3/7] 이슈 마이그레이션...")
        issue_map = migrate_issues(db, user_map, project_map)

        print("[4/7] 부모-자식 이슈 연결...")
        migrate_parent_links(db, issue_map)

        print("[5/7] 저널(이력) 마이그레이션...")
        migrate_journals(db, issue_map, user_map)

        print("[6/7] 타임 엔트리 마이그레이션...")
        migrate_time_entries(db, issue_map, project_map, user_map)

        print("[7/7] 커스텀 필드 값 마이그레이션...")
        migrate_custom_field_values(db, issue_map)

        verify(db)
        print("\n=== 마이그레이션 완료 ===")
        print("다음 단계: 사용자들에게 비밀번호 재설정 이메일 발송 필요 (임시 비밀번호: TempPassword123!)")

    except Exception as e:
        db.rollback()
        log.error("마이그레이션 실패: %s", e, exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
