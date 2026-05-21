# TaskView 마스터 스펙 v2
> **작성일:** 2026-05-21  
> **기준:** TaskInsight_Spec.md (v1) + /grill-me 세션 결정사항 반영  
> **상태:** MVP 개발 준비 완료

---

## 0. TL;DR — 30초 요약

- **제품명:** TaskView
- **포지션:** Redmine 데이터를 분석해 팀장/PM의 의사결정을 돕는 한국형 SEI 플랫폼
- **1차 사용자:** 팀장 + PM (중간관리자). C-level은 2차 (주간보고 수신).
- **핵심 사용 트리거:** ① 주간 회의 전 보고 준비 ② "왜 이 이슈가 막혔지?" 파악
- **MVP 4화면:** Flow+이슈 타임라인 / 주간보고 / Dashboard / Settings
- **핵심 차별점:** 이슈 타임라인 자동 설명 (한국어, qwen3.6:35b-a3b)
- **액션 범위:** Read-only. Redmine 데이터 변경 없음.
- **기술 스택:** PostgreSQL 17 + TimescaleDB / FastAPI / Next.js 16 + Tailwind 4 / Ollama
- **LLM:** qwen3.6:35b-a3b (타임라인+처방) / qwen2.5-coder:14b (관찰 레이어)
- **배포:** localhost 시작, 인증 없음. 이후 Tailscale + 사내망.

---

## 1. 사용자 & 사용 시나리오

### 1.1 1차 사용자: 팀장 / PM

| 항목 | 내용 |
|---|---|
| 역할 | 개발팀 팀장, PM/PO |
| 팀 규모 | 5~15명 |
| 의사결정 단위 | 스프린트/주간 |
| 주요 불편 | Redmine에서 "왜 이게 안 끝났는지" 파악 불가. 주간보고 수동 정리. |

### 1.2 2차 사용자: 본부장 / CTO

- 월간 보고서 수신자 (MVP 이후)
- Dashboard 경영진 뷰 (MVP에서는 팀장 뷰와 동일)

### 1.3 핵심 사용 트리거 2가지

**트리거 A — 주간 회의 전 보고 준비**
> 팀장이 "이번 주 보고서 생성" 버튼 클릭 → 3항목 자동 생성 → 회의에서 활용

**트리거 B — 블로킹 이슈 원인 파악**
> Flow 화면에서 "검수 대기 53건, 평균 22일" 확인 → 이슈 클릭 → 타임라인 자동 설명 → 원인 파악 → Redmine에서 직접 조치

---

## 2. MVP 범위

### 2.1 MVP 4화면

| 화면 | 경로 | 핵심 가치 |
|---|---|---|
| Flow + 이슈 타임라인 | `/flow` | "어디서, 왜 막히는가" |
| 주간보고 | `/reports/weekly` | "이번 주 보고할 것 3가지" |
| Dashboard | `/dashboard` | "전체 흐름 한 눈에" |
| Settings | `/settings` | Redmine 연동 설정 |

**MVP 제외 (v2):**
- Home ("오늘 살펴볼 것") — `/flow` redirect로 임시 대체
- Meeting (면담 준비 자료) — 복잡도 높음, v2
- 팀즈 알림 — v2
- PDF 내보내기 — v2
- 인증/로그인 — v2

### 2.2 기존 페이지 유지

`/executive`, `/manager`, `/team`, `/insight` — MVP 기간 공존. redirect 전환은 v2에서.

---

## 3. 기술 환경

### 3.1 호스트 & 디렉터리

- **호스트:** macOS Mac Studio, zsh, Python 3.11 (.venv)
- **프로젝트 루트:** `~/Taskview/`

