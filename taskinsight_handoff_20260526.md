# TaskInsight — 인수인계 문서
**작성일:** 2026-05-26  
**작업 디렉터리:** `C:\Users\Manna\taskinsight_temp`  
**다음 작업:** Phase 1 구현 (인증 + 이슈 CRUD 백엔드/프론트엔드)

---

## 1. 프로젝트 개요

**TaskInsight**는 두 가지를 하나로 통합한 사내 업무 플랫폼입니다.

1. **업무관리 (Issue Management)** — Redmine을 완전 대체하는 이슈 트래커
2. **분석 대시보드 (SEI Dashboard)** — 업무 데이터 실시간 분석 (기존 기능)

**현재 상태:**
- 기존: 분석 대시보드만 동작 (raw_redmine_* 데이터 기반, 읽기 전용)
- Redmine 데이터: 이슈 16,111건, 저널 97,000건이 `raw_redmine_*` 테이블에 수집됨
- 이번 세션에서 완료: **설계 문서 전체 완성**. 이제 구현 시작 가능한 상태.

---

## 2. 완성된 문서 목록

모든 문서는 `C:\Users\Manna\taskinsight_temp\` 하위에 있음.

### 핵심 가이드 (먼저 읽을 것)
| 파일 | 내용 |
|---|---|
| `CLAUDE.md` | **바이브 코딩 가이드. 모든 구현 결정사항. 코드 패턴 예제 포함.** |
| `docs/CONTEXT.md` | 아키텍처, 코딩 규칙 단일 진실 공급원 |
| `docs/SCHEMA.md` | 완전한 DB 스키마 (신규 테이블 0004~0007) |
| `docs/API_SPEC.md` | 모든 API 요청/응답 명세 (816줄) |
| `docs/UI_SPEC.md` | 화면별 명세 (381줄) |
| `docs/SECURITY_SPEC.md` | 인증/인가 상세 규칙 |
| `docs/DOMAIN.md` | 도메인 모델 |

### 업무 규칙 & 테스트
| 파일 | 내용 |
|---|---|
| `docs/BUSINESS_RULES.md` | 이슈 규칙, 상태 전환, 삭제 정책, 알림 규칙 전체 |
| `docs/TEST_SCENARIOS.md` | Phase 1~4 시나리오 + 경계값 케이스 E-1~E-10 |
| `docs/NON_FUNCTIONAL_REQUIREMENTS.md` | 성능 목표, 가용성, 보안 요구사항 |
| `docs/RELEASE_CHECKLIST.md` | Phase별 운영 투입 전 체크리스트 |

### 운영/배포
| 파일 | 내용 |
|---|---|
| `docs/INFRA_SPEC.md` | 서버 사양, 설치 절차, 운영 명령, 장애 대응 |
| `docs/INTEGRATION_SPEC.md` | Teams Webhook, SMTP, Ollama 연동 명세 |
| `docs/MONITORING.md` | 로그 정책, 헬스체크, 감사 로그 |
| `docs/MIGRATION_PLAN.md` | Redmine D-day 전환 절차 + 롤백 |

### 인프라 파일
| 파일 | 내용 |
|---|---|
| `docker-compose.yml` | nginx + frontend + backend + postgres(TimescaleDB) + redis |
| `nginx.conf` | 리버스 프록시, 25MB 업로드 제한, LLM 타임아웃 180s |
| `.env.example` | 모든 환경변수 목록 |
| `backend/Dockerfile` | python:3.11-slim |
| `frontend/Dockerfile` | node:20-alpine 멀티스테이지 |

### 스크립트
| 파일 | 내용 |
|---|---|
| `backend/app/scripts/seed.py` | 이슈 상태 8개, 우선순위 4개, 관리자 계정 생성 |
| `backend/app/scripts/migrate_from_redmine.py` | Redmine D-day 마이그레이션 |
| `backend/app/scripts/create_test_data.py` | 테스트 계정 4개 + 이슈 25개 + 시간기록 등 |

### 스키마 파일
| 파일 | 내용 |
|---|---|
| `backend/app/schemas/common.py` | ErrorResponse, PaginatedResponse[T] |
| `backend/app/schemas/auth.py` | LoginRequest, TokenResponse, UserOut 등 |
| `backend/app/schemas/issues.py` | IssueCreate, IssueUpdate, IssueOut, JournalOut 등 |

### 샘플 데이터
| 파일 | 내용 |
|---|---|
| `samples/users.csv` | 22명 (4역할, 비활성, 엣지케이스 포함) |
| `samples/projects.csv` | 5개 프로젝트 |
| `samples/issues.csv` | 45건 (전체 상태/우선순위, 기한 초과, 미담당 포함) |
| `samples/time_entries.csv` | 35건 시간기록 |

---

## 3. 핵심 결정사항 요약 (grill-me 세션 확정)

### 역할 체계 (전역)
```
system_admin > project_manager > member > viewer
```
- viewer: 읽기 전용
- member: 이슈 생성/수정/댓글/시간기록
- project_manager: 이슈 삭제, 프로젝트 설정 (본인 프로젝트)
- system_admin: 전체

### 충돌 해소 (docs/CONTEXT.md vs CLAUDE.md)
`CLAUDE.md` Section 0에 명시:
- **역할 체계**: docs/는 프로젝트 단위 역할 → **전역 4단계로 확정**
- **테이블 접두사**: `ti_` 접두사 사용 (seed.py, migrate_from_redmine.py 기준)
- **Gantt 차트**: v2로 연기
- **각 Phase = 즉시 운영 가능 수준** (MVP 없음)

### 4단계 개발 계획
| Phase | 범위 | 목표 |
|---|---|---|
| 1 | 인증 + 이슈 CRUD | 기본 업무관리 운영 가능 |
| 2 | 코멘트 + 파일 첨부 + 알림 | 협업 기능 |
| 3 | 타임 트래킹 + 커스텀 필드 | Redmine 완전 대체 |
| 4 | 분석 통합 | TaskInsight 기반 SEI 분석 |

---

## 4. 기술 스택 & 필수 규칙

### 백엔드
```
FastAPI 0.115+  +  SQLAlchemy 2.0  +  psycopg3  (psycopg2 절대 금지)
Python 3.11  +  Pydantic v2
```

**필수 패턴:**
- 모든 백엔드 파일 최상단: `from __future__ import annotations`
- Pydantic v2: `model_config = {"from_attributes": True}`
- JSONB 업데이트: `Jsonb()` 래핑 필수
- LAG() OVER in UPDATE 불가 → CTE 사용
- 비밀번호: bcrypt rounds=12
- Ollama 호출: `"think": False` 필수 (없으면 content 비어있음)

### 프론트엔드
```
Next.js 16 App Router  +  Tailwind CSS v4  +  SWR (React Query 금지)
TypeScript
```

**필수 패턴:**
- Access Token: localStorage 저장
- Refresh Token: HttpOnly 쿠키 (30일)
- 401 응답 → 자동 로그아웃 + /login redirect
- SWR로 데이터 페칭

### DB 테이블 이름 (ti_ 접두사)
```
ti_users, ti_projects, ti_project_members
ti_issues, ti_issue_statuses, ti_issue_priorities
ti_journals, ti_journal_details
ti_time_entries, ti_issue_attachments
ti_notifications, ti_custom_field_values
```

---

## 5. 다음 세션에서 구현할 것 (Phase 1)

### 5.1 백엔드 구현 순서

**Step 1: Alembic 마이그레이션 (아직 없음)**
```
backend/alembic/versions/0004_auth.py       ← ti_users, ti_sessions
backend/alembic/versions/0005_task_core.py  ← ti_projects ~ ti_issues
backend/alembic/versions/0006_task_collab.py ← ti_journals, ti_attachments
backend/alembic/versions/0007_task_advanced.py ← ti_time_entries, ti_notifications
```
→ `docs/SCHEMA.md` 기준으로 작성. 기존 0001~0003은 건드리지 말 것.

**Step 2: ORM 모델**
```
backend/app/models/auth.py   ← TiUser, TiRefreshToken
backend/app/models/task.py   ← TiProject, TiProjectMember, TiIssue, TiIssueStatus,
                                TiIssuePriority, TiJournal, TiJournalDetail 등
