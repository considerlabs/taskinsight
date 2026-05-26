# TaskInsight — 마스터 컨텍스트

> **AI 에이전트에게:** 이 파일을 모든 세션의 첫 번째로 읽으세요.
> 이 문서는 전체 시스템의 목적, 아키텍처, 결정사항을 담은 단일 진실 공급원(Single Source of Truth)입니다.
> 코드를 작성하기 전에 반드시 `docs/DOMAIN.md`, `docs/SCHEMA.md`, `docs/API_SPEC.md`도 읽으세요.

---

## 제품 정의

**TaskInsight**는 두 가지 기능을 하나의 시스템으로 통합한 플랫폼입니다.

1. **업무관리 (Issue Management)** — Redmine을 대체하는 자체 이슈 트래킹 시스템
2. **분석 대시보드 (SEI Dashboard)** — 업무 데이터를 실시간 분석하여 팀장/PM의 의사결정 지원

### 핵심 차별점
- 이슈를 입력하면 **분석이 즉시 반영**됨 (Redmine sync 지연 없음)
- 이슈 타임라인을 LLM이 **한국어로 자동 설명**
- 주간보고를 **버튼 하나로 자동 생성**
- 팀 내부망 전용, 외부 노출 없음

---

## 사용자

| 역할 | 설명 | 주요 사용 시나리오 |
|---|---|---|
| 시스템 관리자 | 전체 시스템 설정, 사용자 계정 관리 | 사용자 일괄 등록, 시스템 설정 |
| 프로젝트 관리자 | 프로젝트 설정, 멤버 관리, 이슈 전체 권한 | 스프린트 계획, 이슈 배정, 주간보고 생성 |
| 팀원 | 이슈 생성·수정·댓글·시간기록 | 일일 업무 입력, 상태 변경 |
| 뷰어 | 읽기 전용 | 현황 모니터링 |

**1차 사용자:** 팀장 + PM (분석 대시보드 주 사용)
**2차 사용자:** 개발팀원 (이슈 입력/관리)
**규모:** 100명 이상 동시 사용, 단일 조직(사내망 전용)

---

## 아키텍처

### 배포 구조
```
사내 Linux 서버
└── Docker Compose
    ├── nginx (리버스 프록시, 80/443)
    ├── frontend (Next.js, :3000)
    ├── backend (FastAPI, :8000)
    ├── postgres (PostgreSQL 17 + TimescaleDB, :5433)
    ├── redis (캐시 + 세션, :6379)
    └── ollama (LLM, :11434)
```

### 데이터 흐름
```
사용자 이슈 입력
    → backend API
    → issue_* 테이블 (즉시 저장)
    → ETL 이벤트 트리거 (실시간)
    → fct_issue_snapshot 갱신
    → 분석 API 응답 반영

[마이그레이션 경로]
Redmine (아카이브)
    → 1회성 마이그레이션 스크립트
    → issue_* 테이블 (히스토리 보존)

[Redmine 커넥터 유지]
기존 외부 Redmine (읽기 전용)
    → RedmineConnector
    → 분석 병행 가능
```

### 핵심 설계 원칙

1. **단일 DB**: 업무관리 + 분석이 같은 PostgreSQL 인스턴스 사용. ETL이 즉시 동작.
2. **Read-after-write consistency**: 이슈 저장 즉시 분석 지표에 반영.
3. **역할은 프로젝트 단위**: 한 사용자가 프로젝트A에서 관리자, 프로젝트B에서 팀원 가능.
4. **워크플로우는 프로젝트별 설정**: 기본값은 4단계(대기중→진행중→검수중→완료), 변경 가능.
5. **API key 절대 코드에 하드코딩 금지**: 모든 시크릿은 `.env` 또는 DB `connector_instance.config`.
6. **Python 3.9 호환**: 모든 백엔드 파일 최상단에 `from __future__ import annotations` 필수.
7. **Qwen3 모델 호출 시 `think: False` 필수**: 없으면 thinking token 소비 후 content 비어있음.

---

## 기술 스택

