# TaskInsight — 바이브 코딩 가이드

> 이 파일을 읽은 AI는 아래 모든 결정사항을 준수합니다.
> 미결 사항이 있으면 구현 전 반드시 확인 요청합니다.
>
> **읽는 순서:**
> 1. `docs/CONTEXT.md` — 단일 진실 공급원 (Single Source of Truth). 아키텍처, 코딩 규칙 전체.
> 2. `docs/SCHEMA.md` — 완전한 DB 스키마 (테이블명, 컬럼, 인덱스)
> 3. `docs/API_SPEC.md` — 모든 API 요청/응답 명세
> 4. `docs/UI_SPEC.md` — 화면별 명세
> 5. `docs/SECURITY_SPEC.md` — 인증/인가 규칙
> 6. 이 파일(`CLAUDE.md`) — 추가 결정사항 및 구현 패턴
>
> **충돌 시:** `docs/` 폴더 내용이 우선합니다. 이 파일은 docs/를 보완합니다.

---

## 0. docs/와 다른 결정사항 (오늘 grill-me 세션 2026-05-26 확정)

아래 항목은 `docs/CONTEXT.md`와 충돌하며, **이 파일의 내용이 우선**합니다.

| 항목 | docs/ | 오늘 확정 | 이유 |
|---|---|---|---|
| 역할 체계 | 프로젝트 단위 역할 | **프로젝트 단위 역할 확정** (`is_system_admin` boolean 전역, 나머지는 `project_members.role`) | 전역 역할은 4개 프로젝트 100명 조직에서 첫 날 깨짐. `project_members` 테이블·API 설계 전체가 프로젝트 단위 전제. |
| Gantt 차트 | GanttChart.tsx 포함 | **v2로 연기** | 리스트+칸반 먼저 완성 후 추가 |
| 개발 전략 | MVP 개념 있음 | **MVP 없음. 각 페이즈 = 즉시 운영 가능 수준** | |
| 테이블 접두사 | `users`, `projects`, `issues` | **동일하게 사용** (ti_ 접두사 없음) | docs/ 스키마 준수 |

**역할 체계:**
- `users.is_system_admin` (boolean) — 전역. 모든 프로젝트에서 manager 권한.
- `project_members.role` (`manager` | `member` | `viewer`) — 프로젝트 단위.

**역할 매트릭스 (프로젝트 단위 역할 기준):**

| 기능 | system_admin | project manager | member | viewer |
|---|---|---|---|---|
| 사용자 관리 | ✅ | ❌ | ❌ | ❌ |
| 프로젝트 생성 | ✅ | ❌ | ❌ | ❌ |
| 프로젝트 설정 | ✅ | ✅ (해당 프로젝트) | ❌ | ❌ |
| 멤버 추가/제거 | ✅ | ✅ (해당 프로젝트) | ❌ | ❌ |
| 이슈 생성/수정 | ✅ | ✅ | ✅ | ❌ |
| 이슈 삭제 | ✅ | ✅ | ❌ | ❌ |
| 코멘트/파일/타임 | ✅ | ✅ | ✅ | ❌ |
| 분석 대시보드 조회 | ✅ | ✅ | ✅ | ✅ |
| 주간보고 생성 | ✅ | ✅ | ❌ | ❌ |

---

## 1. 프로젝트 한 줄 요약

Redmine 데이터 분석(SEI) + 업무관리(이슈 트래커) 통합 플랫폼.
장기 목표: 사내 Redmine 완전 대체. 현재: Phase 1 (인증 + 이슈 CRUD) 개발 중.

---

## 2. 기술 스택

| Layer | Tech | 주의 |
|---|---|---|
| DB | PostgreSQL 17 + TimescaleDB (port 5433) | |
| Backend | FastAPI 0.115+ + SQLAlchemy 2.0 + psycopg3 | psycopg2 절대 사용 금지 |
| Auth | python-jose + passlib[bcrypt] | |
| Frontend | Next.js 16 App Router + Tailwind 4 | |
| Data Fetching | SWR | React Query 사용 금지 |
| 파일 저장 | Docker volume (`/app/uploads`) | S3 사용 금지 (사내 서버) |
| LLM | Ollama qwen3.6:35b-a3b | think:false 필수 |
| 배포 | Docker Compose (사내 서버) | |

---

## 3. 디렉터리 구조

