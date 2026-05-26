# TaskInsight 마스터 스펙 v3
> **작성일:** 2026-05-26
> **기준:** Spec_v2 + /grill-me 세션 결정사항 (업무관리 도구 통합)
> **상태:** 바이브 코딩 준비 완료

---

## 0. TL;DR — 30초 요약

- **제품명:** TaskInsight
- **포지션:** Redmine 데이터 분석(SEI) + 업무관리(이슈 트래커) 통합 플랫폼. 장기적으로 Redmine 완전 대체.
- **1차 사용자:** 팀장 + PM + 개발팀원 (중간관리자 → 전 팀원으로 확장)
- **기술 스택:** PostgreSQL 17 + TimescaleDB / FastAPI / Next.js 16 + Tailwind 4 / Ollama / Docker Compose
- **인증:** 이메일/비밀번호 + JWT, 4단계 역할
- **배포:** 사내 서버 Docker Compose
- **개발 전략:** MVP 없음 — 각 페이즈 완료 시 즉시 운영 투입 가능한 수준으로 개발

---

## 1. 제품 비전 & 결정 이력

### 1.1 핵심 결정사항 (grill-me 세션 2026-05-26)

| # | 결정 | 내용 |
|---|---|---|
| D19 | 플랫폼 위치 | TaskInsight 확장 — 분석 + 업무관리 통합. 별도 앱 아님. |
| D20 | Redmine 관계 | 장기 목표: Redmine 완전 대체. 단기: 일회성 마이그레이션 후 병행 없음. |
| D21 | 기능 범위 | 실무 대체 수준 — 이슈 CRUD + 프로젝트/버전/카테고리 + 파일첨부 + 코멘트 |
| D22 | 개발 전략 | MVP 없음. 각 페이즈 완료 = 운영 가능 상태. |
| D23 | 배포 | 사내 서버 + Docker Compose |
| D24 | 데이터 이전 | D-day 일회성 마이그레이션 (raw_redmine_* → ti_*). 이후 Redmine sync 중단. |
| D25 | 인증 | 이메일/비밀번호 + JWT. Redmine 사용자 데이터 이전 포함. |
| D26 | 이슈 계층 | 부모-자식(parent_id)만. 관계 타입(blocks/duplicates)은 v2. |
| D27 | 알림 | Teams Webhook + 이메일 알림 모두. |
| D28 | 커스텀 필드 | Redmine 기존 값 읽기 표시만. 신규 생성은 v2. |
| D29 | 타임 트래킹 | 수동 입력 + 프로젝트 합산 조회. Redmine 기존 데이터 이전. |
| D30 | 역할 | 4단계: system_admin / project_manager / member / viewer |
| D31 | 이슈 뷰 | 리스트(기본) + 칸반 보드 토글. 갠트는 v2. |
| D32 | 개발 페이즈 | 4페이즈 (기반 → 협업 → 심화 → 분석 통합) |

---

## 2. 사용자 & 역할

### 2.1 역할 정의

| 역할 | 코드 | 설명 |
|---|---|---|
| 시스템 관리자 | `system_admin` | 전체 시스템 설정, 사용자 관리, 모든 프로젝트 접근 |
| 프로젝트 관리자 | `project_manager` | 담당 프로젝트 설정, 멤버 관리, 이슈 전체 수정 |
| 팀원/개발자 | `member` | 이슈 CRUD, 코멘트, 파일 첨부, 타임 트래킹 |
| 뷰어 | `viewer` | 읽기 전용. 이슈/보고서 조회만 가능. |

### 2.2 역할별 권한 매트릭스

| 기능 | system_admin | project_manager | member | viewer |
|---|---|---|---|---|
| 사용자 관리 | ✅ | ❌ | ❌ | ❌ |
| 프로젝트 생성 | ✅ | ❌ | ❌ | ❌ |
| 프로젝트 설정 변경 | ✅ | ✅ (본인 프로젝트) | ❌ | ❌ |
| 버전/카테고리 관리 | ✅ | ✅ | ❌ | ❌ |
| 멤버 초대/제거 | ✅ | ✅ | ❌ | ❌ |
| 이슈 생성 | ✅ | ✅ | ✅ | ❌ |
| 이슈 수정 | ✅ | ✅ | ✅ (본인 + 담당) | ❌ |
| 이슈 삭제 | ✅ | ✅ | ❌ | ❌ |
| 코멘트 작성 | ✅ | ✅ | ✅ | ❌ |
| 파일 첨부 | ✅ | ✅ | ✅ | ❌ |
| 타임 트래킹 | ✅ | ✅ | ✅ | ❌ |
| 분석 대시보드 조회 | ✅ | ✅ | ✅ | ✅ |
| 주간보고 생성 | ✅ | ✅ | ❌ | ❌ |

