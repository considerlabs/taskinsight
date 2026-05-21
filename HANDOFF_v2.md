# TaskInsight — Handoff v2

**Date:** 2026-05-21  
**Branch:** `main` (up to date with `origin/main`)  
**Repo:** https://github.com/considerlabs/taskinsight  
**Focus for next session:** 저널 전체 수집 완료, dim_status 매핑 검증, UI 품질 개선

---

## Project Overview

TaskInsight = Redmine 데이터 기반 팀 플로우 분석 플랫폼 (한국형 SEI).  
스펙: `/Users/guyskim/TaskInsight/TaskInsight_Spec_v2.md`  
PRD: `/Users/guyskim/TaskInsight/PRD_TaskInsight_MVP.md`

---

## Stack

| Layer | Tech |
|---|---|
| DB | PostgreSQL 17 + TimescaleDB, port **5433** (shared flowlens-pg17 instance) |
| Backend | FastAPI + SQLAlchemy + psycopg3 (NOT psycopg2), Python **3.9** |
| Frontend | Next.js 16 App Router, Tailwind 4, port **3001** |
| LLM | Ollama localhost:11434, model `qwen3.6:35b-a3b` |
| Migrations | Alembic (0001 raw → 0002 mart → 0003 mvp) |

**Python 3.9 critical rules:**
- Always `from __future__ import annotations` at top of every backend file
- Use `Optional[X]` not `X | None`; `Union[A, B]` not `A | B`

---

## Current DB State (2026-05-21)

| Table | Rows |
|---|---|
| raw_redmine_issues | 16,111 |
| raw_redmine_users | 85 |
| raw_redmine_journals | 1,381 |
| raw_redmine_projects | 4 |
| fct_issue_snapshot | 16,111 |
| fct_state_transition | 164 |
| dim_user | 85 |
| dim_project | 4 |

**Flow stage distribution:**
- done: 10,129
- backlog: 5,851
- in_progress: 111
- review: 20

**Issues without journals: 15,922** (=97% 미수집, ongoing)

---

## All Issues Implemented (#2–#15)

전체 구현 완료. 이후 버그픽스 커밋들:
- `bed8f2e` fix: sync 0-count, missing users/journals, LLM timeout
- `dcdc0b8` fix: LAG() in UPDATE → CTE
- `ee20361` fix: psycopg Jsonb() for JSONB update
- `102afde` fix: CORS port 3001, settings error handling
- `9cef135` feat: issues #11–#15 UI layer
- `60b1457` feat: issues #2–#10 backend + frontend

---

## Architecture: Key Files

### Backend
```
backend/
  .env                          # DB/Ollama config (API key stored in DB, not here)
  alembic.ini                   # sqlalchemy.url = postgresql+psycopg://taskinsight:change-me@localhost:5433/taskinsight
  alembic/versions/
    0001_raw_redmine.py         # raw_redmine_* tables + sync_state
    0002_mart.py                # dim_* + fct_* mart tables
    0003_mvp.py                 # connector_instance (seeded), fct_issue_explanation, fct_weekly_report
  app/
    config.py                   # pydantic-settings Settings
    db.py                       # engine + SessionLocal + get_db()
    api/main.py                 # FastAPI app, CORS (ports 3000/3001/3002), startup scheduler
    api/routers/
      connectors.py             # GET /instances, POST /test, PUT /:id, POST /:id/sync
      flow.py                   # GET /stages, /issues, /issue/:id/explanation
      dashboard.py              # GET /summary (speed/effectiveness/quality)
      reports.py                # POST /weekly/generate, GET /weekly/latest, GET /weekly/history
    connectors/
      base.py                   # BaseConnector ABC
      redmine/connector.py      # RedmineConnector — _fetch_issues, _fetch_users (no status param), _fetch_projects
      registry.py               # CONNECTORS dict + COMING_SOON
    collector/
      redmine_collector.py      # sync_redmine(), _collect_journals(), _extract_users_from_issues()
    etl/
      populate.py               # run_etl() → dim_project, dim_user, state_transitions, issue_snapshot, throughput
    narrator/
      issue_explainer.py        # explain_issue() → Ollama with think:false
      weekly_report.py          # generate_weekly_report() → Ollama with think:false
    scheduler.py                # APScheduler 2AM: sync → ETL → 800 extra journals → LLM top-20
```

