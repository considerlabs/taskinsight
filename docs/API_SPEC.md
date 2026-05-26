# TaskInsight — API 엔드포인트 명세

> 모든 엔드포인트는 `/v1` 프리픽스. Content-Type: `application/json`.
> 인증이 필요한 엔드포인트: `Authorization: Bearer {access_token}` 헤더 필수.
> 에러 응답 형식: `{"detail": "에러 메시지"}`

---

## 공통 응답 패턴

### 페이지네이션
```json
{
  "items": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### 타임스탬프
모든 타임스탬프는 ISO 8601 UTC. 예: `"2026-05-26T10:30:00Z"`

---

## 1. 인증 (`/v1/auth`)

### POST `/v1/auth/login`
**인증 불필요**

**Request:**
```json
{
  "email": "user@company.com",
  "password": "plaintext_password"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@company.com",
    "display_name": "홍길동",
    "is_system_admin": false
  }
}
```
_+ `Set-Cookie: refresh_token={token}; HttpOnly; Path=/v1/auth/refresh; Max-Age=2592000`_

**Response 401:** 이메일 또는 비밀번호 오류  
**Response 423:** 계정 잠김 (`{"detail": "계정이 잠겼습니다. 15분 후 다시 시도하세요.", "locked_until": "2026-05-26T10:45:00Z"}`)

---

### POST `/v1/auth/refresh`
**인증 불필요** (HttpOnly 쿠키 사용)

**Response 200:**
```json
{
  "access_token": "eyJhbG...",
  "expires_in": 900
}
```

---

### POST `/v1/auth/logout`
**인증 필요**

현재 Refresh Token 무효화.

**Response 200:** `{"ok": true}`

---

### GET `/v1/auth/me`
**인증 필요**

**Response 200:**
```json
{
  "id": "uuid",
  "email": "user@company.com",
  "display_name": "홍길동",
  "is_system_admin": false,
  "is_active": true,
  "last_login_at": "2026-05-26T09:00:00Z"
}
```

---

### PUT `/v1/auth/me/password`
**인증 필요**

**Request:**
```json
{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

**Response 200:** `{"ok": true}`  
**Response 400:** 현재 비밀번호 오류

---

## 2. 사용자 관리 (`/v1/users`) — 시스템 관리자 전용

### GET `/v1/users`
**권한: 시스템 관리자**

**Query Parameters:** `?limit=20&offset=0&search=홍길동&is_active=true`

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "email": "user@company.com",
      "display_name": "홍길동",
      "is_system_admin": false,
      "is_active": true,
      "last_login_at": "2026-05-26T09:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

---

### POST `/v1/users`
**권한: 시스템 관리자**

**Request:**
```json
{
  "email": "newuser@company.com",
  "display_name": "새 사용자",
  "password": "initial_password",
  "is_system_admin": false
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "email": "newuser@company.com",
  "display_name": "새 사용자",
  "is_system_admin": false,
  "is_active": true,
  "created_at": "2026-05-26T10:00:00Z"
}
```

---

### PUT `/v1/users/{user_id}`
**권한: 시스템 관리자**

**Request:**
```json
{
  "display_name": "수정된 이름",
  "is_active": false,
  "is_system_admin": false
}
```

**Response 200:** 수정된 사용자 객체

---

### POST `/v1/users/{user_id}/reset-password`
**권한: 시스템 관리자**

**Request:**
```json
{
  "new_password": "reset_password"
}
```

**Response 200:** `{"ok": true}`

---

## 3. 프로젝트 (`/v1/projects`)

### GET `/v1/projects`
**인증 필요**

시스템 관리자: 전체 프로젝트. 일반 사용자: 참여 중인 프로젝트만.

**Query Parameters:** `?limit=20&offset=0&is_active=true`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "identifier": "manna-platform",
      "name": "만나 플랫폼",
      "description": "...",
      "is_active": true,
      "my_role": "manager",
      "member_count": 15,
      "open_issue_count": 321,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 4
}
```

---

### POST `/v1/projects`
**권한: 시스템 관리자**

**Request:**
```json
{
  "identifier": "new-project",
  "name": "새 프로젝트",
  "description": "프로젝트 설명"
}
```

**Response 201:** 생성된 프로젝트 객체 (기본 워크플로우 자동 생성됨)

---

### GET `/v1/projects/{project_id}`
**권한: 프로젝트 멤버 또는 시스템 관리자**

**Response 200:**
```json
{
  "id": 1,
  "identifier": "manna-platform",
  "name": "만나 플랫폼",
  "description": "...",
  "is_active": true,
  "my_role": "manager",
  "default_assignee": {"id": "uuid", "display_name": "홍길동"},
  "created_by": {"id": "uuid", "display_name": "홍길동"},
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-05-01T00:00:00Z"
}
```

---

### PUT `/v1/projects/{project_id}`
**권한: 프로젝트 관리자 또는 시스템 관리자**

**Request:**
```json
{
  "name": "수정된 프로젝트명",
  "description": "수정된 설명",
  "is_active": true,
  "default_assignee_id": "uuid"
}
```

---

### GET `/v1/projects/{project_id}/members`
**권한: 프로젝트 멤버 또는 시스템 관리자**

**Response 200:**
```json
{
  "items": [
    {
      "user": {"id": "uuid", "display_name": "홍길동", "email": "..."},
      "role": "manager",
      "joined_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/v1/projects/{project_id}/members`
**권한: 프로젝트 관리자 또는 시스템 관리자**

**Request:**
```json
{
  "user_id": "uuid",
  "role": "member"
}
```

**Response 201:** 생성된 멤버십 객체

---

### PUT `/v1/projects/{project_id}/members/{user_id}`
**권한: 프로젝트 관리자 또는 시스템 관리자**

**Request:** `{"role": "manager"}`

---

### DELETE `/v1/projects/{project_id}/members/{user_id}`
**권한: 프로젝트 관리자 또는 시스템 관리자**

**Response 204**  
**Response 400:** 마지막 관리자 제거 시도 시

---

## 4. 워크플로우 (`/v1/projects/{project_id}/workflow`)

### GET `/v1/projects/{project_id}/workflow/statuses`
**권한: 프로젝트 멤버**

**Response 200:**
```json
{
  "statuses": [
    {
      "id": 1,
      "name": "대기 중",
      "color": "#6B7280",
      "position": 1,
      "is_closed": false,
      "is_default": true,
      "flow_stage": "backlog"
    }
  ]
}
```

---

### PUT `/v1/projects/{project_id}/workflow/statuses`
**권한: 프로젝트 관리자**

상태 목록 전체 교체 (순서 변경 포함).

**Request:**
```json
{
  "statuses": [
    {"id": 1, "name": "대기 중", "color": "#6B7280", "position": 1,
     "is_closed": false, "is_default": true, "flow_stage": "backlog"},
    {"id": null, "name": "QA 중", "color": "#8B5CF6", "position": 3,
     "is_closed": false, "is_default": false, "flow_stage": "review"}
  ]
}
```

---

### GET `/v1/projects/{project_id}/workflow/transitions`
**권한: 프로젝트 관리자**

**Response 200:**
```json
{
  "transitions": [
    {
      "id": 1,
      "from_status": {"id": 1, "name": "대기 중"},
      "to_status": {"id": 2, "name": "진행 중"},
      "allowed_roles": ["manager", "member"]
    }
  ]
}
```

---

### PUT `/v1/projects/{project_id}/workflow/transitions`
**권한: 프로젝트 관리자**

전환 규칙 전체 교체.

---

## 5. 이슈 (`/v1/projects/{project_id}/issues`)

### GET `/v1/projects/{project_id}/issues`
**권한: 프로젝트 멤버**

**Query Parameters:**
```
status_id=1           # 상태 필터 (복수: status_id=1&status_id=2)
assignee_id=uuid      # 담당자 필터
milestone_id=1        # 마일스톤 필터
priority=high         # 우선순위 필터
tracker=bug           # 유형 필터
q=검색어              # 제목 검색
sort=updated_at       # 정렬 기준 (updated_at|created_at|due_date|priority)
order=desc            # 정렬 방향
limit=20
offset=0
```

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "결제 모듈 오류",
      "priority": "high",
      "tracker": "bug",
      "status": {"id": 2, "name": "진행 중", "color": "#2563EB", "flow_stage": "in_progress"},
      "assignee": {"id": "uuid", "display_name": "홍길동"},
      "reporter": {"id": "uuid", "display_name": "김철수"},
      "milestone": {"id": 1, "name": "v1.0"},
      "due_date": "2026-06-01",
      "done_ratio": 30,
      "sub_issue_count": 3,
      "comment_count": 5,
      "created_at": "2026-05-01T00:00:00Z",
      "updated_at": "2026-05-26T10:00:00Z"
    }
  ],
  "total": 321,
  "limit": 20,
  "offset": 0
}
```

---

### POST `/v1/projects/{project_id}/issues`
**권한: 프로젝트 관리자, 팀원**

**Request:**
```json
{
  "title": "결제 모듈 오류",
  "description": "결제 시 500 에러 발생",
  "priority": "high",
  "tracker": "bug",
  "assignee_id": "uuid",
  "milestone_id": 1,
  "parent_issue_id": null,
  "start_date": "2026-05-26",
  "due_date": "2026-06-01",
  "estimated_hours": 4.0
}
```

**Response 201:** 생성된 이슈 전체 객체

---

### GET `/v1/issues/{issue_id}`
**권한: 해당 프로젝트 멤버**

**Response 200:**
```json
{
  "id": 1,
  "project": {"id": 1, "name": "만나 플랫폼", "identifier": "manna-platform"},
  "title": "결제 모듈 오류",
  "description": "결제 시 500 에러 발생",
  "priority": "high",
  "tracker": "bug",
  "status": {"id": 2, "name": "진행 중", "color": "#2563EB", "flow_stage": "in_progress"},
  "assignee": {"id": "uuid", "display_name": "홍길동"},
  "reporter": {"id": "uuid", "display_name": "김철수"},
  "milestone": {"id": 1, "name": "v1.0"},
  "parent_issue": null,
  "sub_issues": [
    {"id": 10, "title": "서브이슈 제목", "status": {...}, "done_ratio": 0}
  ],
  "start_date": "2026-05-26",
  "due_date": "2026-06-01",
  "estimated_hours": 4.0,
  "done_ratio": 30,
  "closed_at": null,
  "attachments": [
    {"id": "uuid", "filename": "error_log.txt", "file_size": 1024, "created_at": "..."}
  ],
  "total_spent_hours": 2.5,
  "allowed_transitions": [
    {"id": 3, "name": "검수 중", "color": "#F59E0B"}
  ],
  "has_explanation": true,
  "created_at": "2026-05-01T00:00:00Z",
  "updated_at": "2026-05-26T10:00:00Z"
}
```

---

### PUT `/v1/issues/{issue_id}`
**권한: 관리자 또는 본인이 등록한 이슈**

**Request (부분 업데이트, 변경된 필드만):**
```json
{
  "title": "수정된 제목",
  "assignee_id": "new-uuid",
  "priority": "urgent",
  "due_date": "2026-06-15",
  "done_ratio": 50,
  "note": "담당자 변경합니다"
}
```

모든 변경사항은 `issue_journals`에 자동 기록됨.

**Response 200:** 수정된 이슈 전체 객체

---

### POST `/v1/issues/{issue_id}/transition`
**권한: 전환 규칙의 `allowed_roles`에 포함된 역할**

**Request:**
```json
{
  "to_status_id": 3,
  "note": "검수 요청합니다"
}
```

**Response 200:** 수정된 이슈 객체  
**Response 400:** 허용되지 않은 전환 (`{"detail": "해당 역할로는 이 상태 전환이 허용되지 않습니다."}`)

---

## 6. 댓글/변경이력 (`/v1/issues/{issue_id}/journals`)

### GET `/v1/issues/{issue_id}/journals`
**권한: 프로젝트 멤버**

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "user": {"id": "uuid", "display_name": "홍길동"},
      "changes": {
        "status_id": {"from": 1, "to": 2,
                      "from_name": "대기 중", "to_name": "진행 중"},
        "assignee_id": {"from": null, "to": "uuid",
                        "from_name": null, "to_name": "홍길동"}
      },
      "note": "개발 시작합니다",
      "created_at": "2026-05-26T10:00:00Z"
    }
  ]
}
```

