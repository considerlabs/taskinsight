# TaskInsight 프로젝트 마스터 스펙 (Master Spec) v1

> **문서 목적.** 본 문서는 TaskView 프로젝트의 모든 설계 결정, 기술 컨텍스트, 경쟁 분석, 차별화 전략, 패치 로드맵을 단일 파일로 통합한 백업/인수인계용 마스터 문서입니다. 본 문서 한 개만 읽으면 어떤 LLM이든 본 프로젝트의 다음 작업(코드 패치 0번부터)을 곧바로 시작할 수 있어야 합니다.
>
> **문서 작성일.** 2026-05-21
> **버전.** v1 (패치 0 — 데이터 소스 추상화 + 연동 관리 UI 추가)
> **현재 상태.** 설계 완료, 패치 작업 대기 중. 사용자의 "패치 작업 시작" 명령 시점부터 패치 0 코드 작성에 진입.

---

## 0. TL;DR — 30초 요약

- **제품명:** TaskView 
- **포지션:** "TaskView는 Redmine을 비롯한 다양한 업무관리도구를 사용하는 한국 조직을 위한, 분석/처방/면담 워크플로우가 통합된, 윤리적 SEI(Software Engineering Intelligence) 플랫폼이다."
- **기술 스택:** PostgreSQL 18 + TimescaleDB / FastAPI / Next.js 16 + Tailwind 4 / Ollama qwen2.5-coder:14b / claude code / Pretendard 폰트
- **차별화 우선순위:** ① 이슈 타임라인 자동 설명 ② 한국형 보고서 자동 생성 ③ 면담 준비 자료의 깊이
- **알림 채널:** 팀즈(Microsoft Teams) Incoming Webhook 방식 단독
- **사이드바 IA:** Home / Dashboard / Flow / Meeting / Reports / Settings (5 + 1)
- **로드맵:** 패치 0 ~ 5 (총 약 15~20주, 4~5개월). 기존 자산 90%는 보존, 데이터 재수집 불필요
- **윤리 원칙:** 개인 단일 점수 금지, 절대 임계치 금지(상대 기준만), 면담 자료 본인 열람 기본, 학습 모드 4주
- **🆕 핵심 추가:** 패치 0(3~4주) — 데이터 소스 추상화 레이어 + 연동 관리 UI. 9개 도구 표시(Redmine 활성, 8개 "곧 지원"), 3개 카테고리(업무관리/메시징/코드 저장소) 분리

---

## 1. 프로젝트 정체성

### 1.1 제품명
**TaskView**

디렉터리 경로(`~/Taskview/`), DB명(`flowlens`), 패키지명(`app/`)은 비용 대비 효익 문제로 그대로 유지. 사용자 노출 영역(UI 헤더, 보고서 헤더, 워터마크, 알림 봇 이름, LLM 시스템 프롬프트의 자칭 등)은 모두 "TaskView"로 통일.

### 1.2 한 문장 포지션
> **"TaskView는 Redmine을 비롯한 다양한 업무관리도구를 사용하는 한국 조직을 위한, 분석/처방/면담 워크플로우가 통합된, 윤리적 SEI 플랫폼이다."**

각 수식어의 근거:
- **"Redmine을 비롯한 다양한 업무관리도구"**: 패치 0의 Connector 추상화로 단일 도구 종속 탈피. 8개 경쟁 SEI 서비스 중 Redmine을 1차 통합 대상으로 다루는 곳이 0개 → 즉시 시장 확보 + Multi-tool 확장성
- **"한국 조직을 위한"**: 한국어 UI/보고서 양식/조직 구조/노동 환경 대응 — 8개 경쟁사 누구도 안 함
- **"분석/처방/면담 워크플로우 통합"**: Jellyfish(분석) + LinearB(처방) + Fellow.ai(면담)을 합친 포지션
- **"윤리적"**: Pluralsight Flow의 실패와 Swarmia의 한계를 시스템 차원에서 회피
- **"SEI 플랫폼"**: Gartner가 인정하는 카테고리(Software Engineering Intelligence)

### 1.3 핵심 미션
업무관리도구 위에 얹는 분석 미들웨어로, **C-level/PM/팀에게 "왜 일어났는지"와 "다음에 무슨 일이 일어날지"를 보여주는 인사이트 엔진**. 단순 분석이 아니라 의사결정 코파일럿(observe → interpret → prescribe).

---

## 2. 기술 환경 정보

### 2.1 호스트 & 디렉터리
- **호스트:** macOS Mac Studio (guyskims-Mac-Studio), zsh, Python 3.11 (.venv)
- **프로젝트 루트:** `~/Taskview/`

```
~/Taskview/
├── backend/
│   ├── .venv/
│   ├── alembic/                 # 0001_phase1_raw, 0002_phase2_mart
│   ├── pyproject.toml
│   └── app/
│       ├── config.py            # pydantic-settings (.env 자동 로드)
│       ├── db.py                # session_scope
│       ├── logging_conf.py
│       ├── models/              # raw, meta, mart
│       ├── collector/           # redmine_client, sync_jobs, scheduler
│       │                        # ※ 패치 0에서 connectors/redmine/으로 이전
│       ├── connectors/          # 🆕 패치 0 신규
│       │   ├── base.py          # BaseConnector ABC
│       │   ├── registry.py      # 어댑터 등록/발견
│       │   ├── redmine/         # 활성
│       │   ├── jira/            # 껍데기 (NotImplementedError)
│       │   ├── asana/           # 껍데기
│       │   ├── github/          # 껍데기
│       │   ├── gitlab/          # 껍데기
│       │   ├── notion/          # 껍데기
│       │   ├── clickup/         # 껍데기
│       │   ├── monday/          # 껍데기
│       │   └── trello/          # 껍데기
│       ├── etl/                 # dims, cycle_time, wip, runner
│       ├── analytics/           # status_groups, bottleneck, risk, forecast,
│       │                        # resource, anomaly, critical_path, summary
│       ├── api/
│       │   ├── main.py
│       │   ├── deps.py
│       │   ├── schemas.py
│       │   └── routers/         # executive, manager, team, insight, meta
│       │                        # 🆕 connectors (패치 0)
│       ├── narrator/            # (빈 상태, STEP B'에서 채움)
│       ├── notifications/       # 🆕 패치 5
│       │   └── channels/teams.py
│       └── ws/                  # (빈 상태, 패치 5에서 채움)
└── frontend/                    # Next.js 16 + Tailwind 4 + TS
    ├── .env.local               # NEXT_PUBLIC_API_BASE=http://localhost:8000
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── globals.css
        │   ├── executive/page.tsx       # 패치 4까지 공존
        │   ├── executive/overview/page.tsx
        │   ├── manager/page.tsx
        │   ├── team/page.tsx
        │   ├── insight/page.tsx
        │   └── settings/connectors/     # 🆕 패치 0
        │       ├── page.tsx             # 연동 목록
        │       ├── new/page.tsx         # 새 연동 마법사
        │       └── [id]/page.tsx        # 연동 상세/수정
        ├── components/
        │   ├── Sidebar.tsx
        │   ├── GlobalFilter.tsx
        │   ├── ThemeToggle.tsx
        │   ├── KpiCard.tsx
        │   ├── DataTable.tsx
        │   ├── StateBox.tsx
        │   ├── connectors/              # 🆕 패치 0
        │   │   ├── ConnectorCard.tsx
        │   │   ├── ConnectionForm.tsx
        │   │   ├── ResourceSelector.tsx
        │   │   ├── StatusMappingTable.tsx
        │   │   └── SyncProgress.tsx
        │   └── charts/
        │       ├── BottleneckBar.tsx
        │       └── TeamLoadBar.tsx
        └── lib/
            ├── api.ts
            └── filters.ts
```

### 2.2 .env 핵심 값
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5433              # PG17 dedicated
POSTGRES_DB=flowlens            # 내부 명칭 유지(데이터 이관 회피)
POSTGRES_USER=flowlens
POSTGRES_PASSWORD=change-me
sqlalchemy.url=postgresql+psycopg://flowlens:change-me@localhost:5433/flowlens