```
→ `CLAUDE.md` Section 4.2 패턴 참고

**Step 3: 의존성 & 설정**
```
backend/app/deps.py    ← get_current_user, require_role, require_project_access
backend/app/config.py  ← Settings (기존 파일에 신규 env vars 추가)
```
→ `CLAUDE.md` Section 4.4 패턴 코드 그대로 사용 가능

**Step 4: 라우터**
```
backend/app/api/routers/auth.py     ← POST /v1/auth/login, POST /v1/auth/refresh, POST /v1/auth/logout
backend/app/api/routers/users.py    ← GET/POST/PATCH/DELETE /v1/users
backend/app/api/routers/projects.py ← CRUD + 멤버 관리
backend/app/api/routers/issues.py   ← CRUD + 필터/정렬
```
→ `docs/API_SPEC.md` 명세 준수

**Step 5: 알림 & 배포**
```
backend/app/notifications/teams.py
backend/app/notifications/email.py
backend/app/notifications/dispatcher.py
```

**Step 6: backend/app/api/main.py 업데이트**
→ 신규 라우터 include_router 추가 (기존 라우터 건드리지 말 것)

### 5.2 프론트엔드 구현 순서

```
frontend/app/(auth)/login/page.tsx         ← 로그인 화면
frontend/app/(app)/layout.tsx             ← 인증 레이아웃 + 사이드바
frontend/app/(app)/page.tsx               ← 홈: 내 이슈 요약
frontend/app/(app)/issues/page.tsx        ← 이슈 목록 (리스트+칸반 탭)
frontend/app/(app)/issues/new/page.tsx    ← 이슈 생성
frontend/app/(app)/issues/[id]/page.tsx   ← 이슈 상세
frontend/app/(app)/projects/page.tsx      ← 프로젝트 목록
frontend/lib/auth.ts                      ← 토큰 관리
frontend/lib/swr-hooks.ts                 ← SWR 커스텀 훅
```
→ `docs/UI_SPEC.md` 화면별 명세 참고  
→ `CLAUDE.md` Section 7 프론트엔드 패턴 참고

---

## 6. 구현 금지 사항

- `psycopg2` 사용 금지 (psycopg3만 사용)
- 기존 `app/api/routers/flow.py`, `dashboard.py`, `reports.py`, `connectors.py` 수정 금지
- 기존 `etl/`, `analytics/`, `narrator/`, `collector/` 수정 금지
- viewer 역할에 쓰기 권한 부여 금지
- JWT 토큰 값 로그 기록 금지
- 비밀번호(평문/해시 모두) 로그 기록 금지
- `.exe .bat .sh .ps1 .vbs .com .scr` 파일 업로드 허용 금지
- S3 사용 금지 (사내 서버 Docker volume만)
- React Query 사용 금지 (SWR만)

---

## 7. 테스트 실행 방법

```bash
# 1. 컨테이너 빌드 & 기동
docker-compose up -d