### 백엔드
| 항목 | 기술 | 버전 | 비고 |
|---|---|---|---|
| 언어 | Python | 3.9+ | `from __future__ import annotations` 필수 |
| 웹 프레임워크 | FastAPI | ≥0.115 | |
| ORM | SQLAlchemy | ≥2.0 | `text()` 기반 raw SQL 사용 |
| DB 드라이버 | psycopg3 | ≥3.1 | psycopg2 아님. JSONB는 `Jsonb()` 래핑 |
| 마이그레이션 | Alembic | ≥1.13 | |
| 인증 | python-jose + passlib | - | JWT HS256 |
| 스케줄러 | APScheduler | ≥3.10 | 야간 배치 |
| HTTP 클라이언트 | httpx | ≥0.27 | Ollama 호출 |
| 캐시 | redis-py | ≥5.0 | |

### 프론트엔드
| 항목 | 기술 | 버전 |
|---|---|---|
| 프레임워크 | Next.js App Router | 16 |
| 언어 | TypeScript | strict mode |
| 스타일 | Tailwind CSS | v4 |
| 폰트 | Pretendard Variable | - |
| 아이콘 | lucide-react | - |
| 상태관리 | React useState/useContext | - |
| HTTP | fetch (native) | - |

### 인프라
| 항목 | 기술 |
|---|---|
| DB | PostgreSQL 17 + TimescaleDB |
| 캐시 | Redis 7 |
| LLM | Ollama (`qwen3.6:35b-a3b`, `qwen2.5-coder:14b`) |
| 컨테이너 | Docker + Docker Compose |
| 프록시 | Nginx |

---

## 디렉터리 구조

```
TaskInsight/
├── docs/                          ← 설계 문서 (이 파일 포함)
│   ├── CONTEXT.md                 ← 마스터 컨텍스트 (지금 읽는 파일)
│   ├── DOMAIN.md                  ← 도메인 모델 & 용어 사전
│   ├── SCHEMA.md                  ← 완전한 DB 스키마
│   ├── API_SPEC.md                ← API 엔드포인트 명세
│   ├── UI_SPEC.md                 ← 화면 명세
│   ├── SECURITY_SPEC.md           ← 인증/인가 규칙
│   ├── MIGRATION_PLAN.md          ← Redmine 데이터 마이그레이션
│   ├── INFRA_SPEC.md              ← 서버 배포 명세
│   └── adr/                       ← 아키텍처 결정 기록
├── backend/
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_raw_redmine.py
│   │       ├── 0002_mart.py
│   │       ├── 0003_mvp.py
│   │       └── 0004_issue_management.py  ← 신규: 업무관리 테이블
│   └── app/
│       ├── config.py
│       ├── db.py
│       ├── auth/                   ← 신규: 인증 모듈
│       │   ├── __init__.py
│       │   ├── router.py           ← /v1/auth/*
│       │   ├── service.py          ← JWT 발급/검증
│       │   └── dependencies.py     ← FastAPI Depends(get_current_user)
│       ├── users/                  ← 신규: 사용자 관리
│       │   ├── __init__.py
│       │   ├── router.py           ← /v1/users/*
│       │   └── service.py
│       ├── projects/               ← 신규: 프로젝트 관리
│       │   ├── __init__.py
│       │   ├── router.py           ← /v1/projects/*
│       │   └── service.py
│       ├── issues/                 ← 신규: 이슈 관리 (핵심)
│       │   ├── __init__.py
│       │   ├── router.py           ← /v1/issues/*
│       │   └── service.py
│       ├── workflows/              ← 신규: 워크플로우 관리
│       │   ├── __init__.py
│       │   ├── router.py           ← /v1/workflows/*
│       │   └── service.py
│       ├── comments/               ← 신규: 댓글/저널
│       │   ├── __init__.py
│       │   └── router.py           ← /v1/issues/{id}/comments
│       ├── time_entries/           ← 신규: 시간 기록
│       │   ├── __init__.py
│       │   └── router.py           ← /v1/issues/{id}/time-entries
│       ├── attachments/            ← 신규: 파일 첨부
│       │   ├── __init__.py
│       │   └── router.py           ← /v1/attachments/*
│       ├── notifications/          ← 신규: 알림
│       │   ├── __init__.py
│       │   └── router.py           ← /v1/notifications/*
│       ├── analytics/              ← 기존 유지
│       ├── narrator/               ← 기존 유지
│       ├── connectors/             ← 기존 유지 (Redmine 커넥터)
│       ├── collector/              ← 기존 유지
│       ├── etl/                    ← 기존 + 신규 소스 처리
│       ├── scheduler.py            ← 기존 유지
│       └── api/
│           └── main.py             ← 라우터 통합
└── frontend/
    └── app/
        ├── (auth)/                 ← 신규: 로그인 페이지 (레이아웃 없음)
        │   └── login/page.tsx
        ├── (app)/                  ← 신규: 인증 필요 레이아웃
        │   ├── layout.tsx          ← 사이드바 + 인증 가드
        │   ├── flow/page.tsx       ← 기존
        │   ├── dashboard/page.tsx  ← 기존
        │   ├── reports/weekly/page.tsx ← 기존
        │   ├── settings/page.tsx   ← 기존
        │   ├── issues/             ← 신규
        │   │   ├── page.tsx        ← 이슈 목록
        │   │   └── [id]/page.tsx   ← 이슈 상세
        │   ├── projects/           ← 신규
        │   │   ├── page.tsx        ← 프로젝트 목록
        │   │   └── [id]/           ← 프로젝트 상세
        │   ├── milestones/         ← 신규
        │   └── admin/              ← 신규 (시스템 관리자 전용)
        │       ├── users/page.tsx
        │       └── system/page.tsx
        └── components/
            ├── (기존 컴포넌트 유지)
            ├── IssueForm.tsx       ← 신규
            ├── IssueDetail.tsx     ← 신규
            ├── CommentThread.tsx   ← 신규
            ├── WorkflowBoard.tsx   ← 신규 (칸반)
            ├── GanttChart.tsx      ← 신규
            └── NotificationBell.tsx ← 신규

```