# 🆕 패치 0 이후: Redmine 설정은 connector_instance 테이블로 이전
# 아래 값은 패치 0에서 자동 마이그레이션되어 첫 connector_instance 레코드로 저장됨
REDMINE_BASE_URL=http://redmine.mannaplanet.co.kr:5555/redmine
REDMINE_API_KEY=<redacted>
COLLECTOR_INITIAL_LOOKBACK_DAYS=3650

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NARRATIVE=qwen2.5-coder:14b
OLLAMA_MODEL_HEAVY=qwen3.6:35b-a3b
```

### 2.3 DB 인스턴스
- **PostgreSQL 18** — 5432 (다른 프로젝트용, 보존)
- **PostgreSQL 17** — 5433 (TaskView 전용), data dir `/opt/homebrew/var/flowlens-pg17`
- **TimescaleDB 2.26.4**, `shared_preload_libraries='timescaledb'`
- **시작 명령:** `/opt/homebrew/opt/postgresql@17/bin/pg_ctl -D /opt/homebrew/var/flowlens-pg17 -l /opt/homebrew/var/flowlens-pg17/server.log start`

### 2.4 Ollama 사용 가능 모델
```
qwen2.5-coder:14b           (8.99 GB)  ← Narrator 기본
qwen3.6:35b-a3b             (23.94 GB) ← 처방 레이어 후보
qwen3.6:35b-a3b-coding-nvfp4 (21.91 GB)
```

---

## 3. 현재 데이터 현황 (재수집 불필요, 그대로 활용)

| Table | Rows | 패치 0 후 신규명 |
|---|---|---|
| raw_issues | 16,092 | raw_redmine_issues |
| raw_journals | 97,302 | raw_redmine_journals |
| raw_time_entries | 20 | raw_redmine_time_entries |
| raw_users | 77 | raw_redmine_users |
| raw_projects | 6 | raw_redmine_projects |
| raw_versions | 0 | raw_redmine_versions |
| fct_state_transition | 45,259 | (변경 없음) |
| fct_issue_flow | 16,092 | (변경 없음) |
| fct_wip_daily | 31,161 | (변경 없음) |
| fct_throughput_weekly | 574 | (변경 없음) |
| dim_project / dim_user | 6 / 88 | (변경 없음) |

**raw 테이블 rename은 PostgreSQL `ALTER TABLE RENAME` 명령으로 데이터 무손실 즉시 실행.** 다운타임 약 2~3분.

### 3.1 프로젝트 분포 (open / total)
- 29 [만나 플랫폼] — 493 / 15,778
- 35 [연구 과제] — 65 / 81
- 34 [조직 운영] — 24 / 168
- 36 [픽오더] — 15 / 54
- 38 [AI_BUSINESS] — 0 / 1
- 37 [AI_DB] — 0 / 10

### 3.2 Status Group 매핑 (`backend/app/analytics/status_groups.py`)
패치 0 옵션 A 채택으로 hardcoded 유지. 매핑 UI에서 사용자가 변경해도 표시만 됨(실제 분석 적용은 v1.5에서).
```
backlog:     1 (신규 등록)
in_progress: 2 (업무 진행), 12 (검토 진행)
review:      3, 4, 14, 17, 18, 19, 20, 24
rework:      8, 21, 22
blocked:     9 (보류), 16 (일시 정지)
done:        5, 10, 11, 13, 23, 25       ← is_closed=true
rejected:    6 (반려)                    ← is_closed=true
```

### 3.3 주요 분석 결과 (project_id=29, 6개월 윈도)
- 평균 lead time: 86일, cycle 56일, queue 13일, review_wait 22일 (lead의 25% — 최대 병목)
- Open 493건 분포: backlog 321, in_progress 85, review 53, blocked 30, rework 4
- Bottleneck score (top 3): backlog 122.29 / in_progress 58.12 / blocked 54.33
- Top risk issues: #10729, #8745 (score 70, blocked, overdue 1,300+일)
- Forecast (Monte Carlo): P50 21w (2026-10-02), P85 24w, P95 26w
- Team Gini: 0.6266 (top 3명이 WIP 34% 점유)
- Anomaly cycle p95 ~8,500h, queue p95 ~963h. 미종료 severe: #16562 (queue 1,707h)
- Critical path: precedes(2)+blocks(0)=2건 → not_applicable

---

## 4. 현재 구현 완료된 백엔드 자산

### 4.1 분석 모듈 시그니처 (`backend/app/analytics/`)
```python
# status_groups.py
group_of(status_id), is_closed(status_id), is_active_work(status_id), name_of(status_id)

# bottleneck.py
detect_bottlenecks(project_id) -> List[Dict]
top_bottleneck_groups(limit, project_id)

# risk.py
top_risky_issues(limit, project_id, min_score) -> List[Dict]
project_risk_summary(project_id) -> Dict

# forecast.py
monte_carlo_forecast(project_id, remaining=None,
                     simulations=2000, lookback_weeks=26) -> Dict

# resource.py
team_load(project_id, recent_weeks=4) -> Dict

# anomaly.py
detect_anomalies(metric="cycle"|"queue", project_id, since_months,
                 limit) -> List[Dict]

# critical_path.py
critical_path(project_id) -> Dict

