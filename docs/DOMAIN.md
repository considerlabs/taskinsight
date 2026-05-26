# TaskInsight — 도메인 모델 & 용어 사전

> 이 문서는 시스템의 모든 개념, 엔티티, 비즈니스 규칙을 정의합니다.
> 코드, API, UI 어디서든 동일한 용어를 사용해야 합니다.

---

## 1. 핵심 엔티티

### 1.1 User (사용자)

시스템에 로그인할 수 있는 모든 인원.

**속성:**
- `id`: UUID (PK)
- `email`: 회사 이메일 주소 (유니크, 로그인 ID로 사용)
- `password_hash`: bcrypt 해시
- `display_name`: 화면 표시 이름 (예: "홍길동")
- `is_system_admin`: 시스템 전체 관리자 여부
- `is_active`: 계정 활성화 여부 (비활성화 시 로그인 불가, 데이터는 보존)
- `last_login_at`: 마지막 로그인 시각
- `created_at`, `updated_at`

**비즈니스 규칙:**
- 이메일은 변경 불가 (시스템 식별자)
- 비활성화된 사용자의 이슈는 그대로 유지 (담당자 표시만 "비활성" 처리)
- 시스템 관리자는 프로젝트 멤버십 없이도 모든 프로젝트 접근 가능

---

### 1.2 Project (프로젝트)

이슈의 최상위 그룹 단위. 팀 또는 제품 단위로 생성.

**속성:**
- `id`: Integer (PK)
- `identifier`: URL-safe 슬러그 (예: "manna-platform"). 변경 불가.
- `name`: 표시 이름 (예: "만나 플랫폼")
- `description`: 설명 (Markdown)
- `is_active`: 활성 여부
- `default_assignee_id`: 기본 담당자 (없으면 NULL)
- `created_by_id`: 생성자
- `created_at`, `updated_at`

**비즈니스 규칙:**
- 프로젝트는 삭제하지 않고 비활성화만 가능 (데이터 보존)
- `identifier`는 생성 시 한 번만 설정, 이후 변경 불가
- 비활성 프로젝트는 새 이슈 생성 불가, 기존 이슈 조회는 가능

---

### 1.3 ProjectMember (프로젝트 멤버십)

사용자의 프로젝트 참여와 역할을 정의.

**속성:**
- `project_id`: FK → projects
- `user_id`: FK → users
- `role`: `manager` | `member` | `viewer`
- `added_by_id`: 초대한 사람
- `joined_at`

**역할 정의:**

| 역할 | 코드 | 권한 |
|---|---|---|
| 프로젝트 관리자 | `manager` | 프로젝트 설정 변경, 멤버 추가/제거, 이슈 전체 수정/삭제, 워크플로우 설정 |
| 팀원 | `member` | 이슈 생성/수정, 댓글, 시간기록, 파일 첨부. 자신이 만든 이슈만 삭제 |
| 뷰어 | `viewer` | 읽기 전용. 댓글 작성 불가 |

**비즈니스 규칙:**
- 한 프로젝트에 최소 1명의 `manager`는 항상 존재해야 함
- 시스템 관리자(`is_system_admin=true`)는 멤버십 없이도 모든 프로젝트에서 `manager` 권한
- `manager`는 자신을 프로젝트에서 제거 불가 (다른 관리자가 존재해야 제거 가능)

---

### 1.4 WorkflowStatus (이슈 상태)

프로젝트별로 정의되는 이슈의 단계.

**속성:**
- `id`: Integer (PK)
- `project_id`: FK → projects
- `name`: 상태명 (예: "검수 대기", "개발 중")
- `color`: 헥스 색상 코드 (예: "#F59E0B")
- `position`: 순서 (정렬 기준)
- `is_closed`: 이 상태가 "완료" 계열인지 여부 (처리량 계산에 사용)
- `flow_stage`: 분석 엔진 매핑 값 (`backlog` | `in_progress` | `review` | `done` | `blocked`)
- `is_default`: 새 이슈 생성 시 기본 상태 여부 (프로젝트당 1개만 true 가능)

**기본값 (모든 프로젝트에 자동 생성):**
```
position 1: "대기 중"    color="#6B7280"  flow_stage=backlog      is_default=true
position 2: "진행 중"    color="#2563EB"  flow_stage=in_progress
position 3: "검수 중"    color="#F59E0B"  flow_stage=review
position 4: "완료"       color="#059669"  flow_stage=done         is_closed=true
position 5: "보류됨"     color="#DC2626"  flow_stage=blocked
```