```
taskinsight/
├── docker-compose.yml
├── nginx.conf
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/versions/
│   │   ├── 0001_raw_redmine.py
│   │   ├── 0002_mart.py
│   │   ├── 0003_mvp.py
│   │   ├── 0004_auth.py          ← users, user_refresh_tokens
│   │   ├── 0005_task_core.py     ← projects, project_members, workflow_statuses, workflow_transitions, issues
│   │   ├── 0006_task_collab.py   ← issue_journals, issue_attachments, milestones, time_entries
│   │   └── 0007_task_advanced.py ← notifications
│   └── app/
│       ├── config.py
│       ├── db.py
│       ├── deps.py               ← get_current_user, require_role, require_project_access
│       ├── api/
│       │   ├── main.py
│       │   └── routers/
│       │       ├── auth.py
│       │       ├── users.py
│       │       ├── projects.py
│       │       ├── issues.py
│       │       ├── journals.py
│       │       ├── attachments.py
│       │       ├── time_entries.py
│       │       ├── notifications.py
│       │       ├── flow.py       ← 기존 유지
│       │       ├── dashboard.py  ← 기존 유지
│       │       ├── reports.py    ← 기존 유지
│       │       └── connectors.py ← 기존 유지
│       ├── models/               ← SQLAlchemy ORM 모델
│       │   ├── auth.py
│       │   ├── task.py
│       │   └── analytics.py      ← 기존 raw_redmine_*, fct_* 모델
│       ├── schemas/              ← Pydantic v2 요청/응답 스키마
│       │   ├── auth.py
│       │   ├── projects.py
│       │   ├── issues.py
│       │   └── common.py         ← ErrorResponse, PaginatedResponse
│       ├── notifications/
│       │   ├── dispatcher.py
│       │   ├── teams.py
│       │   └── email.py
│       ├── scripts/
│       │   └── migrate_from_redmine.py
│       ├── connectors/           ← 기존 유지
│       ├── collector/            ← 기존 유지 (Phase 4에서 deprecated)
│       ├── etl/                  ← 기존 유지
│       ├── analytics/            ← 기존 유지
│       ├── narrator/             ← 기존 유지
│       └── scheduler.py          ← 기존 유지
└── frontend/
    ├── Dockerfile
    ├── app/
    │   ├── (auth)/login/page.tsx
    │   ├── (app)/layout.tsx      ← 인증 필요 레이아웃 + 사이드바
    │   ├── (app)/page.tsx        ← 홈: 내 이슈 요약
    │   ├── (app)/issues/page.tsx
    │   ├── (app)/issues/new/page.tsx
    │   ├── (app)/issues/[id]/page.tsx
    │   ├── (app)/projects/page.tsx
    │   ├── (app)/projects/[id]/page.tsx
    │   ├── (app)/projects/[id]/settings/page.tsx
    │   ├── (app)/flow/page.tsx   ← 기존 유지
    │   ├── (app)/dashboard/page.tsx ← 기존 유지
    │   ├── (app)/reports/weekly/page.tsx ← 기존 유지
    │   └── (app)/settings/page.tsx ← 기존 유지
    ├── components/
    │   ├── issues/
    │   │   ├── IssueList.tsx
    │   │   ├── IssueKanban.tsx
    │   │   ├── IssueForm.tsx
    │   │   └── IssueDetail.tsx
    │   ├── projects/
    │   └── ui/                   ← 공용 컴포넌트
    └── lib/
        ├── api.ts                ← 기존 + 신규 API 클라이언트
        ├── auth.ts               ← JWT 저장/로드/만료 처리
        └── swr-hooks.ts          ← useSWR 커스텀 훅 모음
```

---

## 4. 백엔드 코딩 패턴

### 4.1 파일 최상단 (모든 백엔드 파일)

```python
from __future__ import annotations
```

### 4.2 SQLAlchemy 모델 패턴

```python
# app/models/auth.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_system_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 4.3 Pydantic v2 스키마 패턴

```python
# app/schemas/common.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar("T")

class ErrorResponse(BaseModel):
    detail: str
    code: str = "ERROR"

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
```

```python
# app/schemas/issues.py
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class IssueCreate(BaseModel):
    project_id: int
    subject: str
    description: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    version_id: Optional[int] = None
    category_id: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None

class IssueUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    version_id: Optional[int] = None
    category_id: Optional[int] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    done_ratio: Optional[int] = None
    notes: Optional[str] = None  # 변경 시 코멘트 (저널에 저장)

class IssueOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    subject: str
    description: Optional[str]
    status_id: Optional[int]
    status_name: Optional[str]
    priority_id: Optional[int]
    priority_name: Optional[str]
    assignee_id: Optional[int]
    assignee_name: Optional[str]
    author_id: int
    author_name: str
    parent_id: Optional[int]
    done_ratio: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
```

### 4.4 인증 의존성 패턴

```python
# app/deps.py
from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.auth import User
from app.models.task import ProjectMember
from app.config import settings
from typing import Optional

ROLE_RANK = {"viewer": 0, "member": 1, "manager": 2}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id: int = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="시스템 관리자 권한이 필요합니다")
    return current_user

def get_project_member(
    project_id: int,
    db: Session,
    current_user: User,
) -> Optional[ProjectMember]:
    """system_admin은 None 반환 (모든 프로젝트 접근 허용). 일반 사용자는 멤버십 반환."""
    if current_user.is_system_admin:
        return None
    member = db.query(ProjectMember).filter_by(
        project_id=project_id, user_id=current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="프로젝트 접근 권한이 없습니다")
    return member

def require_project_role(project_id: int, min_role: str):
    """min_role 이상인 프로젝트 멤버만 허용. system_admin은 항상 통과."""
    def dep(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.is_system_admin:
            return current_user
        member = db.query(ProjectMember).filter_by(
            project_id=project_id, user_id=current_user.id
        ).first()
        if not member or ROLE_RANK.get(member.role, -1) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403, detail="권한이 없습니다")
        return current_user
    return dep
```

### 4.5 라우터 패턴

```python
# app/api/routers/issues.py
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user, get_project_member, ROLE_RANK
from app.models.auth import User
from app.models.task import Issue
from app.schemas.issues import IssueCreate, IssueUpdate, IssueOut
from app.schemas.common import PaginatedResponse
from typing import Optional

router = APIRouter()

@router.get("", response_model=PaginatedResponse[IssueOut])
def list_issues(
    project_id: Optional[int] = Query(None),
    status_id: Optional[int] = Query(None),
    assignee_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Issue)
    if project_id:
        q = q.filter(Issue.project_id == project_id)
    if status_id:
        q = q.filter(Issue.status_id == status_id)
    if assignee_id:
        q = q.filter(Issue.assignee_id == assignee_id)
    total = q.count()
    items = q.order_by(Issue.updated_at.desc()).offset(offset).limit(limit).all()
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

