# TaskInsight — 완전한 DB 스키마

> Alembic 마이그레이션: `0004_issue_management.py`
> 기존 0001~0003 테이블은 유지. 신규 테이블만 이 파일에 정의.

---

## 신규 테이블 (0004 마이그레이션)

### users
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    is_system_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    login_fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_is_active ON users (is_active);
```

### user_refresh_tokens
```sql
CREATE TABLE user_refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,  -- SHA-256 해시
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_at     TIMESTAMPTZ,        -- 사용된 시각 (재사용 감지)
    revoked     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_refresh_tokens_user_id ON user_refresh_tokens (user_id);
CREATE INDEX ix_refresh_tokens_token_hash ON user_refresh_tokens (token_hash);
```

### projects
```sql
CREATE TABLE projects (
    id                  SERIAL PRIMARY KEY,
    identifier          VARCHAR(100) NOT NULL UNIQUE,  -- URL slug, 변경 불가
    name                VARCHAR(200) NOT NULL,
    description         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    default_assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by_id       UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_projects_identifier ON projects (identifier);
CREATE INDEX ix_projects_is_active ON projects (is_active);
```

### project_members
```sql
CREATE TYPE project_role AS ENUM ('manager', 'member', 'viewer');

CREATE TABLE project_members (
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        project_role NOT NULL DEFAULT 'member',
    added_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

CREATE INDEX ix_project_members_user_id ON project_members (user_id);
```

### workflow_statuses
```sql
CREATE TABLE workflow_statuses (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    color       VARCHAR(7) NOT NULL DEFAULT '#6B7280',  -- hex color
    position    INTEGER NOT NULL DEFAULT 0,
    is_closed   BOOLEAN NOT NULL DEFAULT FALSE,   -- 완료 계열 여부
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,   -- 신규 이슈 기본 상태
    flow_stage  VARCHAR(20) NOT NULL DEFAULT 'backlog',
                -- CHECK (flow_stage IN ('backlog','in_progress','review','done','blocked'))
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_workflow_statuses_project_id ON workflow_statuses (project_id);
CREATE UNIQUE INDEX ix_workflow_statuses_default
    ON workflow_statuses (project_id) WHERE is_default = TRUE;
```

### workflow_transitions
```sql
CREATE TABLE workflow_transitions (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    from_status_id  INTEGER REFERENCES workflow_statuses(id) ON DELETE CASCADE,
    to_status_id    INTEGER NOT NULL REFERENCES workflow_statuses(id) ON DELETE CASCADE,
    allowed_roles   JSONB NOT NULL DEFAULT '["manager","member"]'::jsonb
    -- 예: ["manager"] or ["manager","member"] or ["manager","member","viewer"]
);

CREATE INDEX ix_workflow_transitions_project_id ON workflow_transitions (project_id);
CREATE INDEX ix_workflow_transitions_from_status ON workflow_transitions (from_status_id);
```

### milestones
```sql
CREATE TABLE milestones (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'open',
                    -- CHECK (status IN ('open', 'closed'))
    start_date      DATE,
    due_date        DATE,
    created_by_id   UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_milestones_project_id ON milestones (project_id);
CREATE INDEX ix_milestones_status ON milestones (status);
```

### issues
```sql
CREATE TYPE issue_priority AS ENUM ('low', 'normal', 'high', 'urgent');
CREATE TYPE issue_tracker  AS ENUM ('task', 'bug', 'feature', 'improvement');

CREATE TABLE issues (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id),
    status_id       INTEGER NOT NULL REFERENCES workflow_statuses(id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    reporter_id     UUID NOT NULL REFERENCES users(id),
    assignee_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    priority        issue_priority NOT NULL DEFAULT 'normal',
    tracker         issue_tracker NOT NULL DEFAULT 'task',
    milestone_id    INTEGER REFERENCES milestones(id) ON DELETE SET NULL,
    parent_issue_id INTEGER REFERENCES issues(id) ON DELETE SET NULL,
    start_date      DATE,
    due_date        DATE,
    estimated_hours NUMERIC(6,1),
    done_ratio      INTEGER NOT NULL DEFAULT 0
                    CHECK (done_ratio >= 0 AND done_ratio <= 100),
    closed_at       TIMESTAMPTZ,
    source_type     VARCHAR(20) NOT NULL DEFAULT 'internal',
                    -- 'internal' | 'redmine_migrated'
    external_id     INTEGER,            -- Redmine issue ID (마이그레이션 시)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_issues_project_id      ON issues (project_id);
CREATE INDEX ix_issues_status_id       ON issues (status_id);
CREATE INDEX ix_issues_assignee_id     ON issues (assignee_id);
CREATE INDEX ix_issues_milestone_id    ON issues (milestone_id);
CREATE INDEX ix_issues_parent_issue_id ON issues (parent_issue_id);
CREATE INDEX ix_issues_created_at      ON issues (created_at);
CREATE INDEX ix_issues_updated_at      ON issues (updated_at);
CREATE INDEX ix_issues_closed_at       ON issues (closed_at);
CREATE INDEX ix_issues_external_id     ON issues (external_id) WHERE external_id IS NOT NULL;
```

### issue_journals
```sql
CREATE TABLE issue_journals (
    id          SERIAL PRIMARY KEY,
    issue_id    INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id),
    changes     JSONB NOT NULL DEFAULT '{}'::jsonb,
    note        TEXT,           -- 댓글 내용 (없으면 NULL)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_issue_journals_issue_id   ON issue_journals (issue_id);
CREATE INDEX ix_issue_journals_user_id    ON issue_journals (user_id);
CREATE INDEX ix_issue_journals_created_at ON issue_journals (created_at);
```

### time_entries
```sql
CREATE TYPE time_activity AS ENUM
    ('development', 'review', 'design', 'meeting', 'testing', 'other');

CREATE TABLE time_entries (
    id          SERIAL PRIMARY KEY,
    issue_id    INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id),
    hours       NUMERIC(5,1) NOT NULL CHECK (hours > 0 AND hours <= 24),
    activity    time_activity NOT NULL DEFAULT 'development',
    spent_on    DATE NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_time_entries_issue_id  ON time_entries (issue_id);
CREATE INDEX ix_time_entries_user_id   ON time_entries (user_id);
CREATE INDEX ix_time_entries_spent_on  ON time_entries (spent_on);
```

### issue_attachments
```sql
CREATE TABLE issue_attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id        INTEGER NOT NULL REFERENCES issues(id) ON DELETE CASCADE,
    uploader_id     UUID NOT NULL REFERENCES users(id),
    filename        VARCHAR(500) NOT NULL,      -- 원본 파일명
    stored_path     VARCHAR(1000) NOT NULL,     -- 서버 저장 경로 (상대)
    content_type    VARCHAR(200) NOT NULL,
    file_size       BIGINT NOT NULL,            -- bytes
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_issue_attachments_issue_id ON issue_attachments (issue_id);
```

### notifications
```sql
CREATE TABLE notifications (
    id          SERIAL PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        VARCHAR(50) NOT NULL,
    issue_id    INTEGER REFERENCES issues(id) ON DELETE CASCADE,
    actor_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    message     VARCHAR(500) NOT NULL,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_notifications_user_id   ON notifications (user_id);
CREATE INDEX ix_notifications_is_read   ON notifications (user_id, is_read);
CREATE INDEX ix_notifications_created_at ON notifications (created_at);
```

---

## 기존 테이블 변경 (ALTER)

### fct_issue_snapshot — source_type 컬럼 추가
```sql
ALTER TABLE fct_issue_snapshot
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'redmine',
    ADD COLUMN IF NOT EXISTS internal_issue_id INTEGER REFERENCES issues(id);
-- source_type: 'internal' | 'redmine'
```

### dim_status — 기존 Redmine 상태 매핑 테이블 유지
```sql
-- 기존 그대로 유지. 신규 이슈는 workflow_statuses.flow_stage를 직접 사용.
```

---

## 초기 데이터 시드 (마이그레이션 스크립트 내)

### 시스템 관리자 계정 (설치 시 생성)
```python
# 비밀번호는 설치 스크립트에서 환경변수로 받음
INSERT INTO users (email, password_hash, display_name, is_system_admin)
VALUES ('admin@company.com', '{bcrypt_hash}', '시스템 관리자', TRUE);
```

### 기본 워크플로우 (프로젝트 생성 시 자동 시드)
```python
# 프로젝트 생성 API에서 트리거
DEFAULT_STATUSES = [
    {"name": "대기 중",  "color": "#6B7280", "position": 1,
     "is_default": True,  "is_closed": False, "flow_stage": "backlog"},
    {"name": "진행 중",  "color": "#2563EB", "position": 2,
     "is_default": False, "is_closed": False, "flow_stage": "in_progress"},
    {"name": "검수 중",  "color": "#F59E0B", "position": 3,
     "is_default": False, "is_closed": False, "flow_stage": "review"},
    {"name": "완료",     "color": "#059669", "position": 4,
     "is_default": False, "is_closed": True,  "flow_stage": "done"},
    {"name": "보류됨",   "color": "#DC2626", "position": 5,
     "is_default": False, "is_closed": False, "flow_stage": "blocked"},
]

DEFAULT_TRANSITIONS = [
    # from_status_id=None → 신규 이슈 초기 상태
    {"from": None,        "to": "대기 중",  "roles": ["manager","member"]},
    {"from": "대기 중",   "to": "진행 중",  "roles": ["manager","member"]},
    {"from": "진행 중",   "to": "대기 중",  "roles": ["manager","member"]},
    {"from": "진행 중",   "to": "검수 중",  "roles": ["manager","member"]},
    {"from": "검수 중",   "to": "진행 중",  "roles": ["manager","member"]},
    {"from": "검수 중",   "to": "완료",     "roles": ["manager"]},
    {"from": "완료",      "to": "진행 중",  "roles": ["manager"]},  # 재오픈
    # 어디서든 보류됨으로
    {"from": "대기 중",   "to": "보류됨",   "roles": ["manager","member"]},
    {"from": "진행 중",   "to": "보류됨",   "roles": ["manager","member"]},
    {"from": "검수 중",   "to": "보류됨",   "roles": ["manager","member"]},
    {"from": "보류됨",    "to": "진행 중",  "roles": ["manager","member"]},
]
```

---

## 쿼리 패턴 (자주 사용되는 복잡 쿼리)

### 이슈 목록 조회 (권한 포함)
```sql
SELECT
    i.id, i.title, i.priority, i.tracker,
    ws.name AS status_name, ws.color AS status_color, ws.flow_stage,
    u_assignee.display_name AS assignee_name,
    u_reporter.display_name AS reporter_name,
    m.name AS milestone_name,
    i.due_date, i.done_ratio, i.created_at, i.updated_at,
    EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 86400.0 AS age_days
FROM issues i
JOIN workflow_statuses ws ON ws.id = i.status_id
LEFT JOIN users u_assignee ON u_assignee.id = i.assignee_id
LEFT JOIN users u_reporter ON u_reporter.id = i.reporter_id
LEFT JOIN milestones m ON m.id = i.milestone_id
WHERE i.project_id = :project_id
  AND (
    EXISTS (SELECT 1 FROM project_members pm
            WHERE pm.project_id = i.project_id AND pm.user_id = :current_user_id)
    OR :is_system_admin = TRUE
  )
ORDER BY i.updated_at DESC
LIMIT :limit OFFSET :offset;
```

### 허용된 상태 전환 조회
```sql
SELECT wt.to_status_id, ws.name, ws.color
FROM workflow_transitions wt
JOIN workflow_statuses ws ON ws.id = wt.to_status_id
WHERE wt.from_status_id = :current_status_id
  AND wt.project_id = :project_id
  AND wt.allowed_roles @> :user_role::jsonb;
-- :user_role 예: '"member"'::jsonb
```

### ETL 부분 갱신 — 단일 이슈 스냅샷 업데이트
```sql
INSERT INTO fct_issue_snapshot
    (issue_id, project_id, subject, current_status_id, flow_stage,
     assigned_to_id, created_on, updated_on, closed_on,
     total_days, days_in_stage, risk_score, is_rework, source_type, internal_issue_id, _etl_at)
SELECT
    i.id, i.project_id, i.title, i.status_id, ws.flow_stage,
    i.assignee_id, i.created_at, i.updated_at, i.closed_at,
    EXTRACT(EPOCH FROM (NOW() - i.created_at)) / 86400.0,
    EXTRACT(EPOCH FROM (NOW() - COALESCE(
        (SELECT MAX(ij.created_at) FROM issue_journals ij
         WHERE ij.issue_id = i.id AND ij.changes ? 'status_id'),
        i.created_at
    ))) / 86400.0,
    0, FALSE, 'internal', i.id, NOW()
FROM issues i
JOIN workflow_statuses ws ON ws.id = i.status_id
WHERE i.id = :issue_id
ON CONFLICT (issue_id) DO UPDATE SET
    current_status_id = EXCLUDED.current_status_id,
    flow_stage        = EXCLUDED.flow_stage,
    assigned_to_id    = EXCLUDED.assigned_to_id,
    updated_on        = EXCLUDED.updated_on,
    closed_on         = EXCLUDED.closed_on,
    total_days        = EXCLUDED.total_days,
    days_in_stage     = EXCLUDED.days_in_stage,
    _etl_at           = EXCLUDED._etl_at;
```

---

## 인덱스 전략 (100명 동시 접속 기준)

| 테이블 | 주요 쿼리 패턴 | 인덱스 |
|---|---|---|
| `issues` | 프로젝트별 + 상태별 조회 | `(project_id, status_id)` 복합 |
| `issues` | 담당자별 조회 | `(assignee_id, project_id)` |
| `issue_journals` | 이슈별 이력 | `(issue_id, created_at DESC)` |
| `notifications` | 미읽음 알림 | `(user_id, is_read, created_at DESC)` |
| `time_entries` | 기간별 집계 | `(project_id, spent_on)` |

---

## Redis 사용 패턴

| 키 패턴 | 용도 | TTL |
|---|---|---|
| `session:{user_id}` | SSE 연결 관리 | 세션 유지 동안 |
| `notifications:{user_id}` | 미발송 알림 큐 | 24시간 |
| `project_members:{project_id}` | 멤버 캐시 | 5분 |
| `login_fail:{email}` | 로그인 실패 카운터 | 15분 |