# summary.py
project_summary(project_id, since_months) -> Dict
```

### 4.2 FastAPI 엔드포인트 (전부 200 검증 완료, 패치 후에도 모두 유지)

| Method | Path | 비고 |
|---|---|---|
| GET | /healthz | meta |
| GET | /v1/meta/projects | dim_project + raw_issues 카운트 |
| GET | /v1/executive/summary | summary.project_summary() |
| GET | /v1/executive/risk | summary + top |
| GET | /v1/manager/bottlenecks | top 옵션 / 전체 |
| GET | /v1/manager/team | limit, recent_weeks, include_all |
| GET | /v1/team/forecast | remaining, simulations, lookback_weeks |
| GET | /v1/insight/anomalies | metric=cycle/queue |
| GET | /v1/insight/critical-path | edge<20 시 not_applicable |

CORS: `allow_origins=["*"]` (개발용)

### 4.3 현재 프론트 페이지 (패치 4까지 공존, 이후 redirect)
| Path | 내용 |
|---|---|
| `/` | → /executive/overview redirect |
| `/executive/overview` | KPI 6+4장, Bottleneck/TeamLoad 차트, Top risky 5, Anomaly |
| `/executive` | risk 중심 — KPI 4 + risk top 10 |
| `/manager` | KPI 5 + Bottleneck Bar + TeamLoad Bar |
| `/team` | Forecast P50/P85/P95 카드 + ETA 타임라인 |
| `/insight` | Anomaly 테이블 + Critical path 카드 |

### 4.4 진행 단계 체크리스트
| STEP | 내용 | 상태 |
|---|---|---|
| 1 | DB / Alembic / Timescale | ✅ |
| 2 | Collector + Journal enrichment | ✅ |
| 3 | ETL (raw → mart) | ✅ |
| 4-Analytics | 분석 모듈 6+1개 | ✅ |
| 4-API | FastAPI 9 엔드포인트 | ✅ |
| 5 | Next.js 5페이지 + 다크모드 | ✅ |
| **재설계** | **이하 모두 진행 중** | |
| **🆕 패치 0** | **Connector 추상화 + 연동 UI** | 🔜 |
| 패치 1 | 디자인 토큰 + 한국어 라벨 + 사이드바 + 홈 | 🔜 |
| 패치 2 | Dashboard + 시간 분포 + 주간보고 1차 | 🔜 |
| 패치 3 | Flow + 이슈 타임라인 자동 설명(1순위) | 🔜 |
| 패치 4 | Meeting + dim_user 확장 + 가정 시뮬레이션 | 🔜 |
| 패치 5 | Settings + 팀즈 알림 + 학습 모드 + 월간보고 | 🔜 |
| 운영화 | Docker Compose / launchd / Caddy / Tailscale | 보류 |

---

## 5. 경쟁 서비스 분석 (8종)

웹 리서치(G2/Gartner 리뷰, Reddit ExperiencedDevs 스레드 82+ 댓글, 10x.pub 비교 글, 공식 문서) 기반 1차 자료 종합.

### 5.1 Jellyfish
- **강점:** 비즈니스 번역(Resource Allocations로 신기능/유지보수/기술부채 자동 분류). 임원 보고 특화. G2 98%가 4~5점.
- **약점:** "가격 천문학적, 결국 예쁜 DORA 메트릭"(r/devops). 30일 파일럿 후 정착 6개월. **셸프웨어 위험 1위.**
- **TaskView가 가져올 것:** Resource Allocations 데이터 모델 → "이번 분기 시간 분포" 카드.
- **TaskView가 피할 것:** 데이터만 보여주고 액션 없는 함정.

### 5.2 LinearB
- **강점:** 워크플로우 자동화(gitStream YAML, WorkerB 슬랙 알림). 8.1M PR 벤치마크.
- **약점:** AI 기여 측정 약함. 비-개발 부서 적용 거의 불가능.
- **TaskView가 가져올 것:** WorkerB식 알림 UX(팀즈 우선). 라우팅 규칙 진단으로 우회 차별화.
- **TaskView가 피할 것:** 개발자에만 집중.

### 5.3 Allstacks
- **강점:** Monte Carlo 일정 예측 카테고리 1위. Goals + Risks 임계치 룰.
- **TaskView가 가져올 것:** Goals + Risk Alerts UX → Settings의 알림 규칙 노코드 빌더.

### 5.4 Logilica
- **강점:** 자연어 질의 인터페이스(AI Advisor).
- **TaskView가 가져올 것:** **한국어 우선** 자연어 질의. 영어로는 Logilica가 잘 하지만 **한국어로는 누구도 안 함**.

### 5.5 DX (GetDX)
- **강점:** DORA/SPACE/DevEx 창시자. DX Core 4 프레임워크. 설문 + 텔레메트리 결합.
- **TaskView가 가져올 것:** **DX Core 4 프레임워크 그대로 인용** (Speed/Effectiveness/Quality/Business Impact 4축).
- **TaskView가 피할 것:** 무거운 설문 운영 → 분기 1회 짧은 펄스(5문항)만.

### 5.6 Swarmia
- **강점:** Working Agreements 시그니처. 깔끔한 UI.
- **약점:** **Reddit 60+ 추천 결정적 비판:** "엔지니어 행복 약속은 거짓, 실제로는 관리자가 팀 비교/순위 매기기에 사용."
- **TaskView가 가져올 것:** Working Agreements 철학과 UX. **단, 악의적 사용을 시스템 차원에서 강제 차단:**
  - 개인별 비교 화면을 코드 레벨에서 부재
  - 면담 자료 본인 열람 기본 제공
  - 팀 약속 위반 알림 수신자 = 팀 전체

### 5.7 Pluralsight Flow (구 GitPrime)
- **약점:** **카테고리 최대의 실패 사례.** Impact Score로 개인 줄 세우기, 감시 도구 인식.
- **TaskView가 피할 것:** **단일 점수로 사람 줄 세우는 모든 메커니즘.**

### 5.8 Code Climate Velocity
- **강점:** 코드 품질 분석 통합. Productive Impact(Impact - Rework).
- **약점:** "데이터 받지만 무엇을 해야 할지 모름."
- **TaskView가 피할 것:** 액션 없는 데이터.

---

## 6. 사용자가 진짜로 원하는 것 (Reddit/리뷰 1차 자료 도출 7가지)

| # | 사용자 요청 | TaskView 적용 |
|---|---|---|
| 1 | 메트릭이 아니라 트렌드 | 모든 KPI 카드에 추이 + 전기간 차이 + 주간 변동성 강제 표시 |
| 2 | 개인이 아니라 팀 단위로만 | "개인 데이터 노출 모드" 스위치(기본 OFF). 켜도 D 화면에서만 |
| 3 | Goodhart 법칙을 막아달라 | **절대 임계치 부재, 상대 기준만 사용** |
| 4 | WIP 상태의 진짜 의미 | "검수자에게 넘어간 후 X일"로 측정 |
| 5 | 이슈가 오래 걸린 이유 자동 설명 | **차별점 5(1순위).** 이슈 상세 타임라인 + LLM 한 줄 요약 |
| 6 | 관리자가 정신차리고 쓰게 | "오늘 살펴볼 사항" 무시 시 다음 주 재출현. fct_action_log 기록 |
| 7 | 셸프웨어 방지 | **학습 모드 4주** — 도입 후 4주간 알림만, 액션 강제 없음 |

---

## 7. 디자인 원칙 7가지 (UI 헌법)

1. **한 화면, 한 질문.** 페이지마다 답해야 할 질문 하나.
2. **숫자보다 문장.** 모든 KPI는 [숫자] + [추이 화살표] + [한 줄 해석] 3단 구조.
3. **색은 의미만.** 빨강(즉시 조치) / 주황(주시) / 회색(정상) / 초록(개선됨) 4가지만.
4. **카드 중심, 표 최소화.** 표는 D 화면(면담)과 C 화면 상세에서만.
5. **사이드바 폭 축소(72px), 상단 컨텍스트 바 도입.**
6. **한국어 보고서 톤 통일.** 보고서체 단문(~함). 권장 조치만 권유형(~을 권장합니다).
7. **라이트 모드 1급, 다크는 보조.**

---

## 8. 한국어 용어 사전 (확정)

### 8.1 영문 유지 (사용자 결정)
Dashboard, Overview, Executive, Manager, Team, Filter

### 8.2 한국어 변환 (사용자 결정)
| 영문 | 한국어 |
|---|---|
| Risk Score | 위험점수 |
| Insight | 심층분석 |

### 8.3 한국어 변환 (제안 그대로 채택)
| 영문 | 한국어 |
|---|---|
| Bottleneck | 정체 구간 |
| Cycle Time | 처리 기간 |
| Lead Time | 전체 소요일 |
| Queue Time | 대기 기간 |
| Review Wait | 검수 대기 |
| WIP | 진행 중 업무 (약어 노출 금지) |
| Throughput | 주간 완료량 |
| Forecast | 완료 예측 |
| Risk | 지연 위험 |
| Anomaly | 이상 신호 |
| Critical Path | 핵심 경로 |
| Gini | 쏠림 지수 |
| P50 / P85 / P95 | 보통 / 보수적 / 안전 (괄호 병기) |
| Backlog | 대기 중 |
| In Progress | 진행 중 |
| Review | 검수 중 |
| Rework | 재작업 |
| Blocked | 보류됨 |
| Done | 완료 |
| Rejected | 반려 |
| Narrator | 자동 분석 메모 |
| Action | 권장 조치 |
| Working Agreement | 팀 약속 |
| Meeting Brief | 면담 준비 자료 |
| Fairness | 업무 분배 균형 |
| User | 구성원 |
| Assignee | 담당자 |
| Owner | 책임자 |
| **Connector** | **연동** |
| **Connector Instance** | **연동 항목** |
| **Resource** | **데이터 종류** |
| **Status Mapping** | **상태 매핑** |
| **Sync** | **동기화** |

### 8.4 표현 규칙
- "직원/사원" 금지 → "구성원"
- "h/d/w" 약어 노출 금지 → "시간/일/주"
- 날짜: "2026년 5월 9일(토)" 형식
- "약점/문제점/부진" 단어 면담 화면에서 절대 사용 금지 → "함께 살펴볼 영역"

---

## 9. 디자인 토큰

```css
/* 폰트 */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');

--font-sans: 'Pretendard Variable', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* 색상 */
--color-bg:           #FAFAFA;
--color-surface:      #FFFFFF;
--color-border:       #E5E7EB;
--color-text:         #111827;
--color-text-muted:   #6B7280;
--color-text-subtle:  #9CA3AF;

--color-critical:     #DC2626;
--color-warning:      #F59E0B;
--color-normal:       #6B7280;
--color-good:         #059669;

--color-accent:       #2563EB;

/* 타이포 */
헤더 1: 24px / 700 / -0.02em
헤더 2: 18px / 600 / -0.01em
본문:   14px / 400 / 1.6
보조:   13px / 400 / 1.5
라벨:   12px / 500 / 1.4 (uppercase 금지)