# 2. DB 마이그레이션
docker-compose exec backend alembic upgrade head

# 3. 시드 데이터
docker-compose exec backend python -m app.scripts.seed

# 4. 테스트 데이터 (개발환경)
docker-compose exec backend python -m app.scripts.create_test_data

# 테스트 계정
# admin@test.com   / TestAdmin123!   (system_admin)
# manager@test.com / TestManager123! (project_manager)
# member@test.com  / TestMember123!  (member)
# viewer@test.com  / TestViewer123!  (viewer)

# 5. 헬스체크
curl http://localhost/health
```

테스트 시나리오는 `docs/TEST_SCENARIOS.md` 참고. Phase 1 시나리오 1~4 + E-1~E-10 전부 통과해야 운영 투입.

---

## 8. 문서 읽기 순서 (구현 전 필수)

```
1. CLAUDE.md                  ← 최우선. 모든 결정사항과 코드 패턴
2. docs/SCHEMA.md             ← 테이블 구조
3. docs/API_SPEC.md           ← 엔드포인트 명세
4. docs/UI_SPEC.md            ← 화면 명세 (프론트엔드 작업 시)
5. docs/SECURITY_SPEC.md      ← 인증 상세
6. docs/BUSINESS_RULES.md     ← 이슈 생성/수정/삭제 규칙
```

`CLAUDE.md` Section 0의 충돌 해소 내용을 먼저 확인할 것.

---

## 9. 현재 존재하지 않는 파일 (구현해야 할 것)

| 파일/디렉터리 | 비고 |
|---|---|
| `backend/alembic/versions/0004~0007_*.py` | 마이그레이션 파일 미작성 |
| `backend/app/models/auth.py` | ORM 모델 미작성 |
| `backend/app/models/task.py` | ORM 모델 미작성 |
| `backend/app/deps.py` | 의존성 함수 미작성 |
| `backend/app/api/routers/auth.py` | 라우터 미작성 |
| `backend/app/api/routers/users.py` | 라우터 미작성 |
| `backend/app/api/routers/projects.py` | 라우터 미작성 |
| `backend/app/api/routers/issues.py` | 라우터 미작성 |
| `backend/app/notifications/` 전체 | 알림 모듈 미작성 |
| `frontend/app/(auth)/` 전체 | 프론트엔드 인증 화면 미작성 |
| `frontend/app/(app)/issues/` 전체 | 이슈 화면 미작성 |
| `frontend/lib/auth.ts` | 토큰 관리 유틸 미작성 |
| `frontend/lib/swr-hooks.ts` | SWR 훅 미작성 |

---

## 10. 참고: 기존 코드베이스 구조

```
backend/app/
├── api/
│   ├── main.py              ← FastAPI 앱 (CORS, 스케줄러 포함) — 기존 라우터 있음
│   └── routers/
│       ├── flow.py          ← 기존 (건드리지 말 것)
│       ├── dashboard.py     ← 기존
│       ├── reports.py       ← 기존
│       └── connectors.py    ← 기존
├── analytics/               ← 기존
├── collector/               ← 기존
├── connectors/              ← 기존
├── etl/                     ← 기존
├── narrator/                ← 기존
├── config.py                ← Settings (신규 env vars 추가 필요)
├── db.py                    ← SessionLocal (기존 사용 가능)
└── scheduler.py             ← 기존
```

Alembic 기존 마이그레이션: `0001_raw_redmine.py`, `0002_mart.py`, `0003_mvp.py`

---

## 11. Suggested Skills

다음 세션에서 유용한 스킬:

- **`/grill-me`** — 구현 중 모호한 결정 사항 발생 시. 예: "이슈 필터 UI 어떻게 할까?"
- **`/handoff`** — Phase 1 구현 완료 후 다음 세션으로 인수인계할 때

---

## 12. 메모리

프로젝트 정보는 아래 경로에 저장됨:
```
C:\Users\Manna\.claude\projects\C--Users-Manna-project\memory\project_taskinsight.md
C:\Users\Manna\.claude\projects\C--Users-Manna-project\memory\MEMORY.md
```