**비즈니스 규칙:**
- `is_closed=true` 상태로 전환 시 `issues.closed_at` 자동 기록
- `is_closed=false` 상태로 재전환 시 `issues.closed_at` NULL로 초기화
- 상태 삭제: 해당 상태를 사용하는 이슈가 없어야 삭제 가능

---

### 1.5 WorkflowTransition (상태 전환 규칙)

어떤 역할이 어떤 상태에서 어떤 상태로 전환할 수 있는지 정의.

**속성:**
- `id`: Integer (PK)
- `project_id`: FK → projects
- `from_status_id`: FK → workflow_statuses (NULL이면 "이슈 생성 시 초기 상태")
- `to_status_id`: FK → workflow_statuses
- `allowed_roles`: `manager` | `member` | `viewer` (복수 가능, JSONB 배열)

**기본값:**
```
모든 역할: 대기중 ↔ 진행중 ↔ 검수중
관리자만: 검수중 → 완료, 완료 → 진행중 (재오픈)
모든 역할: 어디서든 → 보류됨
```

---

### 1.6 Issue (이슈)

업무의 기본 단위. 태스크, 버그, 기능 요청 등 모든 업무 항목.

**속성:**
- `id`: Integer (PK, auto-increment)
- `project_id`: FK → projects
- `status_id`: FK → workflow_statuses (현재 상태)
- `title`: 제목 (필수, 최대 500자)
- `description`: 본문 (Markdown, 선택)
- `reporter_id`: FK → users (등록자, 변경 불가)
- `assignee_id`: FK → users (담당자, 없으면 NULL)
- `priority`: `low` | `normal` | `high` | `urgent` (기본값: `normal`)
- `tracker`: `task` | `bug` | `feature` | `improvement` (업무 유형)
- `milestone_id`: FK → milestones (없으면 NULL)
- `parent_issue_id`: FK → issues (서브이슈, 없으면 NULL. 최대 1단계 중첩)
- `start_date`: 시작일 (선택)
- `due_date`: 마감일 (선택)
- `estimated_hours`: 예상 시간 (선택)
- `done_ratio`: 진행률 0~100 (기본값: 0)
- `closed_at`: 완료 시각 (is_closed 상태 전환 시 자동 기록)
- `created_at`, `updated_at`