```
~/Taskview/
├── backend/
│   ├── .venv/
│   ├── alembic/
│   │   ├── 0001_phase1_raw
│   │   ├── 0002_phase2_mart
│   │   └── 0003_mvp              ← 신규 (raw rename + connector + explanation)
│   └── app/
│       ├── connectors/           ← BaseConnector ABC + RedmineConnector (UI 없음)
│       │   ├── base.py
│       │   ├── registry.py
│       │   └── redmine/connector.py
│       ├── collector/            ← 기존 유지 (sync 완료 후 ETL 자동 트리거 추가)
│       ├── etl/                  ← 기존 유지
│       ├── analytics/            ← 기존 유지 (raw_redmine_* 테이블명만 수정)
│       ├── narrator/             ← LLM 호출 모듈 (신규)
│       │   ├── issue_explainer.py
│       │   └── weekly_report.py
│       └── api/
│           └── routers/
│               ├── flow.py       ← 신규
│               ├── reports.py    ← 신규
│               └── connectors.py ← 신규 (Settings용 Redmine 설정만)
└── frontend/
    └── src/
        └── app/
            ├── flow/page.tsx
            ├── reports/weekly/page.tsx
            ├── dashboard/page.tsx
            └── settings/page.tsx
```

### 3.2 .env 핵심 값 (변경 없음)

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=flowlens
POSTGRES_USER=flowlens
POSTGRES_PASSWORD=change-me
sqlalchemy.url=postgresql+psycopg://flowlens:change-me@localhost:5433/flowlens

