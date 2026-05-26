"""
테스트 데이터 생성 스크립트.
seed.py 실행 후 1회 실행: docker-compose exec backend python -m app.scripts.create_test_data

생성 데이터:
  - 테스트 계정 4개 (admin / manager / member / viewer)
  - 테스트 프로젝트 1개 (identifier="test-project")
  - 프로젝트 멤버 등록
  - 테스트 이슈 25개 (상태/우선순위/담당자/날짜 다양하게)
  - 테스트 저널 10개
  - 테스트 시간기록 15개

멱등성 보장: 테스트 프로젝트 이미 존재하면 전부 skip.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import SessionLocal

log = logging.getLogger(__name__)
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

TODAY = date.today()

TEST_USERS = [
    # (email, password, display_name, role)
    ("admin@test.com",   "TestAdmin123!",   "테스트 관리자",    "system_admin"),
    ("manager@test.com", "TestManager123!", "테스트 PM",       "project_manager"),
    ("member@test.com",  "TestMember123!",  "테스트 팀원",     "member"),
    ("viewer@test.com",  "TestViewer123!",  "테스트 뷰어",     "viewer"),
    # 이슈 담당자 다양화용 추가 계정
    ("dev1@test.com",    "TestDev123!",     "김개발",          "member"),
    ("dev2@test.com",    "TestDev123!",     "이개발",          "member"),
]

TEST_PROJECT = {
    "identifier": "test-project",
    "name": "테스트 프로젝트",
    "description": "기능 테스트용 프로젝트입니다.",
    "status": "active",
}


def _get_or_create_user(db: Session, email: str, password: str,
                        display_name: str, role: str) -> int:
    row = db.execute(
        text("SELECT id FROM ti_users WHERE email = :e"), {"e": email}
    ).fetchone()
    if row:
        return row[0]
    result = db.execute(
        text("""
            INSERT INTO ti_users (email, password_hash, display_name, role, is_active)
            VALUES (:email, :pw, :name, :role, TRUE)
            RETURNING id
        """),
        {"email": email, "pw": pwd_ctx.hash(password),
         "name": display_name, "role": role},
    )
    return result.fetchone()[0]


def create_users(db: Session) -> dict[str, int]:
    """테스트 계정 생성. 반환: {email: user_id}"""
    user_ids: dict[str, int] = {}
    for email, pw, name, role in TEST_USERS:
        uid = _get_or_create_user(db, email, pw, name, role)
        user_ids[email] = uid
    db.commit()
    log.info("테스트 사용자 %d명 준비 완료", len(user_ids))
    return user_ids


def create_project(db: Session, admin_id: int) -> int:
    """테스트 프로젝트 생성. 반환: project_id"""
    row = db.execute(
        text("SELECT id FROM ti_projects WHERE identifier = :ident"),
        {"ident": TEST_PROJECT["identifier"]},
    ).fetchone()
    if row:
        log.info("테스트 프로젝트 이미 존재 (id=%d), skip", row[0])
        return row[0]

    result = db.execute(
        text("""
            INSERT INTO ti_projects (identifier, name, description, status)
            VALUES (:ident, :name, :desc, :status)
            RETURNING id
        """),
        {
            "ident": TEST_PROJECT["identifier"],
            "name": TEST_PROJECT["name"],
            "desc": TEST_PROJECT["description"],
            "status": TEST_PROJECT["status"],
        },
    )
    pid = result.fetchone()[0]
    db.commit()
    log.info("테스트 프로젝트 생성 (id=%d)", pid)
    return pid


def add_project_members(db: Session, project_id: int, user_ids: dict[str, int]) -> None:
    """프로젝트 멤버 등록 (ti_project_members 테이블 없으면 skip)."""
    try:
        role_map = {
            "admin@test.com":   "manager",
            "manager@test.com": "manager",
            "member@test.com":  "member",
            "viewer@test.com":  "viewer",
            "dev1@test.com":    "member",
            "dev2@test.com":    "member",
        }
        for email, uid in user_ids.items():
            role = role_map.get(email, "member")
            db.execute(
                text("""
                    INSERT INTO ti_project_members (project_id, user_id, role)
                    VALUES (:pid, :uid, :role)
                    ON CONFLICT (project_id, user_id) DO NOTHING
                """),
                {"pid": project_id, "uid": uid, "role": role},
            )
        db.commit()
        log.info("프로젝트 멤버 등록 완료")
    except Exception as e:
        db.rollback()
        log.warning("프로젝트 멤버 등록 skip (테이블 미존재 가능): %s", e)


def create_issues(db: Session, project_id: int, user_ids: dict[str, int]) -> list[int]:
    """테스트 이슈 25개 생성."""
    admin_id   = user_ids["admin@test.com"]
    manager_id = user_ids["manager@test.com"]
    member_id  = user_ids["member@test.com"]
    dev1_id    = user_ids["dev1@test.com"]
    dev2_id    = user_ids["dev2@test.com"]

    # (subject, status_id, priority_id, assignee_id, done_ratio, due_date_offset, estimated_hours, description)
    issues_data = [
        # 신규(1) — 보통(2)
        ("로그인 화면 UI 구현",            1, 2, member_id,  0,  7,  8.0,  "이메일/비밀번호 입력 폼, 유효성 검사, 에러 메시지 표시"),
        ("회원 목록 조회 API 개발",         1, 2, dev1_id,    0,  5,  4.0,  "페이지네이션 포함. limit/offset 파라미터 지원"),
        ("이슈 생성 폼 컴포넌트",           1, 3, member_id,  0,  3, 16.0, "제목, 설명, 담당자, 우선순위, 기한 필드"),
        ("DB 인덱스 최적화",               1, 1, None,       0, 30,  None, "이슈 목록 쿼리 느린 원인 분석 후 인덱스 추가"),
        ("알림 발송 실패 케이스 처리",      1, 2, dev2_id,    0, 10,  6.0,  "Teams/Email 발송 실패 시 로그 기록 + 재시도 없이 넘어가기"),
        # 진행 중(2)
        ("이슈 상태 변경 API",             2, 3, dev1_id,   40, -2,  8.0,  "상태 전환 규칙 검증 포함. 잘못된 전환 시 400"),
        ("칸반 보드 드래그앤드롭 구현",     2, 2, member_id, 60,  5, 24.0, "react-beautiful-dnd 또는 @dnd-kit/core 사용"),
        ("파일 업로드 API",                2, 3, dev1_id,   30,  3, 12.0, "최대 20MB, .exe .bat .sh 차단. multipart/form-data"),
        ("JWT 리프레시 토큰 구현",          2, 4, dev2_id,   80, -1,  8.0,  "HttpOnly 쿠키, 30일 만료, 재사용 감지"),
        ("이슈 목록 필터/정렬 기능",        2, 2, member_id, 20,  7, 16.0, "상태/우선순위/담당자/기한 필터, 다중 정렬"),
        # 검수 요청(3)
        ("대시보드 요약 카드 컴포넌트",     3, 2, member_id, 90,  1,  8.0,  "총 이슈 수, 진행 중, 완료, 기한 초과 표시"),
        ("시간기록 입력 모달",             3, 2, dev1_id,   95,  0,  4.0,  "시간, 활동 유형, 날짜, 설명 입력"),
        # 검수 중(4)
        ("이슈 상세 페이지",               4, 3, manager_id, 90, -1, 20.0, "제목/상태/우선순위/담당자/저널/첨부파일 탭"),
        ("Alembic 마이그레이션 0004-0007",  4, 4, dev2_id,  100,  0, 12.0, "신규 테이블 생성 마이그레이션"),
        # 완료(5)
        ("Docker Compose 초기 설정",       5, 2, admin_id, 100, -10, 4.0, "backend/frontend/postgres/redis/nginx 서비스 구성"),
        ("seed.py 작성",                   5, 2, admin_id, 100,  -7, 2.0, "이슈 상태, 우선순위, 관리자 계정 초기 데이터"),
        ("pyproject.toml 의존성 정리",     5, 1, dev1_id,  100,  -5, 1.0, "passlib, python-jose, aiosmtplib 추가"),
        ("nginx.conf 초안",                5, 2, dev2_id,  100,  -3, 2.0, "리버스 프록시, 25MB 업로드 제한, LLM 타임아웃 180s"),
        # 반려(6)
        ("레거시 세션 인증 방식 도입",      6, 1, None,       0, -5, None, "JWT로 확정됨에 따라 반려"),
        # 보류(7)
        ("Gantt 차트 구현",                7, 2, None,       0, 60, None, "Phase 2+ 대상. v2로 연기됨"),
        ("Google SSO 연동",                7, 1, None,       0, 90, None, "사내망 환경으로 인해 보류"),
        # 재작업(8)
        ("이슈 삭제 API",                  8, 3, dev2_id,   30, -3,  4.0, "소프트 삭제(is_deleted 플래그) 방식으로 재설계 필요"),
        # 기한 초과 (due_date_offset < 0, 진행 중)
        ("성능 테스트 시나리오 작성",       2, 3, member_id, 10, -5,  8.0, "k6 또는 locust 사용. 동시 50명 부하 테스트"),
        # 부모 이슈 후보 (자식 이슈가 붙을 것)
        ("Phase 1 인증 모듈",              2, 4, manager_id, 50, 14, 40.0, "로그인, 토큰, 권한 검사 전체"),
        # 미담당 이슈
        ("코드 리뷰 가이드 문서",           1, 1, None,       0, 30, None, "PR 리뷰 기준 및 체크리스트 작성"),
    ]

    # 기존 테스트 이슈 확인
    existing = db.execute(
        text("SELECT COUNT(*) FROM ti_issues WHERE project_id = :pid"),
        {"pid": project_id}
    ).scalar()
    if existing:
        log.info("테스트 이슈 이미 존재 (%d건), skip", existing)
        rows = db.execute(
            text("SELECT id FROM ti_issues WHERE project_id = :pid ORDER BY id"),
            {"pid": project_id}
        ).fetchall()
        return [r[0] for r in rows]

    issue_ids: list[int] = []
    for i, (subject, status_id, priority_id, assignee_id,
            done_ratio, due_offset, estimated_hours, description) in enumerate(issues_data):
        due_date = (TODAY + timedelta(days=due_offset)).isoformat() if due_offset is not None else None
        closed_at = None
        if status_id in (5, 6):  # 완료, 반려
            closed_at = (TODAY + timedelta(days=due_offset)).isoformat()

        result = db.execute(
            text("""
                INSERT INTO ti_issues (
                    project_id, subject, description, status_id, priority_id,
                    assignee_id, author_id, done_ratio, due_date,
                    estimated_hours, closed_at
                ) VALUES (
                    :proj, :subj, :desc, :status, :priority,
                    :assignee, :author, :done, :due,
                    :estimated, :closed
                )
                RETURNING id
            """),
            {
                "proj": project_id,
                "subj": subject,
                "desc": description,
                "status": status_id,
                "priority": priority_id,
                "assignee": assignee_id,
                "author": manager_id,
                "done": done_ratio,
                "due": due_date,
                "estimated": estimated_hours,
                "closed": closed_at,
            },
        )
        issue_ids.append(result.fetchone()[0])

    # 마지막 이슈를 "Phase 1 인증 모듈"의 자식으로 연결 (부모-자식 관계 테스트)
    if len(issue_ids) >= 24:
        parent_id = issue_ids[23]  # "Phase 1 인증 모듈"
        child_candidates = [issue_ids[5], issue_ids[8]]  # "이슈 상태 변경 API", "JWT 리프레시"
        for child_id in child_candidates:
            db.execute(
                text("UPDATE ti_issues SET parent_id = :pid WHERE id = :iid"),
                {"pid": parent_id, "iid": child_id},
            )

    db.commit()
    log.info("테스트 이슈 %d건 생성", len(issue_ids))
    return issue_ids


def create_journals(db: Session, issue_ids: list[int], user_ids: dict[str, int]) -> None:
    """테스트 저널(코멘트 + 상태변경 이력) 생성."""
    admin_id   = user_ids["admin@test.com"]
    manager_id = user_ids["manager@test.com"]
    member_id  = user_ids["member@test.com"]
    dev1_id    = user_ids["dev1@test.com"]

    if not issue_ids:
        return

    # 이미 저널 있으면 skip
    existing = db.execute(
        text("SELECT COUNT(*) FROM ti_journals WHERE issue_id = :iid"),
        {"iid": issue_ids[0]}
    ).scalar()
    if existing:
        log.info("테스트 저널 이미 존재, skip")
        return

    journals = [
        # (issue_idx, user_id, changes, note)
        (0, manager_id, '{}',                                           "로그인 화면 와이어프레임 검토 완료. 개발 시작 가능합니다."),
        (1, dev1_id,    '{"status_id": [1, 2]}',                        "개발 시작합니다."),
        (2, member_id,  '{}',                                           "폼 유효성 검사 로직 구현 중입니다. @dev1@test.com 리뷰 부탁드립니다."),
        (5, dev1_id,    '{"status_id": [1, 2], "assignee_id": [0, 0]}', None),
        (5, manager_id, '{}',                                           "API 스펙 확인 완료. 상태 전환 규칙 docs/BUSINESS_RULES.md 참고."),
        (6, member_id,  '{"done_ratio": [0, 60]}',                      "드래그앤드롭 기본 구현 완료. 저장 로직 연결 중."),
        (7, dev1_id,    '{"status_id": [1, 2]}',                        "파일 업로드 시작. 확장자 차단 로직 먼저 작성."),
        (13, dev1_id,   '{"status_id": [2, 4]}',                        None),
        (14, admin_id,  '{"status_id": [2, 5]}',                        "배포 완료 확인"),
        (15, admin_id,  '{"status_id": [2, 5]}',                        "seed 스크립트 테스트 통과"),
    ]

    for issue_idx, user_id, changes, note in journals:
        if issue_idx >= len(issue_ids):
            continue
        db.execute(
            text("""
                INSERT INTO ti_journals (issue_id, user_id, changes, note)
                VALUES (:iid, :uid, :changes::jsonb, :note)
            """),
            {
                "iid": issue_ids[issue_idx],
                "uid": user_id,
                "changes": changes,
                "note": note,
            },
        )

    db.commit()
    log.info("테스트 저널 %d건 생성", len(journals))


def create_time_entries(db: Session, issue_ids: list[int], user_ids: dict[str, int]) -> None:
    """테스트 시간기록 생성."""
    member_id  = user_ids["member@test.com"]
    dev1_id    = user_ids["dev1@test.com"]
    dev2_id    = user_ids["dev2@test.com"]

    if not issue_ids:
        return

    existing = db.execute(
        text("SELECT COUNT(*) FROM ti_time_entries WHERE issue_id = ANY(:ids)"),
        {"ids": issue_ids[:5]}
    ).scalar()
    if existing:
        log.info("테스트 시간기록 이미 존재, skip")
        return

    entries = [
        # (issue_idx, user_id, hours, activity, days_ago, description)
        (0, member_id, 4.0, "development", 6,  "로그인 UI 기본 구조 작성"),
        (0, member_id, 3.5, "development", 5,  "유효성 검사 로직 구현"),
        (1, dev1_id,   2.0, "development", 4,  "API 엔드포인트 라우터 작성"),
        (1, dev1_id,   2.0, "testing",     3,  "페이지네이션 테스트"),
        (5, dev1_id,   4.0, "development", 2,  "상태 전환 검증 로직"),
        (5, dev1_id,   3.0, "development", 1,  "에러 응답 처리"),
        (6, member_id, 8.0, "development", 3,  "DnD 라이브러리 통합"),
        (6, member_id, 6.0, "development", 2,  "저장 API 연결"),
        (7, dev1_id,   4.0, "development", 5,  "멀티파트 파싱"),
        (8, dev2_id,   6.0, "development", 4,  "리프레시 토큰 구현"),
        (8, dev2_id,   2.0, "testing",     3,  "토큰 재사용 공격 테스트"),
        (12, member_id, 3.0, "design",     1,  "상세 페이지 레이아웃"),
        (13, dev2_id,  4.0, "development", 3,  "마이그레이션 파일 작성"),
        (14, user_ids["admin@test.com"], 1.0, "other", 10, "Docker Compose 초기 구성"),
        (15, user_ids["admin@test.com"], 0.5, "other",  7, "seed 스크립트 작성"),
    ]

    for issue_idx, user_id, hours, activity, days_ago, description in entries:
        if issue_idx >= len(issue_ids):
            continue
        spent_on = (TODAY - timedelta(days=days_ago)).isoformat()
        db.execute(
            text("""
                INSERT INTO ti_time_entries (issue_id, user_id, hours, activity, spent_on, description)
                VALUES (:iid, :uid, :hours, :activity, :spent_on, :desc)
            """),
            {
                "iid": issue_ids[issue_idx],
                "uid": user_id,
                "hours": hours,
                "activity": activity,
                "spent_on": spent_on,
                "desc": description,
            },
        )

    db.commit()
    log.info("테스트 시간기록 %d건 생성", len(entries))


def run() -> None:
    print("=== TaskInsight 테스트 데이터 생성 ===")
    db = SessionLocal()
    try:
        user_ids = create_users(db)
        project_id = create_project(db, user_ids["admin@test.com"])
        add_project_members(db, project_id, user_ids)
        issue_ids = create_issues(db, project_id, user_ids)
        create_journals(db, issue_ids, user_ids)
        create_time_entries(db, issue_ids, user_ids)
        print("=== 테스트 데이터 생성 완료 ===")
        print()
        print("테스트 계정:")
        print("  admin@test.com   / TestAdmin123!   (system_admin)")
        print("  manager@test.com / TestManager123! (project_manager)")
        print("  member@test.com  / TestMember123!  (member)")
        print("  viewer@test.com  / TestViewer123!  (viewer)")
    except Exception as e:
        db.rollback()
        print(f"=== 테스트 데이터 생성 실패: {e} ===")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