---

## 3. 기술 스택

| Layer | Tech | 비고 |
|---|---|---|
| DB | PostgreSQL 17 + TimescaleDB | port 5433 |
| Backend | FastAPI + SQLAlchemy + psycopg3 | Python 3.9 |
| Frontend | Next.js 16 App Router + Tailwind 4 | port 3001 |
| LLM | Ollama localhost:11434 | qwen3.6:35b-a3b |
| 인증 | JWT (python-jose) + bcrypt | |
| 파일 저장 | 로컬 볼륨 (Docker volume mount) | |
| 이메일 | SMTP (smtplib / aiosmtplib) | |
| Teams 알림 | Incoming Webhook | |
| 배포 | Docker Compose | 사내 서버 |
| 마이그레이션 | Alembic | |

**Python 3.9 필수 규칙:**
- 모든 백엔드 파일 상단: `from __future__ import annotations`
- `Optional[X]` (not `X | None`), `Union[A, B]` (not `A | B`)

---

## 4. Docker Compose 구성

```yaml
# docker-compose.yml
version: '3.9'

services:
  db:
    image: timescale/timescaledb:latest-pg17
    ports:
      - "5433:5432"
    environment:
      POSTGRES_DB: taskinsight
      POSTGRES_USER: taskinsight
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+psycopg://taskinsight:${POSTGRES_PASSWORD}@db:5432/taskinsight
      - JWT_SECRET=${JWT_SECRET}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL}
      - SMTP_HOST=${SMTP_HOST}
      - SMTP_PORT=${SMTP_PORT}
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - TEAMS_WEBHOOK_URL=${TEAMS_WEBHOOK_URL}
    volumes:
      - uploads:/app/uploads
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3001:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - backend
      - frontend

volumes:
  pgdata:
  uploads:
```

---

## 5. DB 스키마

### 5.1 알림ic 마이그레이션 순서

```
0001_raw_redmine.py     — 기존 유지 (raw_redmine_* 읽기 전용 수집 테이블)
0002_mart.py            — 기존 유지 (fct_*, dim_* 분석 마트)
0003_mvp.py             — 기존 유지 (connector_instance, fct_issue_explanation, fct_weekly_report)
0004_auth.py            — 신규: ti_users, ti_sessions
0005_task_core.py       — 신규: ti_projects, ti_project_members, ti_versions, ti_categories,
                                  ti_issue_statuses, ti_issue_priorities, ti_issues
0006_task_collab.py     — 신규: ti_journals, ti_journal_details, ti_attachments, ti_watchers
0007_task_advanced.py   — 신규: ti_time_entries, ti_custom_field_values, ti_notifications
0008_analytics.py       — Phase 4: ETL 뷰/함수를 ti_* 기반으로 전환
```

### 5.2 인증 테이블