---

### POST `/v1/issues/{issue_id}/journals`
**권한: 프로젝트 관리자, 팀원**

댓글만 남기기 (변경 없이).

**Request:**
```json
{
  "note": "확인했습니다. 내일 처리 예정입니다."
}
```

**Response 201:** 생성된 journal 객체

---

## 7. 시간 기록 (`/v1/issues/{issue_id}/time-entries`)

### GET `/v1/issues/{issue_id}/time-entries`
**권한: 프로젝트 멤버 (본인 것 + 관리자는 전체)**

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "user": {"id": "uuid", "display_name": "홍길동"},
      "hours": 2.5,
      "activity": "development",
      "spent_on": "2026-05-26",
      "description": "로그인 API 구현",
      "created_at": "2026-05-26T18:00:00Z"
    }
  ],
  "total_hours": 7.5
}
```

---

### POST `/v1/issues/{issue_id}/time-entries`
**권한: 프로젝트 관리자, 팀원**

**Request:**
```json
{
  "hours": 2.5,
  "activity": "development",
  "spent_on": "2026-05-26",
  "description": "로그인 API 구현"
}
```

---

### PUT `/v1/time-entries/{entry_id}`
**권한: 본인 또는 프로젝트 관리자**

---

### DELETE `/v1/time-entries/{entry_id}`
**권한: 본인 또는 프로젝트 관리자**

**Response 204**

---

## 8. 파일 첨부 (`/v1/issues/{issue_id}/attachments`)

### POST `/v1/issues/{issue_id}/attachments`
**권한: 프로젝트 관리자, 팀원**

**Request:** `multipart/form-data`, 필드명 `file`

**Response 201:**
```json
{
  "id": "uuid",
  "filename": "screenshot.png",
  "content_type": "image/png",
  "file_size": 204800,
  "created_at": "2026-05-26T10:00:00Z"
}
```

---

### GET `/v1/attachments/{attachment_id}`
**권한: 프로젝트 멤버**

파일 다운로드. `Content-Disposition: attachment` 헤더 포함.

---

### DELETE `/v1/attachments/{attachment_id}`
**권한: 업로더 또는 프로젝트 관리자**

**Response 204**

---

## 9. 마일스톤 (`/v1/projects/{project_id}/milestones`)

### GET `/v1/projects/{project_id}/milestones`
**Query:** `?status=open`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "v1.0",
      "description": "첫 번째 릴리즈",
      "status": "open",
      "start_date": "2026-05-01",
      "due_date": "2026-06-30",
      "issue_stats": {
        "total": 50,
        "done": 30,
        "in_progress": 15,
        "open": 5
      },
      "completion_rate": 60
    }
  ]
}
```