/* 간격 (8px 그리드) */
카드 패딩: 24px
카드 간격: 16px
섹션 간격: 32px

/* 모서리 */
카드: 12px
버튼: 8px
태그: 6px

/* 그림자 */
카드: 0 1px 2px rgba(0,0,0,0.04)
팝오버: 0 8px 24px rgba(0,0,0,0.08)
```

---

## 10. 화면 IA (Information Architecture)

### 10.1 사이드바 메뉴 (5 + Settings, 폭 72px)
```
🏠 Home
📊 Dashboard
🔀 Flow
💬 Meeting
📋 Reports
─────────
⚙️ Settings
   ├── 연동 (Connectors)        ← 🆕 패치 0
   ├── 팀 약속                   ← 패치 5
   ├── 역할 매핑                 ← 패치 4
   ├── 알림 규칙                 ← 패치 5
   ├── 개인 데이터 노출 모드     ← 패치 5
   └── 학습 모드                 ← 패치 5
```

### 10.2 글로벌 레이아웃
```
┌─────────────────────────────────────────────────────────────────────┐
│ TaskView                                          🔔  🌗  김 ▾      │
├─────────────────────────────────────────────────────────────────────┤
│ 📁 만나 플랫폼 ▾   📅 최근 6개월 ▾   👥 전체 팀 ▾                    │
├──────┬──────────────────────────────────────────────────────────────┤
│ 🏠   │                                                              │
│ 📊   │                                                              │
│ 🔀   │                  본문 영역                                    │
│ 💬   │                                                              │
│ 📋   │                                                              │
│ ──   │                                                              │
│ ⚙️   │                                                              │
└──────┴──────────────────────────────────────────────────────────────┘
  72px                          나머지
```

### 10.3 페이지 구조
- `/` — 홈
- `/dashboard` — DX Core 4 4섹션
- `/flow` — 흐름 진단
- `/meeting/[userId]` — 면담 준비 자료
- `/reports` — 한국형 보고서
- `/settings` — 설정 허브
- `/settings/connectors` — 🆕 연동 관리 목록
- `/settings/connectors/new` — 🆕 새 연동 마법사
- `/settings/connectors/[id]` — 🆕 연동 상세/수정

### 10.4 기존 페이지 단계적 폐기
- 패치 0~3: 그대로 살림. 상단에 안내 배너만.
- 패치 4 완료: redirect로 전환.
- 패치 5 + 1개월 안정화 후: 페이지 파일 삭제.

---

## 11. 화면별 와이어프레임

### 11.1 🆕 패치 0 — 연동 관리 화면 1: 연동 목록
```
┌─ 연동 관리 ─────────────────────────────────────────────────────────┐
│                                          [+ 새 연동 추가]            │
│                                                                      │
│ ✅ 사내 Redmine                              마지막 동기화: 5분 전    │
│    redmine.mannaplanet.co.kr                정상 / 6개 데이터 활성   │
│    [상세 설정] [지금 동기화] [비활성화]                              │
│                                                                      │
│ (다른 연동 없음)                                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.2 🆕 패치 0 — 화면 2: 새 연동 추가 (도구 선택)
```
┌─ 어떤 도구를 연동하시겠습니까? ─────────────────────────────────────┐
│                                                                      │
│  [업무관리 도구] [메시징] [코드 저장소]   ← 3개 카테고리 탭          │
│                                                                      │
│  ── 업무관리 도구 ──                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Redmine  │  │   Jira   │  │  Asana   │  │ ClickUp  │            │
│  │   ✅     │  │  곧 지원 │  │  곧 지원 │  │  곧 지원 │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │ Notion   │  │Monday.com│  │  Trello  │                          │
│  │  곧 지원 │  │  곧 지원 │  │  곧 지원 │                          │
│  └──────────┘  └──────────┘  └──────────┘                          │
│                                                                      │
│  ── 코드 저장소 ──                                                   │
│  ┌──────────┐  ┌──────────┐                                        │
│  │  GitHub  │  │  GitLab  │                                        │
│  │  곧 지원 │  │  곧 지원 │                                        │
│  └──────────┘  └──────────┘                                        │
│                                                                      │
│  ── 메시징 ──                                                        │
│  (현재 지원 예정 항목 없음 — 향후 Slack, 팀즈, 잔디, 카카오워크 추가)│
└──────────────────────────────────────────────────────────────────────┘
```

### 11.3 🆕 패치 0 — 화면 3: Redmine 연결 정보 입력
```
┌─ Redmine 연결 정보 ────────────────────────────────────────────────┐
│ 연동 이름: [사내 Redmine                              ]              │
│ Redmine URL: [http://redmine.mannaplanet.co.kr:5555/  ]              │
│ API 키: [••••••••••••••••••••              ] [발급 방법 보기]        │
│                                                                      │
│ 초기 수집 기간: [최근 1년 ▾] (3년/5년/10년/전체)                     │
│                                                                      │
│                              [연결 테스트]   [취소] [다음]           │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.4 🆕 패치 0 — 화면 4: 데이터 종류 선택
```
┌─ 가져올 데이터 선택 ────────────────────────────────────────────────┐
│ 다음 데이터를 자동으로 수집합니다. 필요한 항목만 선택하세요.          │
│                                                                      │
│ ✅ 프로젝트         (6개 발견, 필수)                                 │
│ ✅ 구성원           (77명 발견, 필수)                                │
│ ✅ 이슈             (약 16,000건, 1시간마다 동기화)                  │
│ ✅ 변경 이력(저널)  (약 97,000건, 분석 정확도에 중요)                │
│ ☐ 시간 기록        (약 20건, 데이터 부족)                           │
│ ☐ 버전/마일스톤    (0건, 미사용)                                    │
│                                                                      │
│                                            [이전] [다음]             │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.5 🆕 패치 0 — 화면 5: 상태 매핑 (옵션 A — 표시만)
```
┌─ 이슈 상태 매핑 ────────────────────────────────────────────────────┐
│ Redmine의 상태를 TaskView 분석 카테고리에 연결합니다.                 │
│ TaskView가 추천 매핑을 제안했습니다.                                  │
│                                                                      │
│ ⚠️ 1차 버전에서는 매핑 변경 사항이 표시만 되며,                       │
│    실제 분석 적용은 다음 업데이트(v1.5)에서 지원됩니다.              │
│                                                                      │
│ Redmine 상태               →  TaskView 카테고리                      │
│ ─────────────────────────────────────────────                        │
│ 신규 등록                  →  [대기 중      ▾]                       │
│ 업무 진행                  →  [진행 중      ▾]                       │
│ 검토 진행                  →  [진행 중      ▾]                       │
│ 검수 요청                  →  [검수 중      ▾]                       │
│ 검수 진행                  →  [검수 중      ▾]                       │
│ 보류                       →  [보류됨      ▾]                       │
│ 일시 정지                  →  [보류됨      ▾]                       │
│ 재작업                     →  [재작업      ▾]                       │
│ 완료                       →  [완료        ▾] ☑ 종료 상태           │
│ 반려                       →  [반려        ▾] ☑ 종료 상태           │
│ ...                                                                  │
│                                          [이전] [완료]               │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.6 🆕 패치 0 — 화면 6: 동기화 진행
```
┌─ 동기화 진행 중 ────────────────────────────────────────────────────┐
│                                                                      │
│ ⏳ 사내 Redmine 초기 수집 중...                                      │
│                                                                      │
│ ✅ 프로젝트 수집 완료      (6 / 6)                                   │
│ ✅ 구성원 수집 완료        (77 / 77)                                 │
│ 🔄 이슈 수집 중...         (8,234 / 약 16,000)  진행률 51%           │
│ ⏸ 변경 이력 수집 대기                                                │
│                                                                      │
│ 예상 남은 시간: 약 12분                                               │
│                                                                      │
│  💡 백그라운드에서 계속 진행됩니다. 다른 화면으로 이동해도 됩니다.    │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.7 홈 — "오늘 결정해야 할 것" (패치 1)
```
┌──────────────────────────────────────────────────────────────────────┐
│ 안녕하세요, 김이슬 팀장님. 2026년 5월 9일 토요일입니다.                │
│ 만나 플랫폼 프로젝트의 이번 주 핵심 사항을 TaskView가 정리했습니다.    │
└──────────────────────────────────────────────────────────────────────┘

┌─ 오늘 살펴볼 사항 3가지 ────────────────────────────────────────────┐
│  ┌────────────────────┐ ┌────────────────────┐ ┌──────────────────┐│
│  │ 🔴 즉시 조치       │ │ 🟠 이번 주 점검    │ │ 🟢 개선됨        ││
│  │ 검수 단계 정체     │ │ 원배문 님 업무집중 │ │ 평균 처리기간 4일││
│  │ 22일 대기 12건     │ │ 진행 중 61건      │ │ 단축됨 90→86일   ││
│  │ → 권장 조치 보기   │ │ → 1:1 면담 준비   │ │                  ││
│  └────────────────────┘ └────────────────────┘ └──────────────────┘│
└──────────────────────────────────────────────────────────────────────┘

┌─ 자동 분석 메모 ────────────────────────────────────────────────────┐
│ 📝 2026년 5월 9일 자동 생성                                          │
│ [관찰] 평균 처리 기간 86일 중 검수 대기 22일(25%)                    │
│ [해석] 검수자 3명 중 2명 다른 프로젝트 분산                          │
│ [권장] ① 검수자 풀 재구성 1:1  ② 라우팅 규칙 점검  ③ 2주 후 재측정 │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.8 Dashboard — DX Core 4 4섹션 (패치 2)
```
┌─ Speed (속도) ──────────────────────────────────────────────────────┐
│  평균 처리기간 86일 ↓4   주간 완료량 22건 ↑3   완료 예측 21주(보통)  │
└──────────────────────────────────────────────────────────────────────┘