---

## 데이터 모델 요약

> 상세 내용은 `docs/DOMAIN.md`와 `docs/SCHEMA.md` 참고

### 신규 핵심 테이블 (0004 마이그레이션)

```
users                    ← 시스템 사용자
projects                 ← 프로젝트
project_members          ← 프로젝트 멤버십 + 역할
workflow_statuses        ← 프로젝트별 이슈 상태 정의
workflow_transitions     ← 상태 전환 허용 규칙 (누가 어디서 어디로)
issues                   ← 이슈 (핵심)
issue_journals           ← 이슈 변경 이력 (모든 변경 기록)
issue_comments           ← 댓글 (notes가 있는 저널과 분리)
issue_attachments        ← 파일 첨부
time_entries             ← 시간 기록
milestones               ← 마일스톤/버전
notifications            ← 알림
```

### 기존 테이블 (유지)
```
raw_redmine_*            ← Redmine 원시 데이터 (아카이브)
fct_issue_snapshot       ← 분석용 스냅샷 (신규 issues 테이블도 소스로 추가)
fct_state_transition     ← 상태 전환 이력 (신규 issue_journals도 소스로 추가)
fct_throughput_daily     ← 처리량
fct_issue_explanation    ← LLM 캐시
fct_weekly_report        ← 주간보고
connector_instance       ← 외부 연동 설정
```

---

## API 네임스페이스

| 네임스페이스 | 설명 |
|---|---|
| `/v1/auth/*` | 로그인, 토큰 갱신, 로그아웃 |
| `/v1/users/*` | 사용자 CRUD (관리자), 프로필 |
| `/v1/projects/*` | 프로젝트 CRUD, 멤버 관리 |
| `/v1/projects/{id}/issues/*` | 프로젝트 이슈 목록/생성 |
| `/v1/issues/*` | 이슈 CRUD, 댓글, 시간기록, 첨부 |
| `/v1/issues/{id}/comments` | 댓글 CRUD |
| `/v1/issues/{id}/time-entries` | 시간기록 CRUD |
| `/v1/milestones/*` | 마일스톤 CRUD |
| `/v1/workflows/*` | 워크플로우 설정 |
| `/v1/notifications/*` | 알림 목록, 읽음 처리 |
| `/v1/attachments/*` | 파일 업로드/다운로드 |
| `/v1/flow/*` | 기존 분석 (유지) |
| `/v1/dashboard/*` | 기존 분석 (유지) |
| `/v1/reports/*` | 기존 분석 (유지) |
| `/v1/connectors/*` | 기존 외부 연동 (유지) |
| `/admin/*` | 관리자 전용 |

---

## 윤리 가드레일 (변경 없음)

1. 개인 비교 화면 없음 — `/v1/users/compare` 엔드포인트 생성 금지
2. 단일 점수 개인 부여 금지
3. 절대 임계치 없음, 상대 기준만
4. 개인 생산성 데이터는 본인만 열람 (v2 Meeting 화면)