---

### POST `/v1/projects/{project_id}/milestones`
**권한: 프로젝트 관리자**

**Request:**
```json
{
  "name": "v1.1",
  "description": "",
  "start_date": "2026-07-01",
  "due_date": "2026-08-31"
}
```

---

### PUT `/v1/projects/{project_id}/milestones/{milestone_id}`
**권한: 프로젝트 관리자**

---

## 10. 알림 (`/v1/notifications`)

### GET `/v1/notifications`
**인증 필요**

**Query:** `?is_read=false&limit=20&offset=0`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "type": "issue_assigned",
      "message": "홍길동님이 '결제 모듈 오류' 이슈를 배정했습니다.",
      "issue": {"id": 1, "title": "결제 모듈 오류", "project_id": 1},
      "actor": {"id": "uuid", "display_name": "홍길동"},
      "is_read": false,
      "created_at": "2026-05-26T10:00:00Z"
    }
  ],
  "unread_count": 3,
  "total": 10
}
```

---

### POST `/v1/notifications/read-all`
**인증 필요**

모든 알림 읽음 처리.

**Response 200:** `{"ok": true, "updated": 5}`

---

### PUT `/v1/notifications/{notification_id}/read`
**인증 필요**

**Response 200:** `{"ok": true}`

---

### GET `/v1/notifications/stream`
**인증 필요**

SSE 스트림. `Accept: text/event-stream`

```
data: {"type":"ping"}