### Frontend
```
frontend/
  app/
    page.tsx                    # redirect → /flow
    flow/page.tsx               # Funnel + issue table + stage filter + modal
    dashboard/page.tsx          # Speed/Effectiveness/Quality MetricCards
    reports/weekly/page.tsx     # Weekly report + generate button + LLM narrative
    settings/page.tsx           # Redmine form: test/save/sync + cumulative count display
    globals.css                 # Pretendard, @custom-variant dark, design tokens
  components/
    Sidebar.tsx                 # 72px sidebar, 4 nav items
    GlobalFilter.tsx            # project + period select
    IssueTimelineModal.tsx      # LLM explanation modal, ESC close, Redmine link
    MetricCard.tsx, SectionCard.tsx, Spinner.tsx
  lib/
    api.ts                      # typed API client
    labels.ts                   # STAGE_LABELS, STAGE_COLOR, METRIC_LABELS
    format.ts                   # formatDays, formatCount, formatDate, riskEmoji
```

---

## Known Issues / Next Work

### 1. 저널 수집 진행 중 (가장 큰 과제)
- 15,922개 이슈에 저널 없음
- 각 sync 시 200건 수집 (UI 동기화), 야간 배치 800건 추가
- 완료까지 ~16일 소요 (자동)
- **수동 가속 옵션**: `/admin/etl` 엔드포인트로 ETL만 반복 실행하거나, `_collect_journals(db, config, max_issues=2000)` 직접 호출

```python
# 빠른 저널 대량 수집 방법:
cd /Users/guyskim/TaskInsight/backend
source .venv/bin/activate
python3 << 'EOF'
from app.db import SessionLocal
from sqlalchemy import text
from app.collector.redmine_collector import _collect_journals

db = SessionLocal()
row = db.execute(text("SELECT config FROM connector_instance WHERE is_active = TRUE LIMIT 1")).fetchone()
count = _collect_journals(db, row.config, max_issues=2000)
print(f"수집: {count}건")
db.close()
EOF
```

### 2. dim_status 매핑 검증 필요
- `dim_status` 테이블: Redmine 상태 ID → `flow_stage` 매핑
- 현재 state_transitions 164건 중 `from_stage`/`to_stage` = 'unknown'이 많을 가능성
- DB 확인: `SELECT * FROM dim_status ORDER BY status_id;`
- 시드 데이터가 실제 Redmine 상태 ID와 맞는지 확인 필요

### 3. `fct_state_transition` 희소
- 164건은 25개 이슈 분량 — 저널 수집이 쌓이면 자동 증가
- 다음 ETL 실행 후 확인: `POST http://localhost:8000/admin/etl`

### 4. rework_rate = 0%
- review → in_progress 역방향 전환 감지 로직 있음
- 저널이 충분히 쌓이면 자연히 올라올 것

### 5. weekly_report assignee 이름 표시
- `dim_user.login` = 표시이름(display name), 실제 login 아님
- Redmine admin 권한 API로 `/users.json` 호출 시 실제 login 얻을 수 있음
- 현재는 이슈 payload author.name → login 컬럼에 저장

---

## Psycopg3 / SQLAlchemy 핵심 패턴

```python
# JSONB 컬럼 업데이트 — 반드시 Jsonb() 래핑
from psycopg.types.json import Jsonb
params["config"] = Jsonb(merged)
db.execute(text("UPDATE t SET config = :config WHERE id = :id"), params)

# json 컬럼 payload — -> 연산자, ->> 텍스트 추출
# payload는 json 타입 (not jsonb): raw_redmine_issues, raw_redmine_journals, raw_redmine_users

# DISTINCT ON json 컬럼 시 equality operator 없음 → DISTINCT ON (key_col) 사용

# LAG() OVER in UPDATE 불가 → CTE로 계산 후 JOIN UPDATE
```

---

## Ollama 사용 규칙

```python
# Qwen3 모델은 반드시 think:false 지정 — 없으면 thinking tokens 소비 후 content 비어있음
resp = httpx.post(url, json={
    "model": "qwen3.6:35b-a3b",
    "messages": [...],
    "stream": False,
    "think": False,          # ← 필수
    "options": {"temperature": 0.3},
}, timeout=120)
```

---

## 서버 시작 명령

```bash
# Backend
cd /Users/guyskim/TaskInsight/backend
source .venv/bin/activate
uvicorn app.api.main:app --reload --port 8000

# Frontend
cd /Users/guyskim/TaskInsight/frontend
npm run dev -- --port 3001

# DB (이미 실행 중이면 skip)
brew services start flowlens-pg17  # or: pg_ctl -D /opt/homebrew/var/taskinsight-pg17 start

# Ollama (이미 실행 중이면 skip)
ollama serve
```

---

## Suggested Skills

다음 세션에서 유용한 스킬:

- `/handoff` — 세션 종료 시 핸드오프 문서 작성
- `/commit` — 작업 완료 후 커밋