┌─ Effectiveness (효율) ──────────────────────────────────────────────┐
│  업무 분배 균형 0.63(높음)  진행 중 업무 493건  미할당 18건           │
│  상위 3명이 진행 업무 34% 담당. 검수자 그룹 쏠림 가장 심함.           │
└──────────────────────────────────────────────────────────────────────┘

┌─ Quality (품질) ────────────────────────────────────────────────────┐
│  재작업 비율 8%   반려율 2%   이상 신호 12건                          │
└──────────────────────────────────────────────────────────────────────┘

┌─ Business Impact (비즈니스 가치) ───────────────────────────────────┐
│  이번 분기 시간 분포                                                  │
│  ███████ 신규 개발 45%                                                │
│  █████ 기능 개선 28%                                                  │
│  ███ 결함 수정 17%                                                    │
│  ██ 운영 대응 10%                                                     │
└──────────────────────────────────────────────────────────────────────┘

┌─ 가정 시뮬레이션 ───────────────────────────────────────────────────┐
│ • 검수자 1명 추가 → 검수 대기 22일 → 11일 (예상)                     │
│ • 원배문 님 WIP 절반 위임 → 평균 처리 86일 → 73일 (예상)             │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.9 Flow — "어디서 막히는가" (패치 3)
```
┌─ 흐름 진단 ─────────────────────────────────────────────────────────┐
│  대기 중 → 진행 중 → 검수 중 → 완료                                  │
│  321건     85건      53건      38건/주                               │
│  평균 8일  평균 14일  평균 22일 ← 가장 오래 머무는 단계               │
└──────────────────────────────────────────────────────────────────────┘
[이슈 클릭 시 → 이슈 타임라인 자동 설명 모달]
```

### 11.10 이슈 타임라인 자동 설명 (1순위 차별화, 패치 3)
```
┌─ 이슈 #10729 — "결제 모듈 검수 대기" ───────────────────────────────┐
│                                                                      │
│ 📅 타임라인                                                          │
│ 2024-12-15  생성 (담당자: 원배문)                                    │
│ 2024-12-20  진행 중 전환                                              │
│ 2025-01-10  PR 등록, 검수 요청                                        │
│ 2025-01-15  검수자(현복최) 배정                                       │
│ 2025-01-15 ~ 현재  검수 대기 (1,300+ 일)                             │
│                                                                      │
│ 🤖 TaskView 분석                                                     │
│ "이 일감은 외부 검수자 대기로 1,300일 이상 정체되었습니다.            │
│  검수자가 다른 프로젝트에 배정되어 있어 응답이 없는 상태입니다.       │
│  검수자 재배정 또는 일감 종료 결정이 필요합니다."                     │
│                                                                      │
│ → 권장 조치: [검수자 재배정] [일감 종료] [본인 확인 요청]            │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.11 Meeting — "이 사람과 무슨 대화" (패치 4)
```
┌─────────────────────────────────────────────────────────────────────┐
│  💬 면담 준비 자료                                                   │
│  ⚠️ 1:1 대화를 돕기 위한 참고 자료입니다.                             │
│     평가/연봉 결정의 단일 근거로 사용하지 마십시오.                   │
│     본인도 동일한 자료를 열람할 수 있습니다.                          │
└─────────────────────────────────────────────────────────────────────┘

대상: 원배문 (개발자, 시니어)
조회 기간: 2026년 2월 9일 ~ 5월 9일
생성 시각: 2026년 5월 9일 14:30 (이 시점 데이터로 동결)

┌─ 강점 패턴 ─────────────────────────────────────────────────────────┐
│ • 백엔드 영역 처리 기간 역할 평균보다 32% 빠름                        │
│ • 검수 반려율 3% (역할 평균 8% 대비 낮음)                            │
└──────────────────────────────────────────────────────────────────────┘

┌─ 함께 살펴볼 영역 ──────────────────────────────────────────────────┐
│ • 진행 중 61건(역할 평균 18건의 3.4배)                               │
│ • 최근 4주 완료량 직전 4주 대비 28% 감소                             │
└──────────────────────────────────────────────────────────────────────┘

┌─ 대화 주제 제안 ────────────────────────────────────────────────────┐
│ 1. 위임 가능한 업무가 있는지                                          │
│ 2. 검수자 대기 정체에 대한 느낌                                       │
└──────────────────────────────────────────────────────────────────────┘