**우선순위 정의:**
| 코드 | 표시 | 색상 |
|---|---|---|
| `urgent` | 긴급 | `--color-critical` (#DC2626) |
| `high` | 높음 | `--color-warning` (#F59E0B) |
| `normal` | 보통 | `--color-normal` (#6B7280) |
| `low` | 낮음 | `--color-normal` (#6B7280) |

**업무 유형(tracker) 정의:**
| 코드 | 표시 | 아이콘 |
|---|---|---|
| `task` | 업무 | CheckSquare |
| `bug` | 버그 | Bug |
| `feature` | 기능 | Zap |
| `improvement` | 개선 | TrendingUp |

**비즈니스 규칙:**
- 이슈는 삭제 불가. 관리자만 아카이브(`status_id` → 완료 계열) 가능
- 서브이슈는 1단계만 허용 (이슈 → 서브이슈. 서브이슈의 서브이슈 금지)
- 부모이슈 완료 시 미완료 서브이슈가 있으면 경고 표시 (막지는 않음)
- `done_ratio`는 서브이슈의 평균으로 자동 계산 (서브이슈 있을 때)

---

### 1.7 IssueJournal (변경 이력)

이슈의 모든 변경 사항을 기록. 되돌리기 불가. 감사 로그 역할.

**속성:**
- `id`: Integer (PK)
- `issue_id`: FK → issues
- `user_id`: FK → users (변경한 사람)
- `created_at`: 변경 시각
- `changes`: JSONB — 변경 전/후 값
  ```json
  {
    "status_id":  {"from": 1, "to": 2},
    "assignee_id": {"from": null, "to": 5},
    "priority":   {"from": "normal", "to": "high"}
  }
  ```
- `note`: 댓글 (변경과 함께 남긴 메모, 선택)

**비즈니스 규칙:**
- 이슈 상태 전환 시 자동으로 journal 생성
- 이슈 필드 변경(담당자, 우선순위 등) 시 자동으로 journal 생성
- 댓글만 남기는 것도 journal로 기록 (changes는 빈 객체 `{}`)
- journal은 수정/삭제 불가 (관리자도)

---

### 1.8 TimeEntry (시간 기록)

이슈에 소요된 실제 작업 시간.

**속성:**
- `id`: Integer (PK)
- `issue_id`: FK → issues
- `user_id`: FK → users
- `hours`: 소요 시간 (소수점 1자리, 예: 2.5)
- `activity`: `development` | `review` | `design` | `meeting` | `testing` | `other`
- `spent_on`: 작업 날짜 (Date)
- `description`: 작업 내용 메모 (선택)
- `created_at`, `updated_at`

**비즈니스 규칙:**
- `hours`는 0 초과, 24 이하
- 팀원은 자신의 시간기록만 수정/삭제 가능
- 관리자는 팀 전체 시간기록 조회/수정 가능

---

### 1.9 Milestone (마일스톤)

스프린트 또는 릴리즈 버전 단위.

**속성:**
- `id`: Integer (PK)
- `project_id`: FK → projects
- `name`: 마일스톤명 (예: "v1.0", "2분기 릴리즈")
- `description`: 설명
- `status`: `open` | `closed`
- `start_date`: 시작일 (선택)
- `due_date`: 마감일 (선택)
- `created_by_id`: FK → users
- `created_at`, `updated_at`

**비즈니스 규칙:**
- 마일스톤 종료(`closed`) 시 미완료 이슈는 자동으로 다음 마일스톤으로 이동하지 않음 (수동 처리)
- 마일스톤 삭제 시 연결된 이슈의 `milestone_id`는 NULL로 초기화

---

### 1.10 Attachment (첨부파일)

이슈에 첨부된 파일.

**속성:**
- `id`: UUID (PK)
- `issue_id`: FK → issues
- `uploader_id`: FK → users
- `filename`: 원본 파일명
- `stored_path`: 서버 저장 경로 (UPLOAD_DIR 기준 상대 경로)
- `content_type`: MIME 타입
- `file_size`: 바이트 단위
- `created_at`

**비즈니스 규칙:**
- 최대 파일 크기: 50MB
- 허용 MIME 타입: 이미지, PDF, 문서, 압축파일 (실행파일 .exe, .sh 등 금지)
- 파일 삭제: 이슈 삭제 시 연동 삭제 (이슈는 삭제 안 되므로 실질적으로 업로더 또는 관리자만 삭제)

---

### 1.11 Notification (알림)

시스템 내 이벤트 알림.

**속성:**
- `id`: Integer (PK)
- `user_id`: FK → users (수신자)
- `type`: 알림 유형 (아래 목록)
- `issue_id`: FK → issues (관련 이슈, 있을 경우)
- `actor_id`: FK → users (행위자)
- `message`: 알림 메시지
- `is_read`: 읽음 여부
- `created_at`

**알림 유형:**
| type | 트리거 |
|---|---|
| `issue_assigned` | 이슈 담당자로 지정됨 |
| `issue_commented` | 내 이슈에 댓글이 달림 |
| `issue_status_changed` | 내 이슈 상태가 변경됨 |
| `issue_mentioned` | 댓글에서 @mention됨 |
| `milestone_due_soon` | 마일스톤 마감 3일 전 |

**비즈니스 규칙:**
- 알림은 SSE(Server-Sent Events)로 실시간 전송
- 30일 이상 된 읽은 알림은 자동 삭제 (배치)
- 본인이 수행한 행위는 알림 생성 안 함

---

## 2. ETL 통합 (분석 연동)

### 2.1 신규 이슈 → 분석 파이프라인

```
issues 테이블 INSERT/UPDATE
    → FastAPI background_tasks.add_task(trigger_etl_for_issue, issue_id)
    → populate_issue_snapshot() 부분 갱신
    → populate_throughput_daily() 갱신

issue_journals 테이블 INSERT (상태 전환)
    → populate_state_transitions() 해당 이슈만 갱신
    → fct_issue_explanation.is_stale = TRUE (LLM 캐시 무효화)
```

### 2.2 데이터 소스 통합

`fct_issue_snapshot`은 두 가지 소스를 통합:

```sql
-- 소스 1: 신규 자체 이슈 (issues 테이블)
-- 소스 2: Redmine 마이그레이션 데이터 (raw_redmine_issues에서 마이그레이션된 것도 issues 테이블로)
-- 소스 3: 연동된 외부 Redmine (raw_redmine_issues, 커넥터 활성 시)

-- source_type 컬럼으로 구분
source_type = 'internal'  -- 자체 시스템에서 생성된 이슈
source_type = 'redmine'   -- Redmine 커넥터에서 동기화된 이슈
```

### 2.3 flow_stage 자동 매핑

이슈의 `status_id` → `workflow_statuses.flow_stage` → `fct_issue_snapshot.flow_stage`

커스텀 워크플로우 설정 시 관리자가 각 상태의 `flow_stage`를 지정.

---

## 3. 비즈니스 규칙 요약

### 권한 매트릭스

| 작업 | 시스템관리자 | 프로젝트관리자 | 팀원 | 뷰어 |
|---|---|---|---|---|
| 프로젝트 생성 | ✅ | ❌ | ❌ | ❌ |
| 프로젝트 설정 변경 | ✅ | ✅ | ❌ | ❌ |
| 멤버 추가/제거 | ✅ | ✅ | ❌ | ❌ |
| 이슈 생성 | ✅ | ✅ | ✅ | ❌ |
| 이슈 수정 (본인 것) | ✅ | ✅ | ✅ | ❌ |
| 이슈 수정 (타인 것) | ✅ | ✅ | ❌ | ❌ |
| 이슈 상태 변경 | ✅ | ✅ | ✅ (전환규칙 내) | ❌ |
| 댓글 작성 | ✅ | ✅ | ✅ | ❌ |
| 시간기록 | ✅ | ✅ | ✅ | ❌ |
| 파일 첨부 | ✅ | ✅ | ✅ | ❌ |
| 워크플로우 설정 | ✅ | ✅ | ❌ | ❌ |
| 사용자 계정 관리 | ✅ | ❌ | ❌ | ❌ |
| LLM 설명 조회 | ✅ | ✅ | ✅ | ✅ |
| 주간보고 생성 | ✅ | ✅ | ❌ | ❌ |
| Dashboard 조회 | ✅ | ✅ | ✅ | ✅ |

### 데이터 접근 규칙

- **프로젝트 이슈 접근**: 해당 프로젝트의 멤버(또는 시스템관리자)만 가능
- **비공개 이슈**: v2 (현재 모든 이슈는 프로젝트 멤버 전체 공개)
- **시간기록 조회**: 본인 것은 항상, 타인 것은 관리자만

---

## 4. 한국어 용어 사전 (전체)

| 영문 코드 | 화면 표시 | 금지 표현 |
|---|---|---|
| `issue` | 이슈 | 티켓, 항목 |
| `project` | 프로젝트 | - |
| `milestone` | 마일스톤 | 버전, 스프린트 |
| `status` | 상태 | - |
| `workflow` | 워크플로우 | - |
| `assignee` | 담당자 | 담당, 할당자 |
| `reporter` | 등록자 | 작성자, 요청자 |
| `priority` | 우선순위 | - |
| `tracker` | 유형 | 종류, 타입 |
| `journal` | 변경이력 | 로그, 히스토리 |
| `time_entry` | 시간기록 | 작업시간, 공수 |
| `attachment` | 첨부파일 | 파일 |
| `notification` | 알림 | 노티 |
| `member` | 팀원 | 구성원, 멤버 |
| `manager` | 프로젝트 관리자 | PM, 리더 |
| `system_admin` | 시스템 관리자 | 관리자 (단독 사용 시) |
| `flow_stage` | 흐름단계 | - (내부 용어) |
| `risk_score` | 지연위험 | 위험도, 리스크 |
| `bottleneck` | 정체 구간 | 병목 |
| `throughput` | 주간 완료량 | 처리량 |
| `lead_time` | 전체 소요일 | 리드타임 |
| `cycle_time` | 처리 기간 | 사이클타임 |

**표현 규칙:**
- "직원/사원" → "구성원"
- "약점/문제점/부진" → "함께 살펴볼 영역"
- 보고서체: 단문 (~함, ~됨). 권장은 권유형 (~을 권장합니다)
- LLM 생성 텍스트: 개인 평가 절대 금지, 팀/상황 설명만

---

## 5. 상태 전환 흐름 (기본)

```
[대기 중] ←→ [진행 중] ←→ [검수 중]
                                ↓ (관리자만)
                             [완료]
                    ↑ (재오픈, 관리자만)

[어디서든] → [보류됨] → [진행 중]
```

Gantt 차트 기준일: `start_date` (없으면 `created_at`), `due_date`