```sql
CREATE TABLE ti_users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name  VARCHAR(200) NOT NULL,
    role          VARCHAR(50) NOT NULL DEFAULT 'member',
                  -- 'system_admin' | 'project_manager' | 'member' | 'viewer'
    is_active     BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ti_sessions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES ti_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.3 프로젝트 테이블

```sql
CREATE TABLE ti_projects (
    id           SERIAL PRIMARY KEY,
    identifier   VARCHAR(100) UNIQUE NOT NULL,  -- URL slug (e.g. "manna-platform")
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    status       VARCHAR(20) DEFAULT 'active',  -- 'active' | 'archived' | 'closed'
    homepage     VARCHAR(255),
    is_public    BOOLEAN DEFAULT FALSE,
    created_by   INTEGER REFERENCES ti_users(id),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ti_project_members (
    id         SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ti_projects(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES ti_users(id) ON DELETE CASCADE,
    role       VARCHAR(50) NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

CREATE TABLE ti_versions (
    id           SERIAL PRIMARY KEY,
    project_id   INTEGER REFERENCES ti_projects(id) ON DELETE CASCADE,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    status       VARCHAR(20) DEFAULT 'open',  -- 'open' | 'locked' | 'closed'
    due_date     DATE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ti_categories (
    id         SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES ti_projects(id) ON DELETE CASCADE,
    name       VARCHAR(255) NOT NULL,
    UNIQUE(project_id, name)
);
```

### 5.4 이슈 관련 테이블

```sql
CREATE TABLE ti_issue_statuses (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    flow_stage VARCHAR(50) NOT NULL,
               -- 'backlog' | 'in_progress' | 'review' | 'rework' | 'blocked' | 'done' | 'rejected'
    is_closed  BOOLEAN DEFAULT FALSE,
    position   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE ti_issue_priorities (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(100) NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    color    VARCHAR(7) DEFAULT '#6B7280'  -- hex color
);

CREATE TABLE ti_issues (
    id               SERIAL PRIMARY KEY,
    project_id       INTEGER NOT NULL REFERENCES ti_projects(id),
    subject          VARCHAR(500) NOT NULL,
    description      TEXT,
    status_id        INTEGER REFERENCES ti_issue_statuses(id),
    priority_id      INTEGER REFERENCES ti_issue_priorities(id),
    assignee_id      INTEGER REFERENCES ti_users(id),
    author_id        INTEGER NOT NULL REFERENCES ti_users(id),
    parent_id        INTEGER REFERENCES ti_issues(id),       -- 부모 이슈
    version_id       INTEGER REFERENCES ti_versions(id),
    category_id      INTEGER REFERENCES ti_categories(id),
    start_date       DATE,
    due_date         DATE,
    estimated_hours  NUMERIC(6,2),
    done_ratio       INTEGER DEFAULT 0 CHECK (done_ratio BETWEEN 0 AND 100),
    is_private       BOOLEAN DEFAULT FALSE,
    closed_at        TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW(),
    -- Redmine 원본 ID (마이그레이션 추적용)
    redmine_id       INTEGER UNIQUE
);

-- 이슈 검색 성능
CREATE INDEX idx_ti_issues_project_id ON ti_issues(project_id);
CREATE INDEX idx_ti_issues_assignee_id ON ti_issues(assignee_id);
CREATE INDEX idx_ti_issues_status_id ON ti_issues(status_id);
CREATE INDEX idx_ti_issues_parent_id ON ti_issues(parent_id);
CREATE INDEX idx_ti_issues_updated_at ON ti_issues(updated_at DESC);
```

### 5.5 저널 (이력) 테이블

```sql
CREATE TABLE ti_journals (
    id         SERIAL PRIMARY KEY,
    issue_id   INTEGER NOT NULL REFERENCES ti_issues(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES ti_users(id),
    notes      TEXT,                    -- 코멘트 본문
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Redmine 원본 ID
    redmine_id INTEGER
);

CREATE TABLE ti_journal_details (
    id         SERIAL PRIMARY KEY,
    journal_id INTEGER NOT NULL REFERENCES ti_journals(id) ON DELETE CASCADE,
    property   VARCHAR(50) NOT NULL,    -- 'attr' | 'cf' | 'attachment'
    prop_key   VARCHAR(100) NOT NULL,   -- 'status_id' | 'assignee_id' | ...
    old_value  TEXT,
    new_value  TEXT
);

CREATE INDEX idx_ti_journals_issue_id ON ti_journals(issue_id);
```

### 5.6 협업 테이블

```sql
CREATE TABLE ti_attachments (
    id           SERIAL PRIMARY KEY,
    issue_id     INTEGER REFERENCES ti_issues(id) ON DELETE CASCADE,
    journal_id   INTEGER REFERENCES ti_journals(id) ON DELETE SET NULL,
    filename     VARCHAR(500) NOT NULL,
    content_type VARCHAR(200),
    filesize     INTEGER,
    storage_path VARCHAR(1000) NOT NULL,  -- Docker volume 내 상대 경로
    created_by   INTEGER REFERENCES ti_users(id),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ti_watchers (
    issue_id   INTEGER REFERENCES ti_issues(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES ti_users(id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, user_id)
);
```

### 5.7 타임 트래킹 + 커스텀 필드

```sql
CREATE TABLE ti_time_entries (
    id          SERIAL PRIMARY KEY,
    issue_id    INTEGER REFERENCES ti_issues(id) ON DELETE CASCADE,
    project_id  INTEGER NOT NULL REFERENCES ti_projects(id),
    user_id     INTEGER NOT NULL REFERENCES ti_users(id),
    hours       NUMERIC(6,2) NOT NULL,
    activity    VARCHAR(100),           -- '개발' | '테스트' | '설계' | ...
    spent_on    DATE NOT NULL,
    comments    TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    -- Redmine 원본 ID
    redmine_id  INTEGER
);

CREATE TABLE ti_custom_field_values (
    id          SERIAL PRIMARY KEY,
    issue_id    INTEGER NOT NULL REFERENCES ti_issues(id) ON DELETE CASCADE,
    field_name  VARCHAR(200) NOT NULL,
    field_value TEXT,
    UNIQUE(issue_id, field_name)
);
```

### 5.8 알림 테이블

```sql
CREATE TABLE ti_notifications (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES ti_users(id) ON DELETE CASCADE,
    event_type  VARCHAR(100) NOT NULL,
                -- 'issue_assigned' | 'issue_updated' | 'comment_added' | 'mentioned'
    payload     JSONB NOT NULL,
    is_read     BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ti_notifications_user_id ON ti_notifications(user_id, is_read);
```

---

## 6. 마이그레이션 스크립트 (Redmine → ti_*)

```python
# backend/scripts/migrate_from_redmine.py
# D-day 실행. raw_redmine_* → ti_* 일회성 변환.

def migrate_users():
    """raw_redmine_users → ti_users (임시 비밀번호 설정, 이메일 알림 필요)"""

def migrate_projects():
    """raw_redmine_projects → ti_projects"""

def migrate_issues():
    """raw_redmine_issues → ti_issues (redmine_id 보존)"""

def migrate_journals():
    """raw_redmine_journals → ti_journals + ti_journal_details (payload 파싱)"""

def migrate_time_entries():
    """raw_redmine_time_entries → ti_time_entries"""

def migrate_custom_field_values():
    """raw_redmine_issues.payload custom_fields → ti_custom_field_values"""

def run_migration():
    # 순서: users → projects → issues → journals → time_entries → custom_fields
    # 각 단계 실패 시 롤백 가능하도록 트랜잭션 분리
    pass
```

---

## 7. API 엔드포인트 (전체)

### 7.1 인증

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| POST | /v1/auth/login | 이메일/비밀번호 로그인 → JWT 반환 | 전체 |
| POST | /v1/auth/logout | 토큰 무효화 | 로그인 |
| GET | /v1/auth/me | 현재 사용자 정보 | 로그인 |
| PUT | /v1/auth/me | 프로필 수정 (이름, 비밀번호) | 로그인 |

### 7.2 사용자 관리

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| GET | /v1/users | 사용자 목록 | system_admin |
| POST | /v1/users | 사용자 생성 | system_admin |
| PUT | /v1/users/{id} | 사용자 수정 (역할 변경 포함) | system_admin |
| DELETE | /v1/users/{id} | 사용자 비활성화 | system_admin |

### 7.3 프로젝트

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| GET | /v1/projects | 접근 가능한 프로젝트 목록 | 로그인 |
| POST | /v1/projects | 프로젝트 생성 | system_admin |
| GET | /v1/projects/{id} | 프로젝트 상세 | 멤버 |
| PUT | /v1/projects/{id} | 프로젝트 수정 | system_admin, project_manager |
| DELETE | /v1/projects/{id} | 프로젝트 아카이브 | system_admin |
| GET | /v1/projects/{id}/members | 멤버 목록 | 멤버 |
| POST | /v1/projects/{id}/members | 멤버 추가 | system_admin, project_manager |
| DELETE | /v1/projects/{id}/members/{user_id} | 멤버 제거 | system_admin, project_manager |
| GET | /v1/projects/{id}/versions | 버전 목록 | 멤버 |
| POST | /v1/projects/{id}/versions | 버전 생성 | project_manager+ |
| PUT | /v1/projects/{id}/versions/{vid} | 버전 수정 | project_manager+ |
| GET | /v1/projects/{id}/categories | 카테고리 목록 | 멤버 |
| POST | /v1/projects/{id}/categories | 카테고리 생성 | project_manager+ |

### 7.4 이슈

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| GET | /v1/issues | 이슈 목록 (필터: project/status/assignee/priority/version/due) | 멤버+ |
| POST | /v1/issues | 이슈 생성 | member+ |
| GET | /v1/issues/{id} | 이슈 상세 + 저널 + 첨부파일 | 멤버+ |
| PUT | /v1/issues/{id} | 이슈 수정 (저널 자동 생성) | member+ |
| DELETE | /v1/issues/{id} | 이슈 삭제 | project_manager+ |
| GET | /v1/issues/{id}/children | 하위 이슈 목록 | 멤버+ |
| POST | /v1/issues/{id}/watchers | 관심 등록 | member+ |
| DELETE | /v1/issues/{id}/watchers | 관심 해제 | member+ |

### 7.5 저널 (코멘트)

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| POST | /v1/issues/{id}/journals | 코멘트 추가 | member+ |
| PUT | /v1/issues/{id}/journals/{jid} | 코멘트 수정 (본인만) | member+ |
| DELETE | /v1/issues/{id}/journals/{jid} | 코멘트 삭제 | project_manager+ |

### 7.6 파일 첨부

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| POST | /v1/issues/{id}/attachments | 파일 업로드 (multipart) | member+ |
| GET | /v1/attachments/{id} | 파일 다운로드 | 멤버+ |
| DELETE | /v1/attachments/{id} | 파일 삭제 | project_manager+ |

### 7.7 타임 트래킹

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| GET | /v1/issues/{id}/time_entries | 이슈별 시간 기록 | 멤버+ |
| POST | /v1/issues/{id}/time_entries | 시간 기록 추가 | member+ |
| PUT | /v1/time_entries/{id} | 시간 기록 수정 | member+ (본인) |
| DELETE | /v1/time_entries/{id} | 시간 기록 삭제 | member+ (본인) |
| GET | /v1/projects/{id}/time_entries | 프로젝트 공수 합산 | project_manager+ |

### 7.8 알림

| Method | Path | 설명 | 역할 |
|---|---|---|---|
| GET | /v1/notifications | 내 알림 목록 | 로그인 |
| PUT | /v1/notifications/{id}/read | 읽음 처리 | 로그인 |
| PUT | /v1/notifications/read_all | 전체 읽음 | 로그인 |

### 7.9 기존 분석 API (유지)

| Method | Path | 설명 |
|---|---|---|
| GET | /v1/flow/stages | 단계별 건수 + 평균 체류일 |
| GET | /v1/flow/issues | 이슈 목록 (분석용) |
| GET | /v1/flow/issue/{id}/explanation | LLM 타임라인 설명 |
| POST | /v1/reports/weekly/generate | 주간보고 생성 |
| GET | /v1/reports/weekly/latest | 최근 보고서 |
| GET | /v1/reports/weekly/history | 보고서 이력 |
| GET | /v1/dashboard/summary | Speed + Effectiveness + Quality |
| GET | /v1/connectors/instances | 연동 목록 |
| POST | /v1/connectors/test | 연결 테스트 |
| PUT | /v1/connectors/{id} | 연동 설정 수정 |
| POST | /v1/connectors/{id}/sync | 수동 동기화 (Phase 4 이후 deprecated) |

---

## 8. 화면 구성 (전체)

### 8.1 화면 목록

| 경로 | 화면명 | 설명 |
|---|---|---|
| `/login` | 로그인 | 이메일/비밀번호 |
| `/` | 홈 | 내 이슈 요약 + 최근 활동 |
| `/issues` | 전체 이슈 목록 | 리스트/칸반 뷰 토글 |
| `/issues/new` | 이슈 생성 | |
| `/issues/{id}` | 이슈 상세 | 저널, 첨부파일, 타임라인 |
| `/projects` | 프로젝트 목록 | |
| `/projects/{id}` | 프로젝트 홈 | 이슈 목록 + 버전/카테고리 사이드바 |
| `/projects/{id}/issues` | 프로젝트 이슈 | 리스트/칸반 |
| `/projects/{id}/settings` | 프로젝트 설정 | 버전/카테고리/멤버 관리 |
| `/flow` | 흐름 진단 | 기존 분석 화면 유지 |
| `/dashboard` | 분석 대시보드 | Speed/Effectiveness/Quality |
| `/reports/weekly` | 주간보고 | 기존 화면 유지 |
| `/settings` | 시스템 설정 | Redmine 연동 + 이메일/Teams 설정 |
| `/admin/users` | 사용자 관리 | system_admin만 |

### 8.2 이슈 목록 화면 (리스트 + 칸반)

```
┌─ 전체 이슈 ───────────────────────────────────────── [리스트 | 칸반] [+ 새 이슈] ┐
│ 필터: [프로젝트▾] [상태▾] [담당자▾] [우선순위▾] [버전▾]  [검색...]              │
│                                                                                   │
│ [리스트 뷰]                                                                        │
│  #      제목                      프로젝트     상태      담당자    기한     우선순위 │
│  10729  결제 모듈 검수 대기        만나 플랫폼  검수중    현복최   -        높음 🔴  │
│  8745   API 연동 재작업            만나 플랫폼  재작업    원배문   2026-06  보통     │
│                                                                                   │
│ [칸반 뷰]                                                                          │
│  ┌─대기중──┐  ┌─진행중──┐  ┌─검수중──┐  ┌─완료────┐                              │
│  │ 321건   │  │  85건   │  │  53건   │  │  38건   │                              │
│  │ #10123  │  │ #9876   │  │ #10729  │  │ #8001   │                              │
│  │ ...     │  │ ...     │  │ ...     │  │ ...     │                              │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘                              │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 이슈 상세 화면

```
┌─ #10729 결제 모듈 검수 대기 ──────────────────────────── [수정] [삭제] [관심등록] ┐
│                                                                                   │
│ 상태: 검수중  우선순위: 높음  담당자: 현복최  기한: -  진행률: 30%                │
│ 프로젝트: 만나 플랫폼  버전: v2.3  카테고리: 결제  등록자: 원배문                 │
│ 상위 이슈: #9000 결제 시스템 리팩토링                                             │
│                                                                                   │
│ 설명:                                                                             │
│ 결제 모듈 검수 요청건. 카드사 연동 부분 재확인 필요.                               │
│                                                                                   │
│ [커스텀 필드] (Redmine 이전 값 표시)                                               │
│  사업부: 플랫폼팀  고객사: 내부  예상공수: 16h                                    │
│                                                                                   │
│ ─────────── 하위 이슈 ─────────────────────────────────────────────────────────  │
│  #10730 카드사 연동 테스트  진행중  원배문                                         │
│                                                                                   │
│ ─────────── 활동 이력 ─────────────────────────────────────────────────────────  │
│  2024-12-15 원배문 이슈 생성                                                      │
│  2025-01-10 원배문 → 현복최 담당자 변경                                           │
│  2025-01-15 현복최: "검수 시작. 카드사 API 응답 확인 중"                          │
│                                                                                   │
│ ─────────── TaskInsight 분석 ──────────────────────────────────────── [재생성] ─  │
│  "검수 요청 후 1,300일이 경과됨. 검수자 재배정 검토를 권장함."                    │
│                                                                                   │
│ ─────────── 공수 기록 ────────────────────────────── [+ 시간 기록]  합계: 12.5h ─  │
│  2025-01-15  현복최  3.0h  테스트                                                │
│                                                                                   │
│ ─────────── 파일 첨부 ────────────────────────────────────────── [+ 파일 추가] ─  │
│  [검수체크리스트.xlsx]  [API응답샘플.json]                                        │
│                                                                                   │
│ [코멘트 작성...]                                                    [저장]         │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 사이드바 구조 (72px)

```
┌────┐
│ 🏠 │ 홈 (내 이슈)
│ 📋 │ 이슈
│ 📁 │ 프로젝트
├────┤
│ 📊 │ Flow 진단
│ 📈 │ Dashboard
│ 📝 │ 주간보고
├────┤
│ ⚙️ │ 설정
└────┘
```

---

## 9. 알림 시스템

### 9.1 알림 트리거 이벤트

| 이벤트 | 수신자 | Teams | 이메일 |
|---|---|---|---|
| 이슈 담당자 배정 | 담당자 | ✅ | ✅ |
| 이슈 상태 변경 | 담당자 + 관심 등록자 | ✅ | ✅ |
| 코멘트 추가 | 담당자 + 관심 등록자 | ✅ | ✅ |
| @멘션 | 멘션된 사용자 | ✅ | ✅ |
| 기한 D-1 | 담당자 | ✅ | ✅ |
| 이슈 마감 | 등록자 + 관심 등록자 | ✅ | ❌ |

### 9.2 구현 위치

```python
# backend/app/notifications/
#   dispatcher.py     — 이벤트 발생 시 Teams + 이메일 동시 발송
#   teams.py          — Incoming Webhook 페이로드 구성
#   email.py          — SMTP 발송 (aiosmtplib, 비동기)
#   templates/        — 이메일 HTML 템플릿
```

### 9.3 알림 설정

```python
# ti_users에 notification_settings JSONB 컬럼 추가
# {"email": true, "teams": true, "events": ["assigned", "mentioned"]}
```

---

## 10. 개발 페이즈 상세

### Phase 1 — 기반 (인증 + 프로젝트 + 이슈 CRUD)
**목표:** Redmine 대체 운영 가능한 기본 이슈 트래커

**백엔드:**
- [ ] Docker Compose 환경 구성 (DB + backend + frontend + nginx)
- [ ] Alembic 0004 (ti_users, ti_sessions)
- [ ] Alembic 0005 (ti_projects ~ ti_issues)
- [ ] JWT 인증 미들웨어 + 역할 권한 데코레이터
- [ ] `/v1/auth/*` 엔드포인트
- [ ] `/v1/users/*` 엔드포인트 (system_admin용)
- [ ] `/v1/projects/*` 엔드포인트
- [ ] `/v1/issues` CRUD 엔드포인트
- [ ] Redmine 마이그레이션 스크립트 (`scripts/migrate_from_redmine.py`)

**프론트엔드:**
- [ ] `/login` 화면
- [ ] 사이드바 업데이트 (8.4 구조)
- [ ] `/projects` 목록 + 상세 화면
- [ ] `/issues` 리스트 뷰 (필터/정렬 포함)
- [ ] `/issues/new` 생성 폼
- [ ] `/issues/{id}` 상세 (기본 정보 + 이력)
- [ ] 칸반 보드 뷰

**마이그레이션:**
- [ ] 마이그레이션 스크립트 테스트 (스테이징 DB)
- [ ] D-day 실행 + 검증

---

### Phase 2 — 협업 (코멘트 + 파일 + 알림)
**목표:** 팀 협업 기능 완성

**백엔드:**
- [ ] Alembic 0006 (ti_journals, ti_journal_details, ti_attachments, ti_watchers)
- [ ] Alembic 0007 부분 (ti_notifications)
- [ ] `/v1/issues/{id}/journals` 엔드포인트
- [ ] `/v1/issues/{id}/attachments` + `/v1/attachments/{id}` 엔드포인트
- [ ] `/v1/issues/{id}/watchers` 엔드포인트
- [ ] `/v1/notifications/*` 엔드포인트
- [ ] `notifications/dispatcher.py` — Teams + 이메일 발송
- [ ] @멘션 파싱 + 알림 트리거

**프론트엔드:**
- [ ] 이슈 상세: 코멘트 작성/수정
- [ ] 이슈 상세: 파일 첨부/다운로드
- [ ] 이슈 상세: 관심 등록/해제
- [ ] 알림 벨 아이콘 + 드롭다운 목록
- [ ] 설정 화면: Teams Webhook URL + SMTP 설정

---

### Phase 3 — 심화 (타임 트래킹 + 커스텀 필드)
**목표:** Redmine 실무 기능 완성

**백엔드:**
- [ ] Alembic 0007 나머지 (ti_time_entries, ti_custom_field_values)
- [ ] `/v1/issues/{id}/time_entries` 엔드포인트
- [ ] `/v1/projects/{id}/time_entries` 집계 엔드포인트
- [ ] 커스텀 필드 이슈 상세 API 포함

**프론트엔드:**
- [ ] 이슈 상세: 타임 트래킹 섹션 (기록 추가/목록/합계)
- [ ] 프로젝트: 공수 합산 뷰
- [ ] 이슈 상세: 커스텀 필드 표시 섹션
- [ ] 기한 D-1 알림 배치 스케줄러 추가

---

### Phase 4 — 분석 통합
**목표:** 기존 TaskInsight 분석 대시보드를 ti_* 테이블 기반으로 완전 전환

**백엔드:**
- [ ] Alembic 0008: ETL 뷰/함수 ti_* 기반으로 재작성
- [ ] `etl/populate.py` ti_issues → fct_* 변환 로직 교체
- [ ] `collector/` Redmine sync 비활성화
- [ ] 분석 API 검증 (flow/dashboard/reports)
- [ ] LLM 설명 캐시 ti_issues 기반으로 연동

**프론트엔드:**
- [ ] 분석 화면 데이터 소스 확인 (변경 최소화)
- [ ] 홈(`/`) 화면: 내 이슈 요약 + 최근 활동 구현

---

## 11. 기존 TaskInsight 분석 기능 (v2 유지)

Phase 1~3 동안 기존 분석 기능은 `raw_redmine_*` 기반으로 **그대로 운영**됩니다.

- `/flow`, `/dashboard`, `/reports/weekly`, `/settings` (Redmine 연동) — 변경 없음
- Phase 4에서 `ti_*` 기반으로 전환 후 Redmine sync 중단

---

## 12. 보안 규칙

```python
# JWT 토큰 구조
{
    "sub": user_id,
    "email": "user@example.com",
    "role": "member",
    "exp": timestamp
}

# 모든 API에 적용할 의존성
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> ti_users:
    ...

def require_role(*roles: str):
    def decorator(current_user: ti_users = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403)
    return decorator

# 프로젝트 멤버십 체크
def require_project_access(project_id: int, current_user: ti_users, db: Session):
    if current_user.role == "system_admin":
        return  # 전체 접근
    member = db.query(ti_project_members).filter_by(
        project_id=project_id, user_id=current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=403)
```

---

## 13. 디자인 토큰 (v2 유지)

```css
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

--color-critical: #DC2626;
--color-warning:  #F59E0B;
--color-normal:   #6B7280;
--color-good:     #059669;
--color-accent:   #2563EB;
```

**이슈 우선순위 색상:**
- 긴급: `#DC2626` (빨강)
- 높음: `#F59E0B` (주황)
- 보통: `#2563EB` (파랑)
- 낮음: `#6B7280` (회색)

---

## 14. 한국어 용어 사전 (v2 확장)

| 영문 | 한국어 |
|---|---|
| Issue | 이슈 |
| Project | 프로젝트 |
| Version / Milestone | 버전 |
| Category | 카테고리 |
| Journal | 활동 이력 |
| Attachment | 첨부 파일 |
| Watcher | 관심 등록 |
| Time Entry | 공수 기록 |
| Assignee | 담당자 |
| Author | 등록자 |
| Due Date | 기한 |
| Done Ratio | 진행률 |
| Parent Issue | 상위 이슈 |
| Child Issue | 하위 이슈 |
| Custom Field | 커스텀 필드 |
| system_admin | 시스템 관리자 |
| project_manager | 프로젝트 관리자 |
| member | 팀원 |
| viewer | 뷰어 |

---

## 15. v2+ 로드맵 (현재 범위 외)

| 기능 | 비고 |
|---|---|
| 이슈 관계 타입 (blocks/duplicates/precedes) | 부모-자식 이후 |
| 커스텀 필드 신규 생성/관리 | 읽기 표시 이후 |
| 갠트 차트 | 리스트+칸반 이후 |
| Wiki | 프로젝트 문서화 |
| 이메일로 이슈 생성 | IMAP 연동 |
| 팀즈 채널에서 이슈 생성 | Adaptive Card |
| PDF 내보내기 | 주간보고 |
| 인증 SSO | Tailscale + OIDC |
| 자연어 질의 | 한국어 Q&A |
| 처방 레이어 | prescription.py 룰 30~50개 |
| 다중 사용자 동시 편집 | WebSocket |
| 월간보고 | |

---

## 16. 새 대화에서 이어가기

> 첨부 `TaskInsight_Spec_v3.md` 기준으로 작업합니다.
>
> **현재 상태:** 설계 완료, Phase 1 개발 직전.
>
> **시작점:**
> 1. Docker Compose 환경 구성 (`docker-compose.yml`, `nginx.conf`)
> 2. Alembic 0004 (`ti_users`, `ti_sessions`) + JWT 인증 미들웨어
> 3. Alembic 0005 (`ti_projects` ~ `ti_issues`) + 기본 CRUD API
>
> **핵심 제약:**
> - Python 3.9: `from __future__ import annotations` 필수, `Optional[X]` 사용
> - psycopg3 (NOT psycopg2): JSONB 업데이트 시 `Jsonb()` 래핑
> - Phase 1~3: 기존 분석 기능(`/flow`, `/dashboard`, `/reports`) 건드리지 않음
> - MVP 없음: 각 페이즈 완료 = 즉시 운영 투입 가능 수준
>
> 본 문서의 모든 결정사항(특히 섹션 1.1 결정 이력)을 준수하고, 미결 사항은 반드시 확인 요청.

---

*TaskInsight Master Spec v3 — 2026-05-26*