[자료 동결 저장] [PDF 내보내기] [본인에게 공유]
```

---

## 12. 데이터베이스 변경

### 12.1 기존 테이블 (전부 유지)
패치 0에서 raw_* 6개 테이블만 `raw_redmine_*`로 rename. 데이터 무손실.

### 12.2 🆕 패치 0 신규 테이블 (alembic 0003)
```sql
-- 연동 항목 (도구 인스턴스)
CREATE TABLE connector_instance (
    id SERIAL PRIMARY KEY,
    connector_type VARCHAR(50) NOT NULL,        -- "redmine"|"jira"|"asana"|...
    instance_name VARCHAR(200) NOT NULL,        -- "사내 Redmine"
    config JSONB NOT NULL,                      -- URL, API key 등
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 리소스(데이터 종류)별 수집 설정
CREATE TABLE connector_resource (
    id SERIAL PRIMARY KEY,
    connector_instance_id INTEGER REFERENCES connector_instance(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,         -- "issues"|"journals"|"users"|...
    is_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 60,
    last_synced_at TIMESTAMPTZ,
    last_sync_status VARCHAR(20),               -- "success"|"failed"|"running"
    last_sync_error TEXT,
    extra_config JSONB
);

-- 상태 매핑 (옵션 A: 1차에서는 표시만, 분석 미반영)
CREATE TABLE connector_status_mapping (
    id SERIAL PRIMARY KEY,
    connector_instance_id INTEGER REFERENCES connector_instance(id) ON DELETE CASCADE,
    source_status VARCHAR(200) NOT NULL,        -- Redmine: "1", Jira: "To Do"
    source_status_label VARCHAR(200),           -- 표시용 라벨
    canonical_status_group VARCHAR(50) NOT NULL,-- backlog|in_progress|review|...
    is_closed BOOLEAN DEFAULT FALSE
);

-- 동기화 작업 이력 (진행 표시 + 에러 추적)
CREATE TABLE connector_sync_job (
    id SERIAL PRIMARY KEY,
    connector_instance_id INTEGER REFERENCES connector_instance(id),
    resource_type VARCHAR(50),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(20),                         -- "running"|"success"|"failed"
    records_fetched INTEGER DEFAULT 0,
    records_total INTEGER,
    error_message TEXT
);
```

### 12.3 raw 테이블 rename (alembic 0003 동일 마이그레이션)
```sql
ALTER TABLE raw_issues       RENAME TO raw_redmine_issues;
ALTER TABLE raw_journals     RENAME TO raw_redmine_journals;
ALTER TABLE raw_time_entries RENAME TO raw_redmine_time_entries;
ALTER TABLE raw_users        RENAME TO raw_redmine_users;
ALTER TABLE raw_projects     RENAME TO raw_redmine_projects;
ALTER TABLE raw_versions     RENAME TO raw_redmine_versions;
```

### 12.4 데이터 시드 (마이그레이션 후 자동 실행)
```python
# alembic upgrade의 데이터 마이그레이션 단계
# 1) 기본 connector_instance 1건 INSERT (.env의 REDMINE_* 값 복사)
# 2) connector_resource 6건 INSERT (issues, journals, users, projects, versions, time_entries)
# 3) connector_status_mapping INSERT (status_groups.py의 hardcoded 매핑 11건)
```

### 12.5 dim_user 컬럼 추가 (alembic 0004, 패치 4)
```sql
ALTER TABLE dim_user ADD COLUMN role VARCHAR(50);
ALTER TABLE dim_user ADD COLUMN function_group VARCHAR(50);
ALTER TABLE dim_user ADD COLUMN seniority VARCHAR(20);
ALTER TABLE dim_user ADD COLUMN manager_id INTEGER;
ALTER TABLE dim_user ADD COLUMN employment_type VARCHAR(20);
ALTER TABLE dim_user ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
```

### 12.6 신규 테이블 (alembic 0005~0009, 패치 4~5)
- `dim_role_baseline` (패치 4)
- `fct_meeting_prep` (패치 4)
- `fct_working_agreement` (패치 5)
- `fct_action_log` (패치 5)
- `fct_action_rule` (패치 5)

---

## 13. 백엔드 모듈 확장

### 13.1 🆕 패치 0 — Connector 모듈
```python
# backend/app/connectors/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterator
from dataclasses import dataclass

@dataclass
class ConnectionTestResult:
    success: bool
    message: str
    metadata: dict  # {"version": "...", "user_count": 77, ...}

@dataclass
class ResourceCatalog:
    resources: list  # [{"type": "issues", "label": "이슈",
                     #   "estimated_count": 16000, "required": False, "recommended": True}, ...]

@dataclass
class CanonicalRecord:
    record_type: str  # "issue"|"user"|"project"|"transition"|...
    external_id: str  # 도구 내 ID
    payload: dict     # canonical 필드들

class BaseConnector(ABC):
    connector_type: str
    display_name: str
    category: str  # "task_management"|"messaging"|"code_repo"
    status: str    # "active"|"coming_soon"
    config_schema: dict  # JSON Schema for connection form

    @abstractmethod
    def test_connection(self, config: dict) -> ConnectionTestResult: ...

    @abstractmethod
    def discover_resources(self, config: dict) -> ResourceCatalog: ...

    @abstractmethod
    def fetch_resource(self, resource_id: str, config: dict, since: datetime) -> Iterator[dict]: ...

    @abstractmethod
    def to_canonical(self, raw_record: dict, resource_id: str) -> CanonicalRecord: ...

    @abstractmethod
    def get_status_mapping_template(self, config: dict) -> dict: ...
```

### 13.2 🆕 패치 0 — Connector 등록
```python
# backend/app/connectors/registry.py
from .redmine.connector import RedmineConnector
from .jira.connector import JiraConnector
# ... 8개 도구 import

CONNECTORS = {
    "redmine":  RedmineConnector,
    "jira":     JiraConnector,
    "asana":    AsanaConnector,
    "clickup":  ClickUpConnector,
    "notion":   NotionConnector,
    "monday":   MondayConnector,
    "trello":   TrelloConnector,
    "github":   GitHubConnector,
    "gitlab":   GitLabConnector,
}

def get_connector(connector_type: str) -> BaseConnector:
    return CONNECTORS[connector_type]()

def list_available_connectors() -> list:
    return [
        {"type": k, "display_name": v.display_name,
         "category": v.category, "status": v.status}
        for k, v in CONNECTORS.items()
    ]
```

### 13.3 🆕 패치 0 — Redmine 어댑터 (기존 코드 90% 재활용)
```python
# backend/app/connectors/redmine/connector.py
class RedmineConnector(BaseConnector):
    connector_type = "redmine"
    display_name = "Redmine"
    category = "task_management"
    status = "active"
    config_schema = {
        "type": "object",
        "required": ["base_url", "api_key"],
        "properties": {
            "base_url": {"type": "string", "format": "uri"},
            "api_key": {"type": "string", "format": "password"},
            "initial_lookback_days": {"type": "integer", "default": 365}
        }
    }

    def test_connection(self, config):
        # 기존 redmine_client.py의 GET /users/current 재활용
        ...

    def discover_resources(self, config):
        return ResourceCatalog(resources=[
            {"type": "projects", "label": "프로젝트", "required": True, ...},
            {"type": "users", "label": "구성원", "required": True, ...},
            {"type": "issues", "label": "이슈", "recommended": True, ...},
            {"type": "journals", "label": "변경 이력(저널)", "recommended": True, ...},
            {"type": "time_entries", "label": "시간 기록", ...},
            {"type": "versions", "label": "버전/마일스톤", ...},
        ])
    # ... 나머지 메서드는 기존 sync_jobs.py 재활용
```

### 13.4 🆕 패치 0 — 다른 8개 어댑터 (껍데기)
```python
# backend/app/connectors/jira/connector.py
class JiraConnector(BaseConnector):
    connector_type = "jira"
    display_name = "Jira"
    category = "task_management"
    status = "coming_soon"
    config_schema = {}

    def test_connection(self, config):
        raise NotImplementedError("Jira 연동은 곧 지원 예정입니다.")
    # ... 나머지도 NotImplementedError
```
**Asana, ClickUp, Notion, Monday.com, Trello, GitHub, GitLab도 동일 패턴.**

### 13.5 도구별 카테고리 분류 (사용자 결정)
| 도구 | 카테고리 | 패치 0 상태 |
|---|---|---|
| Redmine | task_management | ✅ active |
| Jira | task_management | coming_soon |
| Asana | task_management | coming_soon |
| ClickUp | task_management | coming_soon |
| Notion | task_management | coming_soon |
| Monday.com | task_management | coming_soon |
| Trello | task_management | coming_soon |
| GitHub | code_repo | coming_soon |
| GitLab | code_repo | coming_soon |
| (메시징 카테고리) | messaging | (현재 없음, 향후 Slack/팀즈/잔디/카카오워크 추가) |

### 13.6 기존 분석 모듈 (전부 유지)
status_groups, bottleneck, risk, forecast, resource, anomaly, critical_path, summary 모두 그대로. 패치 0에서 raw 테이블명만 `raw_redmine_*`로 변경되므로 SQL 쿼리만 일괄 수정.

### 13.7 신규 모듈 (패치 1~5)
- `prescription.py`, `meeting_brief.py`, `weekly_report.py`, `monthly_report.py` (패치 2/4/5)
- `fairness.py`, `workload_health.py` (패치 4)
- `issue_explainer.py` — **차별점 5(1순위)** (패치 3)
- `time_allocation.py` (패치 2)

### 13.8 신규 API 엔드포인트
**🆕 패치 0 — Connector 8개:**
- `GET /v1/connectors/types` — 사용 가능한 도구 목록 (3개 카테고리)
- `GET /v1/connectors/instances` — 등록된 연동 목록
- `POST /v1/connectors/instances` — 새 연동 생성
- `POST /v1/connectors/test` — 연결 테스트 (저장 전)
- `GET /v1/connectors/{id}/resources` — 리소스 카탈로그
- `PUT /v1/connectors/{id}/resources` — 리소스 활성/비활성
- `GET /v1/connectors/{id}/status-mapping` — 현재 매핑
- `PUT /v1/connectors/{id}/status-mapping` — 매핑 수정 (옵션 A: DB만 저장, 분석 미반영)
- `POST /v1/connectors/{id}/sync` — 즉시 동기화 트리거
- `GET /v1/connectors/{id}/sync-jobs` — 동기화 진행/이력

**패치 1~5 (이전 v1과 동일):**
- `/v1/home/today` (1)
- `/v1/dashboard/summary`, `/time-allocation` (2)
- `/v1/reports/weekly` (2), `/monthly` (5)
- `/v1/flow/stages`, `/by-role`, `/v1/issue/{id}/explanation` (3)
- `/v1/dashboard/scenario`, `/v1/meeting/{user_id}/brief` (4)
- `/v1/notifications/teams/test` (5)

### 13.9 deprecated 처리
패치 5 완료 시점에 기존 8개(`/v1/executive/*`, `/v1/manager/*`, `/v1/team/*`, `/v1/insight/*`)를 deprecated 헤더 표시. 응답 자체는 최소 6개월 유지.

---

## 14. 윤리 가드레일 (시스템 차원 강제)

`docs/ETHICS_GUARDRAILS.md` 신규 문서로 명문화.

### 14.1 5대 강제 메커니즘
1. **개인 비교 화면 부재** — 코드 레벨에서 user 비교 화면 부재. `/v1/users/compare` 같은 엔드포인트 절대 금지.
2. **면담 자료 본인 열람 기본** — 관리자가 면담 자료 생성 시 본인에게 자동 접근권 부여. opt-out 불가.
3. **단일 점수 사람에게 부여 금지** — 분석 모듈 함수 시그니처에서 `user_id` 받는 함수는 점수 반환 금지.
4. **절대 임계치 부재, 상대 기준만** — "리드타임 X일 이내" 같은 절대 목표 금지.
5. **학습 모드 4주** — 도입 시 4주간 알림은 받되 액션 강제 없음.

### 14.2 알림 규칙 빌더 제약
Settings의 알림 규칙 빌더에서 `user_id` 조건은 선택 불가(UI 레벨).

### 14.3 팀 약속 위반 알림
수신자 = 팀 전체가 기본값.

---

## 15. 알림 통합 (팀즈 단독)

### 15.1 방식
**Microsoft Teams Incoming Webhook (방식 A)** 단독. Azure AD 앱 등록 불필요.

### 15.2 구현 위치
`backend/app/notifications/channels/teams.py` 신규. Adaptive Card 포맷.

### 15.3 메시지 포맷 예시
```
🔴 검수 대기 12건이 22일 누적되었습니다.
검수자 풀 점검을 권장합니다.
[상세 보기] [규칙 조정] [무시]
```
헤더 "TaskView" 표기. 봇 이름 "TaskView 알림".

---

## 16. Narrator (자동 분석 메모) 3-레이어 설계

- **레이어 1 — 관찰:** 한국어 보고서체 불릿 3~4줄. qwen2.5-coder:14b
- **레이어 2 — 해석:** 같은 모델, 더 긴 컨텍스트
- **레이어 3 — 처방:** prescription.py 룰 + LLM. 무거운 모델(qwen3.6:35b-a3b) 검토

자칭: "TaskView가 분석한 결과", "TaskView 분석 메모"

---

## 17. 패치 로드맵 (15~20주)

### 🆕 패치 0 — Connector 추상화 + 연동 관리 UI (1~4주차) ⭐ 필수
**범위:**

**백엔드 (3주):**
- `backend/app/connectors/base.py` — BaseConnector 추상 클래스 + 데이터 클래스
- `backend/app/connectors/redmine/connector.py` — 기존 redmine_client.py 리팩터링 (90% 재활용)
- `backend/app/connectors/{jira,asana,clickup,notion,monday,trello,github,gitlab}/connector.py` — 껍데기 8개 (NotImplementedError, status="coming_soon")
- `backend/app/connectors/registry.py` — 9개 어댑터 등록
- alembic 0003 — 4개 신규 테이블 + raw_* 6개 rename + 데이터 시드
- `app/api/routers/connectors.py` — 10개 엔드포인트
- 기존 collector/scheduler를 connector 인터페이스 통과하도록 수정
- 기존 분석 모듈 SQL 쿼리의 raw_* → raw_redmine_* 일괄 수정 (grep+sed)
- 동기화 진행 상황 추적 (connector_sync_job 테이블 기반)

**프론트엔드 (1.5주):**
- `app/settings/connectors/page.tsx` — 연동 목록
- `app/settings/connectors/new/page.tsx` — 4단계 마법사
- `app/settings/connectors/[id]/page.tsx` — 상세/수정
- `components/connectors/ConnectorCard.tsx` — 도구 선택 카드 (3카테고리 탭)
- `components/connectors/ConnectionForm.tsx` — config_schema 기반 동적 폼
- `components/connectors/ResourceSelector.tsx` — 데이터 종류 선택
- `components/connectors/StatusMappingTable.tsx` — 상태 매핑 표시(옵션 A)
- `components/connectors/SyncProgress.tsx` — 동기화 진행

**마이그레이션 (0.5주):**
1. 빈 connector_instance 생성 (id=1, "사내 Redmine", .env 복사)
2. raw_* → raw_redmine_* rename (다운타임 2~3분)
3. status_groups.py hardcoded 매핑을 connector_status_mapping에 INSERT
4. ETL 코드의 테이블명 참조 업데이트
5. 검증: 16,092건 보존 확인

**불변:** 분석 모듈 로직 변경 없음 (status_groups.py 내부 hardcoded 유지, 옵션 A). 기존 9개 API 엔드포인트 모두 살아있음. 기존 5개 페이지 살아있음.

**가시화:** Settings → 연동 메뉴에서 "TaskView가 9개 도구를 지원할 수 있는 플랫폼"임이 시각적으로 선언됨. 실제로는 Redmine만 동작해도 시장 메시지가 강력해짐.

### 패치 1 — 기반 재정비 (5~6주차)
**범위:**
- 디자인 토큰 (Pretendard CDN, 의미 색상 4종, 8px 그리드)
- 한국어 라벨 사전 (`frontend/src/lib/labels.ts`)
- 포맷 헬퍼 (`frontend/src/lib/format.ts`)
- 새 사이드바 (5 + Settings, 폭 72px)
- ContextBar 신규
- Greeting / ActionCard / NarratorPanel 컴포넌트
- 홈 화면 (`/`) 본체
- Reports 메뉴 placeholder
- **FlowLens → TaskView 일괄 교체** (사용자 노출 영역 전체)
- 백엔드 `/v1/home/today` 엔드포인트 (1차)

### 패치 2 — Dashboard + 한국형 주간보고 1차 (7~8주차)
**범위:**
- Dashboard 화면 (DX Core 4 4섹션)
- MetricCard (3단 구조)
- 시간 분포 카드 (`time_allocation.py`)
- 가정 시뮬레이션 1차
- **주간보고 1차** (`weekly_report.py`, 임원/팀장/본인 3톤)
- Reports 페이지 + PDF/Markdown 내보내기
- `summary.py`에 `compare_with_previous_period()`
- 백엔드 `/v1/dashboard/summary`, `/time-allocation`, `/v1/reports/weekly`

### 패치 3 — Flow + 이슈 타임라인 자동 설명 (9~10주차) 🌟
**범위:**
- Flow 화면
- **이슈 타임라인 자동 설명** (`issue_explainer.py`) 🌟 1순위 차별화
- 이슈 상세 모달 컴포넌트
- 백엔드 `/v1/flow/stages`, `/by-role`, `/v1/issue/{id}/explanation`

### 패치 4 — Meeting + dim_user 확장 (11~12주차)
**범위:**
- alembic 0004(dim_user 6컬럼) + 0005(dim_role_baseline) + 0006(fct_meeting_prep)
- 역할 정보 입력 (raw_redmine_users payload 확인 후 결정)
- 모든 분석 모듈 "역할 인지" 버전 리팩터링
- `fairness.py`, `workload_health.py`, `meeting_brief.py` 신규
- Meeting 화면 본체
- WarningBanner, 자료 동결 저장, PDF 내보내기, 본인 공유
- 가정 시뮬레이션 2차 (인원 변경 시나리오)
- 백엔드 `/v1/meeting/{user_id}/brief`, `/v1/dashboard/scenario`
- **기존 5개 페이지 redirect 전환.** 기존 chart/table 컴포넌트 3개 삭제.

### 패치 5 — Settings + 팀즈 알림 + 학습 모드 + 월간보고 (13~16주차)
**범위:**
- Settings 화면 6개 탭 (연동은 패치 0에서 이미 완성)
  - 팀 약속 (Working Agreements 8종 한국어 템플릿)
  - 역할 매핑
  - 알림 규칙 (노코드 빌더, user_id 조건 차단)
  - 개인 데이터 노출 모드 (기본 OFF)
  - 학습 모드 (4주 자동)
- alembic 0007~0009
- **팀즈 Incoming Webhook 통합**
- WebSocket `/ws/alerts`
- **월간보고** (`monthly_report.py`)
- 분기 펄스 설문 (DX Core 4 5문항)
- 자연어 질의 인터페이스 (한국어, Logilica 한국화)
- `prescription.py` 본격 가동 (룰 30~50개)
- 기존 페이지 파일 완전 삭제

### 운영화 (보류)
Docker Compose / launchd / Caddy / Tailscale.

---

## 18. 검증 명령어

### 18.1 DB 카운트 (패치 0 후)
```bash
PGPASSWORD=change-me /opt/homebrew/opt/postgresql@17/bin/psql \
  -h localhost -p 5433 -U flowlens -d flowlens -c "
SELECT 'raw_redmine_issues' AS t, COUNT(*) FROM raw_redmine_issues UNION ALL
SELECT 'raw_redmine_journals', COUNT(*) FROM raw_redmine_journals UNION ALL
SELECT 'fct_state_transition', COUNT(*) FROM fct_state_transition UNION ALL
SELECT 'connector_instance', COUNT(*) FROM connector_instance UNION ALL
SELECT 'connector_resource', COUNT(*) FROM connector_resource;"
```

### 18.2 Backend 기동
```bash
cd ~/Taskview/backend && source .venv/bin/activate && \
  uvicorn app.api.main:app --reload --port 8000
```

### 18.3 Frontend 기동
```bash
cd ~/Taskview/frontend && npm run dev
```

### 18.4 연동 동기화 (패치 0 후 신규 명령)
```bash
# 즉시 동기화 (특정 connector_instance)
curl -X POST http://localhost:8000/v1/connectors/1/sync

# 동기화 진행 확인
curl http://localhost:8000/v1/connectors/1/sync-jobs
```

### 18.5 Ollama 모델 확인
```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"'
```

---

## 19. 주의사항 (Caveats)

- cycle_time_h 계산된 closed 이슈: 6,263 / 15,495 (40%) — started_on 미기록 다수
- TimescaleDB chunk_time_interval 기본값(7일) 사용 중 — 향후 90일로 조정 검토
- lucide-react는 ^0.544.0 명시 필수
- Tailwind 4 다크모드: `@custom-variant dark (&:where(.dark, .dark *))` + `.dark { ... }` 조합. `@media (prefers-color-scheme: dark)` 블록은 충돌
- payload 컬럼은 json 타입(jsonb 아님) → `json_array_elements` 사용
- zsh heredoc에서 `${...}` 충돌 주의 → `python3 - <<'PY'` 패턴 사용
- 패치 4 시작 전 raw_redmine_users payload 1건 확인하여 역할 정보 출처 결정
- **🆕 패치 0 마이그레이션 시 raw_* → raw_redmine_* rename으로 약 2~3분 다운타임 발생.** 사용자에게 사전 공지 필요.
- **🆕 패치 0 옵션 A 채택:** 상태 매핑 UI는 완성되나 변경사항이 분석에 즉시 반영되지 않음. UI에 명시 안내. 실제 적용은 v1.5에서 옵션 B로 업그레이드 예정.

---

## 20. 새 대화/새 LLM에서 이어가기 — 권장 첫 메시지

다음 메시지를 새 대화창 또는 다른 LLM에 첨부 파일과 함께 보내면 즉시 작업 재개 가능:

> 첨부한 `TaskView_Master_Spec_v2.md`는 TaskView 프로젝트의 전체 컨텍스트입니다. 이 문서를 기준으로 작업을 이어갑니다.
>
> 현재 상태는 설계 단계 완료, **패치 0 코드 작성 직전**입니다. 본 문서의 17장 "패치 로드맵"에 정의된 패치 0의 범위(Connector 추상화 + 연동 관리 UI + raw_* 테이블 rename + 9개 어댑터 클래스 작성, 그 중 Redmine만 active 나머지 8개는 coming_soon)를 한 번에 패치 코드로 작성해주세요.
>
> 본 문서의 모든 결정사항(특히 14장 윤리 가드레일, 11장 와이어프레임, 9장 디자인 토큰, 8장 한국어 용어 사전, 13장 Connector 인터페이스)을 그대로 준수해야 합니다. 사용자가 추가 결정을 요청하지 않은 영역은 본 문서의 결정을 변경하지 마십시오.

---

## 21. 결정 이력 (Decision Log)

| # | 결정 사항 | 근거/일자 |
|---|---|---|
| D01 | 재설계 방향 동의 (직급 IA → 의사결정 상황 IA, 화면 D 최우선) | 사용자 결정 |
| D02 | 기존 STEP B(Narrator 4문장) 중단, STEP B'로 직접 진입 | 중간 산출물 폐기 회피 |
| D03 | 용어 사전: Dashboard/Overview/Executive/Manager/Team/Filter 영문 유지 | 사용자 결정 |
| D04 | 용어 사전: Risk Score → 위험점수, Insight → 심층분석 | 사용자 결정 |
| D05 | 폰트: Pretendard 사용 | 사용자 결정 |
| D06 | 차별화 우선순위: ① 이슈 타임라인 자동 설명 ② 한국형 보고서 ③ 면담 준비 | 사용자 결정 |
| D07 | 알림 채널: 팀즈 단독, Incoming Webhook 방식 | 사용자 결정 |
| D08 | **제품명 FlowLens → TaskView 전면 교체** | 사용자 결정 |
| D09 | DB명/디렉터리/패키지 경로는 그대로 유지 (내부 명칭) | 데이터 이관 회피 |
| D10 | 패치는 별도 명령 시점부터 시작, 자동 진행 금지 | 사용자 결정 |
| D11 | **🆕 패치 0 진행 결정** — Connector 추상화 + 연동 관리 UI를 패치 1 전에 필수 추가 | 사용자 결정 |
| D12 | **🆕 지원 도구 9개**: Redmine(active) / Jira / Asana / GitHub / GitLab / Notion / ClickUp / Monday.com / Trello (8개 coming_soon) | 사용자 결정 |
| D13 | **🆕 카테고리 3분할**: 업무관리 도구 / 메시징 / 코드 저장소. 메시징은 현재 비어있음 (향후 Slack/팀즈/잔디/카카오워크 추가) | 사용자 결정 |
| D14 | **🆕 상태 매핑 옵션 A 채택**: 매핑 UI는 완성하되 1차에서는 표시만, 분석 적용은 v1.5에서 | 사용자 결정 |

---

## 22. 마무리

본 문서는 TaskView 프로젝트의 단일 진실 공급원(Single Source of Truth) v2입니다. 본 문서에 명시되지 않은 결정사항이 필요한 경우, 작업 LLM은 사용자에게 반드시 확인을 요청해야 합니다.

본 문서의 어떤 결정사항도 사용자 명시 동의 없이 변경하지 마십시오. 변경이 필요해 보이는 경우 변경안과 근거를 제시한 뒤 사용자 승인을 받아야 합니다.

작업 시작 명령(예: "패치 0 시작")이 있을 때까지 코드 패치를 자동 진행하지 마십시오.

— TaskView Master Spec v2, 2026-05-09