---

## 한국어 용어 사전

> 전체 목록은 `docs/DOMAIN.md` 참고

| 영문 코드 | 화면 표시 | 설명 |
|---|---|---|
| `issue` | 이슈 | 업무 단위 |
| `project` | 프로젝트 | 이슈의 상위 그룹 |
| `milestone` | 마일스톤 | 버전/스프린트 |
| `workflow_status` | 상태 | 이슈의 현재 단계 |
| `assignee` | 담당자 | 이슈 담당자 |
| `reporter` | 등록자 | 이슈를 등록한 사람 |
| `journal` | 변경이력 | 이슈의 모든 변경 기록 |
| `time_entry` | 시간기록 | 작업 소요 시간 |
| `attachment` | 첨부파일 | 이슈에 첨부된 파일 |
| `notification` | 알림 | 시스템 내 알림 |
| `flow_stage` | 흐름단계 | 분석용 단계 그룹 (backlog/in_progress/review/done/blocked) |
| `risk_score` | 지연위험 | 0~100 위험 점수 |

---

## 현재 개발 상태 (2026-05-26 기준)

### 완료된 것
- [x] Redmine 데이터 수집 파이프라인 (raw_redmine_* 테이블)
- [x] ETL (fct_* 마트 테이블)
- [x] Flow 분석 API + 화면
- [x] Dashboard (Speed/Effectiveness/Quality)
- [x] 주간보고 자동 생성
- [x] LLM 이슈 타임라인 설명
- [x] Settings (Redmine 연동 관리)
- [x] Connector 추상화 (BaseConnector)

### 개발 예정 (이번 작업)
- [ ] 사용자 인증 (JWT)
- [ ] 업무관리 시스템 (이슈 CRUD, 댓글, 시간기록, 첨부)
- [ ] 프로젝트 관리 (멤버, 워크플로우 설정)
- [ ] 마일스톤/Gantt
- [ ] 알림 시스템
- [ ] Redmine 데이터 마이그레이션
- [ ] 관리자 화면

### DB 현황 (마이그레이션 시작 전)
| 테이블 | 행 수 |
|---|---|
| raw_redmine_issues | 16,111 |
| raw_redmine_journals | ~97,000 (수집 진행 중) |
| raw_redmine_users | 85 |
| raw_redmine_projects | 4 |
| fct_issue_snapshot | 16,111 |

---

## 코딩 규칙 (AI 에이전트 준수 필수)

### 백엔드
1. 모든 파일 첫 줄: `from __future__ import annotations`
2. 타입 힌트: `Optional[X]` (X | None 금지), `Union[A, B]` (A | B 금지)
3. JSONB 컬럼 업데이트: `from psycopg.types.json import Jsonb` → `Jsonb(data)` 래핑
4. LAG() OVER를 UPDATE에 직접 사용 불가 → CTE로 계산 후 JOIN UPDATE
5. 인증이 필요한 모든 엔드포인트: `current_user: User = Depends(get_current_user)` 의존성 추가
6. 권한 체크: `require_role(ProjectRole.MANAGER)` 데코레이터 또는 서비스 레이어에서 처리
7. SQL 인젝션 방지: 모든 쿼리는 `text("... WHERE id = :id")` + params dict 사용. f-string 직접 삽입 금지
8. Ollama 호출: `"think": False` 필수 (Qwen3 모델)

### 프론트엔드
1. 모든 API 호출: `lib/api.ts`의 `request<T>()` 래퍼 사용
2. 인증 토큰: `localStorage`의 `access_token` 자동 첨부 (api.ts에서 처리)
3. 권한별 UI 분기: `useAuth()` 훅의 `currentUser.role` 사용
4. 에러 처리: 401 → 자동 로그아웃 + `/login` 리다이렉트
5. 디자인 토큰: CSS custom properties 사용 (`var(--color-critical)` 등). 하드코딩 금지
6. 한국어 레이블: `lib/labels.ts`에 추가 후 import하여 사용

### 공통
1. 환경변수: `.env` 파일. 코드에 하드코딩 절대 금지
2. 파일 첨부 경로: `UPLOAD_DIR` 환경변수 기준 상대 경로 저장
3. 날짜/시간: DB 저장은 UTC (`TIMESTAMPTZ`). 화면 표시는 `Asia/Seoul` 변환