data: {"type":"issue_assigned","notification_id":1,"issue_id":123,"message":"..."}
```

---

## 11. 기존 분석 API (유지, 변경 없음)

| 경로 | 설명 |
|---|---|
| `GET /v1/flow/stages` | 단계별 건수 + 평균 체류일 |
| `GET /v1/flow/issues` | 이슈 목록 (분석용 필터) |
| `GET /v1/flow/issue/{id}/explanation` | LLM 설명 |
| `GET /v1/dashboard/summary` | Speed/Effectiveness/Quality |
| `POST /v1/reports/weekly/generate` | 주간보고 생성 |
| `GET /v1/reports/weekly/latest` | 최근 보고서 |
| `GET /v1/connectors/instances` | 연동 목록 |
| `POST /v1/connectors/test` | 연결 테스트 |
| `PUT /v1/connectors/{id}` | 연동 설정 수정 |
| `POST /v1/connectors/{id}/sync` | 즉시 동기화 |

---

## 12. HTTP 상태 코드 가이드

| 코드 | 사용 상황 |
|---|---|
| 200 | 성공 (GET, PUT) |
| 201 | 생성 성공 (POST) |
| 204 | 삭제 성공 (DELETE) |
| 400 | 잘못된 요청 (비즈니스 규칙 위반) |
| 401 | 인증 실패 (토큰 없음 또는 만료) |
| 403 | 권한 없음 (인증은 됐지만 권한 부족) |
| 404 | 리소스 없음 |
| 409 | 충돌 (이미 존재하는 email 등) |
| 422 | 요청 데이터 형식 오류 (FastAPI 기본) |
| 423 | 잠긴 계정 |
| 500 | 서버 오류 |