REDMINE_BASE_URL=http://redmine.mannaplanet.co.kr:5555/redmine
REDMINE_API_KEY=<redacted>
COLLECTOR_INITIAL_LOOKBACK_DAYS=3650

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_TIMELINE=qwen3.6:35b-a3b      ← 변경 (coder:14b → qwen3.6)
OLLAMA_MODEL_NARRATIVE=qwen2.5-coder:14b   ← 관찰 레이어 유지
OLLAMA_MODEL_HEAVY=qwen3.6:35b-a3b
```

### 3.3 DB 인스턴스

- **PostgreSQL 17** — 5433 (TaskView 전용)
- **TimescaleDB 2.26.4**
- **시작:** `/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/flowlens-pg17 -l /opt/homebrew/var/flowlens-pg17/server.log start`

---

## 4. 현재 데이터 현황

| Table | Rows | MVP 후 신규명 |
|---|---|---|
| raw_issues | 16,092 | raw_redmine_issues |
| raw_journals | 97,302 | raw_redmine_journals |
| raw_time_entries | 20 | raw_redmine_time_entries |
| raw_users | 77 | raw_redmine_users |
| raw_projects | 6 | raw_redmine_projects |
| raw_versions | 0 | raw_redmine_versions |
| fct_state_transition | 45,259 | 변경 없음 |
| fct_issue_flow | 16,092 | 변경 없음 |
| fct_wip_daily | 31,161 | 변경 없음 |
| fct_throughput_weekly | 574 | 변경 없음 |
| dim_project / dim_user | 6 / 88 | 변경 없음 |

---

## 5. DB 스키마 변경 (alembic 0003)

### 5.1 raw 테이블 rename (다운타임 2~3분)

```sql
ALTER TABLE raw_issues       RENAME TO raw_redmine_issues;
ALTER TABLE raw_journals     RENAME TO raw_redmine_journals;
ALTER TABLE raw_time_entries RENAME TO raw_redmine_time_entries;
ALTER TABLE raw_users        RENAME TO raw_redmine_users;
ALTER TABLE raw_projects     RENAME TO raw_redmine_projects;
ALTER TABLE raw_versions     RENAME TO raw_redmine_versions;
```

### 5.2 connector_instance (Settings용 — 최소 버전)

```sql
CREATE TABLE connector_instance (
    id SERIAL PRIMARY KEY,
    connector_type VARCHAR(50) NOT NULL,   -- "redmine"
    instance_name VARCHAR(200) NOT NULL,   -- "사내 Redmine"
    config JSONB NOT NULL,                 -- {base_url, api_key, lookback_days}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 초기 데이터 시드 (.env 값 복사)
INSERT INTO connector_instance (connector_type, instance_name, config)
VALUES ('redmine', '사내 Redmine',
        '{"base_url": "http://redmine.mannaplanet.co.kr:5555/redmine",
          "lookback_days": 3650}'::jsonb);
```

### 5.3 LLM 설명 캐시 테이블

```sql
CREATE TABLE fct_issue_explanation (
    issue_id INTEGER PRIMARY KEY,
    explanation TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(50),          -- "qwen3.6:35b-a3b"
    is_stale BOOLEAN DEFAULT FALSE      -- 새 저널 도착 시 TRUE
);
```

### 5.4 주간보고 저장 테이블

```sql
CREATE TABLE fct_weekly_report (
    id SERIAL PRIMARY KEY,
    project_id INTEGER,
    period_start DATE,
    period_end DATE,
    throughput_current INTEGER,
    throughput_previous INTEGER,
    bottleneck_summary JSONB,           -- top 3 bottleneck
    forecast_p50_weeks INTEGER,
    forecast_change_weeks INTEGER,      -- 전주 대비 변화
    narrative_text TEXT,               -- LLM 생성 서술
    generated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. 백엔드 아키텍처

### 6.1 Connector 추상화 (UI 없음, 구조만)

```python
# backend/app/connectors/base.py
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    connector_type: str
    display_name: str
    category: str   # "task_management" | "code_repo" | "messaging"
    status: str     # "active" | "coming_soon"

    @abstractmethod
    def test_connection(self, config: dict) -> dict: ...

    @abstractmethod
    def fetch_resource(self, resource_type: str, config: dict, since) -> list: ...
```

```python
# backend/app/connectors/registry.py
from .redmine.connector import RedmineConnector

CONNECTORS = {
    "redmine": RedmineConnector,
    # jira, asana 등은 coming_soon 껍데기로 추후 추가
}

def get_connector(connector_type: str) -> BaseConnector:
    return CONNECTORS[connector_type]()
```

### 6.2 LLM 모듈 — issue_explainer.py

**입력 데이터 전략 (옵션 C: 선별 입력)**

```python
# 상태 전환 + 담당자 변경 + 코멘트 있는 저널만 선별
def build_issue_context(issue_id: int) -> dict:
    return {
        "issue": {
            "id": issue_id,
            "subject": ...,
            "created_on": ...,
            "current_status": ...,
            "current_assignee": ...,
        },
        "state_transitions": [
            # fct_state_transition 에서
            {"from": "in_progress", "to": "review", "at": "2025-01-10",
             "days_in_from": 21}
        ],
        "assignee_changes": [...],      # 담당자 변경 저널만
        "comments": [                   # notes != '' 인 저널만 (최대 10건)
            {"at": "2025-01-15", "author": "현복최", "text": "..."}
        ],
        "metrics": {
            "total_days": 486,
            "current_stage": "review",
            "days_in_current_stage": 1300,
            "risk_score": 70
        }
    }
```

**시스템 프롬프트:**
```
당신은 TaskView의 이슈 분석 모듈입니다.
주어진 이슈의 타임라인 데이터를 바탕으로 한국어 보고서체(~함, ~됨)로
3~4문장 설명을 작성하세요.

규칙:
- "약점", "문제점", "부진" 단어 사용 금지 → "함께 살펴볼 영역"
- 개인 평가 금지. 상황 설명만.
- 권장 조치 1~2가지 제안 (권유형: ~을 권장합니다)
- 최대 150자
```

### 6.3 LLM 캐싱 전략

| 시점 | 동작 |
|---|---|
| 매일 새벽 2시 | 위험점수 상위 20건 사전 생성 → fct_issue_explanation 저장 |
| 팀장이 이슈 클릭 | 캐시 있으면 즉시 반환. 없으면 온디맨드 생성 (30초) + 저장 |
| 새 저널 도착 시 | 해당 이슈 is_stale = TRUE → 다음 배치 또는 클릭 시 재생성 |

### 6.4 ETL 파이프라인

```
Redmine sync 완료
    └→ ETL 자동 트리거 (callback)
           └→ raw_redmine_* → fct_* 갱신
                  └→ [매일 새벽 2시] LLM 배치 (위험점수 재계산 → 상위 20건 재생성)
```

### 6.5 주간보고 생성 (수동 트리거)

```python
# POST /v1/reports/weekly/generate
# 팀장이 버튼 클릭 → 생성 → fct_weekly_report 저장

def generate_weekly_report(project_id: int, period_weeks: int = 1) -> dict:
    throughput = get_throughput_comparison(project_id, period_weeks)
    bottleneck = top_bottleneck_groups(limit=3, project_id=project_id)
    forecast = monte_carlo_forecast(project_id)
    narrative = llm_generate_narrative(throughput, bottleneck, forecast)

    save_to_fct_weekly_report(...)
    return report
```

---

## 7. 신규 API 엔드포인트 (MVP)

| Method | Path | 설명 |
|---|---|---|
| GET | /v1/flow/stages | 단계별 건수 + 평균 체류일 |
| GET | /v1/flow/issues | 이슈 목록 (단계/프로젝트/기간 필터) |
| GET | /v1/flow/issue/{id}/explanation | LLM 타임라인 설명 (캐시 우선) |
| POST | /v1/reports/weekly/generate | 주간보고 생성 (수동 트리거) |
| GET | /v1/reports/weekly/latest | 최근 생성 보고서 조회 |
| GET | /v1/dashboard/summary | Speed + Effectiveness + Quality |
| GET | /v1/connectors/instances | 연동 목록 (Settings용) |
| POST | /v1/connectors/test | 연결 테스트 |
| PUT | /v1/connectors/{id} | 연동 설정 수정 |

**기존 9개 엔드포인트 전부 유지.**

---

## 8. 화면별 UX

### 8.1 Flow + 이슈 타임라인

```
┌─ 글로벌 필터 ──────────────────────────────────────────────────────┐
│  📁 만나 플랫폼 ▾   📅 최근 6개월 ▾                                 │
└────────────────────────────────────────────────────────────────────┘

┌─ 흐름 진단 (펀넬) ──────────────────────────────────────────────────┐
│                                                                      │
│  [대기 중]    [진행 중]    [검수 중]    [완료]                       │
│   321건        85건        53건 ←★     38건/주                      │
│   평균 8일     평균 14일   평균 22일    ────                         │
│                            ↑ 클릭 시 하단 필터                      │
└──────────────────────────────────────────────────────────────────────┘

┌─ 이슈 목록 (체류일 내림차순) ───────────────────────────────────────┐
│  #     제목                    담당자    체류일    위험점수           │
│  10729 결제 모듈 검수 대기     현복최    1,300일   70  🔴             │
│  8745  API 연동 재작업         원배문      847일   70  🔴             │
│  ...                                                                 │
└──────────────────────────────────────────────────────────────────────┘
```

**이슈 클릭 → 타임라인 모달:**
```
┌─ #10729 결제 모듈 검수 대기 ────────────────────────────────────────┐
│ 📅 타임라인                                                          │
│ 2024-12-15  생성 (담당자: 원배문)                                    │
│ 2024-12-20  진행 중 전환                                              │
│ 2025-01-10  검수 요청                                                 │
│ 2025-01-15  검수자(현복최) 배정                                       │
│ 2025-01-15 ~ 현재  검수 대기 1,300일                                  │
│                                                                      │
│ 🤖 TaskView 분석                              ← qwen3.6:35b-a3b     │
│ "검수 요청 후 1,300일이 경과됨. 현복최 님이 타 프로젝트 배정 이후    │
│  응답이 없는 상태로, 검수자 재배정 또는 일감 종료 검토를 권장함."    │
│                                                                      │
│  [Redmine에서 열기 ↗]                                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 주간보고

```
┌─ 주간보고 ─────────────────────────────  [이번 주 보고서 생성]  ──┐
│  만나 플랫폼 | 2026년 5월 11일(월) ~ 5월 17일(일)                   │
│                                                                      │
│ ┌─ 1. 이번 주 완료량 ──────────────────────────────────────────┐   │
│ │  22건 완료 ↓3건 (지난 주 25건 대비)                           │   │
│ │  "완료량이 소폭 감소함. 검수 대기 53건 중 5건이 이번 주 처리됨."│   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌─ 2. 정체 구간 현황 ──────────────────────────────────────────┐   │
│ │  🔴 검수 중  53건  평균 22일 체류 (전체 소요일의 25%)          │   │
│ │  🟠 보류됨   30건  평균 54일 체류                              │   │
│ │  "검수 단계가 주요 정체 구간으로, 검수자 배정 재검토를 권장함."│   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌─ 3. 완료 예측 변화 ──────────────────────────────────────────┐   │
│ │  P50: 21주 후 (2026-10-02) ── 지난 주 대비 변화 없음          │   │
│ │  P85: 24주 / P95: 26주                                        │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  생성 시각: 2026-05-17 09:23  [이전 보고서 보기]                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.3 Dashboard (Speed + Effectiveness + Quality)

```
┌─ Speed (속도) ──────────────────────────────────────────────────────┐
│  전체 소요일 86일 ↓4   주간 완료량 22건 ↑3   완료 예측 21주(보통)  │
│  "처리 기간이 지난달 대비 4일 단축됨."                               │
└──────────────────────────────────────────────────────────────────────┘

┌─ Effectiveness (효율) ──────────────────────────────────────────────┐
│  업무 쏠림 지수 0.63 (높음)   진행 중 업무 493건   미할당 18건       │
│  "상위 3명이 진행 업무 34% 담당. 검수자 그룹 쏠림 가장 심함."       │
└──────────────────────────────────────────────────────────────────────┘

┌─ Quality (품질) ────────────────────────────────────────────────────┐
│  재작업 비율 8%   반려율 2%   이상 신호 12건                         │
│  "이상 신호 12건 중 3건이 1,000시간 초과 대기 상태."                 │
└──────────────────────────────────────────────────────────────────────┘
```

*Business Impact 섹션: v2에서 추가 (이슈 분류 태깅 전략 별도 결정 후)*

### 8.4 Settings — Redmine 연동

```
┌─ 연동 설정 ─────────────────────────────────────────────────────────┐
│                                                                      │
│ ✅ 사내 Redmine                         마지막 동기화: 5분 전 · 정상 │
│                                                                      │
│  연동 이름:    [사내 Redmine                    ]                    │
│  Redmine URL:  [http://redmine.mannaplanet.co.kr:5555/redmine]       │
│  API 키:       [••••••••••••••••••              ] [발급 방법 보기]   │
│                                                                      │
│                         [연결 테스트]  [저장]  [지금 동기화]         │
│                                                                      │
│ ─────────────────────────────────────────────────────────────────── │
│  다른 업무관리 도구 연동은 추후 지원 예정입니다.                      │
│  (Jira, Asana, ClickUp, Notion 등)                                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 9. LLM 전략 (확정)

| 역할 | 모델 | 비고 |
|---|---|---|
| 이슈 타임라인 자동 설명 | `qwen3.6:35b-a3b` | 핵심 차별점 |
| 주간보고 서술 생성 | `qwen3.6:35b-a3b` | |
| 처방 레이어 (v2) | `qwen3.6:35b-a3b` | |
| Narrator 관찰 레이어 | `qwen2.5-coder:14b` | 구조화 출력 |

**캐싱 정책:**
- 위험점수 상위 20건: 매일 새벽 2시 사전 생성
- 나머지: 온디맨드 생성 + `fct_issue_explanation` 저장
- 새 저널 도착 시: `is_stale = TRUE` → 다음 클릭 또는 배치에서 재생성

---

## 10. 디자인 원칙 & 토큰

*(v1 스펙 그대로 유지)*

```css
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

--color-critical: #DC2626;
--color-warning:  #F59E0B;
--color-normal:   #6B7280;
--color-good:     #059669;
--color-accent:   #2563EB;
```

**색상 의미:** 빨강(즉시 조치) / 주황(주시) / 회색(정상) / 초록(개선됨)

**글로벌 필터:** 프로젝트 + 기간 (1/3/6/12개월). MVP에서 팀원 필터 제외.

---

## 11. 한국어 용어 사전 (v1 확정사항 유지)

| 영문 | 한국어 |
|---|---|
| Bottleneck | 정체 구간 |
| Cycle Time | 처리 기간 |
| Lead Time | 전체 소요일 |
| Queue Time | 대기 기간 |
| Review Wait | 검수 대기 |
| WIP | 진행 중 업무 |
| Throughput | 주간 완료량 |
| Forecast | 완료 예측 |
| Risk | 지연 위험 |
| Anomaly | 이상 신호 |
| Gini | 쏠림 지수 |
| P50 / P85 / P95 | 보통 / 보수적 / 안전 |
| Backlog | 대기 중 |
| In Progress | 진행 중 |
| Review | 검수 중 |
| Rework | 재작업 |
| Blocked | 보류됨 |
| Narrator | 자동 분석 메모 |

**표현 규칙:**
- "직원/사원" → "구성원"
- "약점/문제점/부진" → "함께 살펴볼 영역" (Meeting 화면)
- 보고서체: 단문 (~함, ~됨). 권장은 권유형 (~을 권장합니다)

---

## 12. 윤리 가드레일

1. **개인 비교 화면 없음** — `/v1/users/compare` 엔드포인트 생성 금지
2. **단일 점수 개인 부여 금지** — 분석 함수가 user_id 받아 점수 반환하는 패턴 금지
3. **절대 임계치 없음** — "리드타임 X일 이내" 같은 절대 목표 금지, 상대 기준만
4. **면담 자료 본인 열람** — v2 Meeting 화면 구현 시 적용

---

## 13. 로드맵

### MVP (현재 → 6~8주)

**Week 1 — 기반 정비:**
- alembic 0003: raw_* rename + connector_instance + fct_issue_explanation + fct_weekly_report
- BaseConnector ABC + RedmineConnector (구조만, UI 없음)
- 기존 분석 모듈 SQL: raw_* → raw_redmine_* 일괄 수정
- 디자인 토큰 + Pretendard + 한국어 라벨 (`labels.ts`)
- 새 사이드바 (Flow/주간보고/Dashboard/Settings, 72px)

**Week 2~3 — Flow 화면:**
- `/v1/flow/stages`, `/v1/flow/issues` API
- 펀넬 차트 컴포넌트
- 이슈 목록 (정렬/필터)
- 글로벌 필터바 (프로젝트 + 기간)

**Week 3~4 — 이슈 타임라인 자동 설명:**
- `narrator/issue_explainer.py` (qwen3.6:35b-a3b)
- `/v1/flow/issue/{id}/explanation` API (캐시 우선)
- 타임라인 모달 컴포넌트
- 새벽 2시 배치 (위험점수 상위 20건 사전 생성)

**Week 4~5 — Dashboard:**
- Speed + Effectiveness + Quality 3섹션
- MetricCard 컴포넌트 (숫자 + 추이 + 한 줄 해석)
- `/v1/dashboard/summary` API 확장

**Week 5~6 — 주간보고:**
- `narrator/weekly_report.py` (3항목 LLM 서술)
- `/v1/reports/weekly/generate`, `/latest` API
- 주간보고 화면 + "이번 주 보고서 생성" 버튼

**Week 6~7 — Settings + 마무리:**
- Settings 화면 (Redmine 연동 폼)
- `/v1/connectors/*` API (목록, 테스트, 수정)
- ETL 자동 연계 (sync 완료 후 트리거)
- 전체 통합 테스트

### v2 (MVP 이후)

| 기능 | 내용 |
|---|---|
| Home 화면 | "오늘 살펴볼 것" + 자동 분석 메모 |
| Meeting 화면 | 면담 준비 자료 + 본인 열람 |
| Dashboard Business Impact | 이슈 분류 태깅 전략 결정 후 |
| 팀즈 알림 | Incoming Webhook |
| PDF 내보내기 | 주간보고 PDF |
| 인증 | Tailscale + 단순 Bearer 토큰 |
| 자연어 질의 | 한국어 Q&A |
| 처방 레이어 | prescription.py 룰 30~50개 |
| 다중 사용자 | 팀장 2~5명 접속 |

---

## 14. 검증 명령어

```bash
# DB 카운트 확인
PGPASSWORD=change-me /opt/homebrew/opt/postgresql@17/bin/psql \
  -h localhost -p 5433 -U flowlens -d flowlens -c "
SELECT 'raw_redmine_issues' AS t, COUNT(*) FROM raw_redmine_issues UNION ALL
SELECT 'raw_redmine_journals', COUNT(*) FROM raw_redmine_journals UNION ALL
SELECT 'fct_issue_explanation', COUNT(*) FROM fct_issue_explanation UNION ALL
SELECT 'connector_instance', COUNT(*) FROM connector_instance;"

# Backend 기동
cd ~/Taskview/backend && source .venv/bin/activate && \
  uvicorn app.api.main:app --reload --port 8000

# Frontend 기동
cd ~/Taskview/frontend && npm run dev

# LLM 모델 확인
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"'

# 이슈 설명 생성 테스트
curl http://localhost:8000/v1/flow/issue/10729/explanation
```

---

## 15. 결정 이력

| # | 결정 | 근거 |
|---|---|---|
| D01 | 1차 사용자: 팀장 + PM | C-level은 2차, 월간 보고 수신자 |
| D02 | 사용 트리거: 주간 회의 전 + 블로킹 파악 | 실제 사용 패턴 기반 |
| D03 | MVP 4화면: Flow+타임라인/주간보고/Dashboard/Settings | 핵심 가치 집중 |
| D04 | Patch 0 연동 UI 생략 | 팀장 사용 불필요, 4주 지연 회피 |
| D05 | BaseConnector ABC 구조만 유지 | 향후 Jira 등 확장 가능성 보존 |
| D06 | Dashboard: Speed+Effectiveness+Quality (Business Impact 제외) | 태깅 전략 미결정 |
| D07 | LLM: qwen3.6:35b-a3b (타임라인+처방) | 한국어 품질 우선 |
| D08 | LLM 입력: 상태전환+담당자변경+코멘트 저널 선별 | 노이즈 최소화 |
| D09 | LLM 캐싱: 상위20 배치 + 온디맨드 캐시 | 첫 클릭 30초 UX 위험 완화 |
| D10 | Read-only. Redmine 쓰기 없음 | 데이터 오염 위험, 도입 장벽 |
| D11 | 주간보고: 3항목만 (완료량/정체/예측) | DX Core 4 전체는 Dashboard 전용 |
| D12 | 주간보고: 화면 전용, PDF 없음 | 한국어 폰트 이슈, MVP 복잡도 |
| D13 | 주간보고: 수동 버튼 트리거 | 회의 전 의도적 사용 패턴에 부합 |
| D14 | ETL: sync 완료 후 자동 트리거 | 데이터 신선도 1시간 이내 |
| D15 | LLM 배치: 매일 새벽 2시 | 업무 시간 외 부하 |
| D16 | 배포: localhost 시작, 인증 없음 | MVP 복잡도 최소화 |
| D17 | 글로벌 필터: 프로젝트 + 기간만 | 팀원 필터는 v2 |
| D18 | Flow UX: 펀넬 + 이슈 목록 + 글로벌 필터 | 클릭 → 드릴다운 패턴 |

---

## 16. 새 대화에서 이어가기

> 첨부 `TaskInsight_Spec_v2.md` 기준으로 작업합니다.
> 현재 상태: MVP 설계 완료, **Week 1 개발 직전**.
>
> 시작점: alembic 0003 마이그레이션 작성 + raw_* rename + BaseConnector ABC + 디자인 토큰 적용.
> 본 문서의 모든 결정사항(특히 15장 결정 이력)을 준수하고, 미결 사항은 반드시 확인 요청.

---

*TaskView Master Spec v2 — 2026-05-21*
