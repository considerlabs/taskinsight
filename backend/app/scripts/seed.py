"""
Seed 데이터 초기화 스크립트.
최초 1회 실행: docker-compose exec backend python -m app.scripts.seed
이미 데이터 있으면 skip (멱등성 보장).
"""
from __future__ import annotations

import os
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db import SessionLocal

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


ISSUE_STATUSES = [
    # (id, name, flow_stage, is_closed, position)
    (1,  "신규",       "backlog",     False, 1),
    (2,  "진행 중",    "in_progress", False, 2),
    (3,  "검수 요청",  "review",      False, 3),
    (4,  "검수 중",    "review",      False, 4),
    (5,  "완료",       "done",        True,  5),
    (6,  "반려",       "rejected",    True,  6),
    (7,  "보류",       "blocked",     False, 7),
    (8,  "재작업",     "rework",      False, 8),
]

ISSUE_PRIORITIES = [
    # (id, name, position, color)
    (1, "낮음",  4, "#6B7280"),
    (2, "보통",  3, "#2563EB"),
    (3, "높음",  2, "#F59E0B"),
    (4, "긴급",  1, "#DC2626"),
]


def seed_issue_statuses(db: Session) -> None:
    from sqlalchemy import text
    existing = db.execute(text("SELECT COUNT(*) FROM ti_issue_statuses")).scalar()
    if existing:
        print(f"  ti_issue_statuses: {existing}건 이미 존재, skip")
        return
    for sid, name, flow_stage, is_closed, position in ISSUE_STATUSES:
        db.execute(
            text("""
                INSERT INTO ti_issue_statuses (id, name, flow_stage, is_closed, position)
                VALUES (:id, :name, :flow_stage, :is_closed, :position)
            """),
            {"id": sid, "name": name, "flow_stage": flow_stage,
             "is_closed": is_closed, "position": position},
        )
    db.execute(text("SELECT setval('ti_issue_statuses_id_seq', 100)"))
    print(f"  ti_issue_statuses: {len(ISSUE_STATUSES)}건 생성")


def seed_issue_priorities(db: Session) -> None:
    from sqlalchemy import text
    existing = db.execute(text("SELECT COUNT(*) FROM ti_issue_priorities")).scalar()
    if existing:
        print(f"  ti_issue_priorities: {existing}건 이미 존재, skip")
        return
    for pid, name, position, color in ISSUE_PRIORITIES:
        db.execute(
            text("""
                INSERT INTO ti_issue_priorities (id, name, position, color)
                VALUES (:id, :name, :position, :color)
            """),
            {"id": pid, "name": name, "position": position, "color": color},
        )
    db.execute(text("SELECT setval('ti_issue_priorities_id_seq', 100)"))
    print(f"  ti_issue_priorities: {len(ISSUE_PRIORITIES)}건 생성")


def seed_admin_user(db: Session) -> None:
    from sqlalchemy import text
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "change-me-admin-password")
    display_name = os.getenv("ADMIN_DISPLAY_NAME", "시스템 관리자")

    existing = db.execute(
        text("SELECT COUNT(*) FROM ti_users WHERE email = :email"),
        {"email": email}
    ).scalar()
    if existing:
        print(f"  admin user ({email}): 이미 존재, skip")
        return

    password_hash = pwd_ctx.hash(password)
    db.execute(
        text("""
            INSERT INTO ti_users (email, password_hash, display_name, role, is_active)
            VALUES (:email, :password_hash, :display_name, 'system_admin', TRUE)
        """),
        {"email": email, "password_hash": password_hash, "display_name": display_name},
    )
    print(f"  admin user: {email} 생성 완료")


def run() -> None:
    print("=== TaskInsight Seed 데이터 초기화 ===")
    db = SessionLocal()
    try:
        seed_issue_statuses(db)
        seed_issue_priorities(db)
        seed_admin_user(db)
        db.commit()
        print("=== Seed 완료 ===")
    except Exception as e:
        db.rollback()
        print(f"=== Seed 실패: {e} ===")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