@router.post("", response_model=IssueOut, status_code=201)
def create_issue(
    body: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # member 이상만 생성 가능 — viewer는 403
    member = get_project_member(body.project_id, db, current_user)
    if member and ROLE_RANK.get(member.role, -1) < ROLE_RANK["member"]:
        raise HTTPException(status_code=403)
    issue = Issue(**body.model_dump(), author_id=current_user.id)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    # 알림 dispatch (비동기 처리)
    from app.notifications.dispatcher import dispatch_issue_event
    dispatch_issue_event("issue_created", issue, current_user, db)
    return issue
```

### 4.6 psycopg3 / JSONB 패턴

```python
# JSONB 컬럼 업데이트 — 반드시 Jsonb() 래핑
from psycopg.types.json import Jsonb
db.execute(
    text("UPDATE connector_instance SET config = :config WHERE id = :id"),
    {"config": Jsonb(merged_dict), "id": instance_id}
)

# LAG() OVER in UPDATE 불가 → CTE로 계산 후 JOIN UPDATE
```

### 4.7 API 에러 응답 표준

```python
# 모든 에러는 아래 형식으로 통일
# {"detail": "에러 메시지", "code": "ERROR_CODE"}

# HTTP 상태 코드 사용 기준:
# 400 — 잘못된 요청 (입력값 오류)
# 401 — 인증 없음/토큰 만료
# 403 — 권한 없음
# 404 — 리소스 없음
# 409 — 중복 (이메일 중복 등)
# 422 — Pydantic 검증 실패 (FastAPI 기본)
# 500 — 서버 오류
```

### 4.8 페이지네이션 표준

```python
# offset 기반. limit 기본 50, 최대 200.
# 응답: {"items": [...], "total": 321, "limit": 50, "offset": 0}

# URL 예시: GET /v1/issues?limit=50&offset=100
```

---

## 5. 이슈 수정 시 저널 자동 생성

이슈가 수정될 때마다 변경 이력을 `ti_journals` + `ti_journal_details`에 자동 저장합니다.

```python
def create_journal_for_update(
    db: Session,
    issue: TiIssue,
    update_data: dict,
    user_id: int,
    notes: Optional[str] = None
) -> None:
    """이슈 수정 시 호출. 변경된 필드만 journal_details에 기록."""
    changed_fields = []
    trackable = ["status_id", "priority_id", "assignee_id", "version_id",
                 "category_id", "due_date", "done_ratio", "parent_id"]
    for field in trackable:
        if field in update_data:
            old_val = str(getattr(issue, field)) if getattr(issue, field) is not None else None
            new_val = str(update_data[field]) if update_data[field] is not None else None
            if old_val != new_val:
                changed_fields.append({"prop_key": field, "old_value": old_val, "new_value": new_val})

    if not changed_fields and not notes:
        return  # 변경 없으면 저널 생성 안 함

    journal = Journal(issue_id=issue.id, user_id=user_id, notes=notes)
    db.add(journal)
    db.flush()
    for cf in changed_fields:
        db.add(JournalDetail(journal_id=journal.id, property="attr", **cf))
```

---

## 6. 알림 발송 패턴

```python
# app/notifications/dispatcher.py
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.notifications.teams import send_teams_notification
from app.notifications.email import send_email_notification

_executor = ThreadPoolExecutor(max_workers=4)

def dispatch_issue_event(
    event_type: str,   # "issue_assigned" | "issue_updated" | "comment_added" | "mentioned"
    issue,
    actor,             # 이벤트를 발생시킨 사용자
    db,
    extra: dict = {}
) -> None:
    """비동기로 Teams + 이메일 동시 발송. API 응답을 블로킹하지 않음."""
    recipients = _get_recipients(event_type, issue, db)
    payload = _build_payload(event_type, issue, actor, extra)

    for user in recipients:
        if user.id == actor.id:
            continue  # 본인에게는 알림 안 보냄
        _executor.submit(send_teams_notification, payload)
        _executor.submit(send_email_notification, user.email, payload)
        # DB 알림 레코드도 저장
        from app.models.task import Notification
        db.add(Notification(user_id=user.id, event_type=event_type, payload=payload))
    db.commit()
```

---

## 7. 프론트엔드 코딩 패턴

### 7.1 인증 토큰 관리

```typescript
// lib/auth.ts
const TOKEN_KEY = "ti_token";

export function saveToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}
```

### 7.2 API 클라이언트 패턴 (기존 확장)

```typescript
// lib/api.ts 에 추가할 패턴
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (res.status === 401) {
    removeToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `API ${res.status}`);
  }
  return res.json() as Promise<T>;
}
```

### 7.3 SWR 커스텀 훅 패턴

```typescript
// lib/swr-hooks.ts
import useSWR from "swr";
import { fetchIssues, IssuesResponse } from "./api";

export function useIssues(params: Parameters<typeof fetchIssues>[0]) {
  const key = ["issues", params] as const;
  return useSWR(key, () => fetchIssues(params), {
    revalidateOnFocus: false,
    keepPreviousData: true,
  });
}
```

### 7.4 인증 미들웨어 (Next.js middleware.ts)

```typescript
// middleware.ts (루트)
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("ti_token")?.value;
  const isPublic = PUBLIC_PATHS.some((p) => request.nextUrl.pathname.startsWith(p));

  if (!isPublic && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

### 7.5 파일 업로드 제한

```
최대 파일 크기: 20MB
허용 확장자: .jpg .jpeg .png .gif .pdf .doc .docx .xls .xlsx .ppt .pptx .zip .txt .md .csv
업로드 경로: POST /v1/issues/{id}/attachments (multipart/form-data)
저장 경로: Docker volume /app/uploads/{issue_id}/{uuid}_{filename}
```

---

## 8. 이슈 번호 체계

- **전역 순번**: `ti_issues.id` (SERIAL). 이슈 번호 = `#ID`.
- 프로젝트별 번호 없음. `#10729` 같이 전역 ID로 참조.
- Redmine 마이그레이션 시 `redmine_id` 컬럼에 원본 번호 보존.
- UI에서 `#` prefix 표시: `#10729 결제 모듈 검수 대기`

---

## 9. 해야 할 것 / 하지 말아야 할 것

### 해야 할 것

- `from __future__ import annotations` — 모든 백엔드 파일 상단
- psycopg3 사용 (`psycopg`, NOT `psycopg2`)
- JSONB 업데이트 시 `Jsonb()` 래핑
- 모든 API 응답에 `PaginatedResponse` 또는 단일 Pydantic 스키마 사용
- 이슈 수정 시 `create_journal_for_update()` 호출
- 알림 발송 시 `dispatch_issue_event()` 사용 (API 응답 블로킹 금지)
- Docker volume mount 경로 `/app/uploads` 사용
- 에러 응답: `{"detail": "메시지", "code": "ERROR_CODE"}` 형식

### 하지 말아야 할 것

- `psycopg2` import 절대 금지
- `LAG() OVER` in UPDATE — CTE로 대체
- Redmine sync 건드리기 (Phase 1~3에서 기존 `/v1/flow`, `/v1/dashboard`, `/v1/reports`, `/v1/connectors` 변경 금지)
- 개인 비교 엔드포인트 (`/v1/users/compare` 등) 생성 금지
- 개인에게 단일 점수 부여하는 API 생성 금지
- `viewer` 역할에게 쓰기 권한 부여 금지
- S3 / 외부 스토리지 사용 금지 (사내 서버 로컬 볼륨만)
- React Query 사용 금지 (SWR 사용)

---

## 10. Phase 1 완료 체크리스트

Phase 1 완료 기준 — 아래 모두 통과 시 운영 투입 가능:

### 백엔드
- [ ] `docker-compose up` 으로 전체 스택 기동
- [ ] `POST /v1/auth/login` → JWT 반환
- [ ] `GET /v1/auth/me` → 현재 사용자 정보
- [ ] `GET /v1/projects` → 프로젝트 목록 (viewer 이상 접근)
- [ ] `POST /v1/projects` → 프로젝트 생성 (system_admin만)
- [ ] `GET /v1/issues` → 필터/페이지네이션 동작
- [ ] `POST /v1/issues` → 이슈 생성 + 저널 자동 생성
- [ ] `PUT /v1/issues/{id}` → 이슈 수정 + 저널 자동 생성
- [ ] `DELETE /v1/issues/{id}` → project_manager 이상만
- [ ] Alembic 0004, 0005 마이그레이션 clean run
- [ ] seed data 적용 (이슈 상태 8개, 우선순위 4개, system_admin 계정 1개)
- [ ] `scripts/migrate_from_redmine.py` 실행 후 이슈 건수 검증

### 프론트엔드
- [ ] `/login` 로그인 → JWT 저장 → 홈 redirect
- [ ] 비로그인 상태에서 보호 경로 접근 시 `/login` redirect
- [ ] `/issues` 리스트 뷰 + 필터 동작
- [ ] `/issues` 칸반 뷰 토글
- [ ] `/issues/new` 이슈 생성 폼 제출
- [ ] `/issues/{id}` 이슈 상세 + 이력 표시
- [ ] `/projects` 목록 + `/projects/{id}` 프로젝트 홈

---

## 11. 환경 변수 (.env)

`.env.example` 파일 참조. 실제 `.env` 파일은 Git에 커밋하지 않음.

---

## 12. 서버 시작 명령 (Docker)

```bash
# 전체 기동
docker-compose up -d

# 마이그레이션
docker-compose exec backend alembic upgrade head

# Seed 데이터
docker-compose exec backend python -m app.scripts.seed

# Redmine 마이그레이션 (D-day)
docker-compose exec backend python -m app.scripts.migrate_from_redmine

# 로그 확인
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## 13. 기존 기능 유지 규칙 (Phase 1~3)

아래 파일/경로는 **절대 수정 금지**:

```
backend/app/api/routers/flow.py
backend/app/api/routers/dashboard.py
backend/app/api/routers/reports.py
backend/app/api/routers/connectors.py
backend/app/analytics/
backend/app/collector/
backend/app/etl/
backend/app/narrator/
backend/app/scheduler.py
frontend/app/flow/
frontend/app/dashboard/
frontend/app/reports/
frontend/app/settings/       ← Redmine 연동 설정 유지
```

Phase 4에서 ETL을 `ti_*` 기반으로 전환할 때 수정.
