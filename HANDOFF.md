# TaskView — 인수인계 문서

**작성일:** 2026-05-21  
**다음 세션 포커스:** MVP 개발 착수 (이슈 #2 DB 마이그레이션 + 이슈 #3 디자인 시스템부터 병렬 시작)

---

## 프로젝트 현황

**레포:** https://github.com/considerlabs/taskinsight  
**프로젝트 루트:** `~/Taskview/` (TaskInsight 레포와 별개 — 레포는 문서 전용, 코드는 ~/Taskview/)

### 이번 세션에서 완료된 것

1. `/grill-me` — 14개 질문으로 MVP 설계 결정사항 전부 확정
2. `TaskInsight_Spec_v2.md` 작성 — 기존 v1 스펙을 그릴링 결정사항으로 갱신
3. `PRD_TaskView_MVP.md` 작성 + GitHub 이슈 #1로 등록
4. 수직 슬라이스 14개 GitHub 이슈 #2~#15로 등록

---

## 핵심 결정사항 (요약)

전체 내용: `TaskInsight_Spec_v2.md` 15장 "결정 이력" 참조

| 항목 | 결정 |
|---|---|
| 1차 사용자 | 팀장 + PM |
| MVP 4화면 | Flow+타임라인 / 주간보고 / Dashboard / Settings |
| Patch 0 연동 UI | **생략** — BaseConnector ABC + raw rename만 |
| LLM (타임라인+처방) | `qwen3.6:35b-a3b` |
| LLM (관찰 레이어) | `qwen2.5-coder:14b` |
| LLM 캐싱 | 위험점수 상위 20건 새벽 2시 배치 + 온디맨드 캐시 |
| Dashboard | Speed + Effectiveness + Quality (Business Impact 제외) |
| 주간보고 | 3항목만, 화면 전용(PDF 없음), 수동 버튼 트리거 |
| 액션 | Read-only (Redmine 쓰기 없음) |
| 배포 | Localhost 시작, 인증 없음 |

---

## GitHub 이슈 맵

| 이슈 | 제목 | 선행 | 상태 |
|---|---|---|---|
| [#2](https://github.com/considerlabs/taskinsight/issues/2) | DB 마이그레이션 (alembic 0003) | 없음 | 🟢 시작 가능 |
| [#3](https://github.com/considerlabs/taskinsight/issues/3) | 디자인 시스템 + 사이드바 + 글로벌 필터 | 없음 | 🟢 시작 가능 |
| [#4](https://github.com/considerlabs/taskinsight/issues/4) | Connector 추상화 | #2 | ⏳ |
| [#5](https://github.com/considerlabs/taskinsight/issues/5) | Flow API | #2 | ⏳ |
| [#6](https://github.com/considerlabs/taskinsight/issues/6) | Dashboard API | #2 | ⏳ |
| [#7](https://github.com/considerlabs/taskinsight/issues/7) | Settings API | #4 | ⏳ |
| [#8](https://github.com/considerlabs/taskinsight/issues/8) | 이슈 타임라인 LLM 설명 API + 캐싱 | #2, #5 | ⏳ |
| [#9](https://github.com/considerlabs/taskinsight/issues/9) | 주간보고 API | #2, #6 | ⏳ |
| [#10](https://github.com/considerlabs/taskinsight/issues/10) | LLM 배치 + ETL 자동 연계 | #8 | ⏳ |
| [#11](https://github.com/considerlabs/taskinsight/issues/11) | Flow 화면 UI | #5, #3 | ⏳ |
| [#12](https://github.com/considerlabs/taskinsight/issues/12) | Dashboard 화면 UI | #6, #3 | ⏳ |
| [#13](https://github.com/considerlabs/taskinsight/issues/13) | 주간보고 화면 UI | #9, #3 | ⏳ |
| [#14](https://github.com/considerlabs/taskinsight/issues/14) | Settings 화면 UI | #7, #3 | ⏳ |
| [#15](https://github.com/considerlabs/taskinsight/issues/15) | 이슈 타임라인 모달 UI | #8, #11 | ⏳ |

---

## 코드베이스 현황 (~/Taskview/)

### 이미 구현 완료 (건드리지 말 것)

- **DB:** PostgreSQL 17 (port 5433), DB명 `flowlens`, TimescaleDB 2.26.4
- **백엔드 분석 모듈 8개:** status_groups, bottleneck, risk, forecast, resource, anomaly, critical_path, summary — 모두 200 검증 완료
- **FastAPI 엔드포인트 9개:** `/v1/executive/*`, `/v1/manager/*`, `/v1/team/*`, `/v1/insight/*`, `/healthz` — 유지
- **프론트엔드 5페이지:** `/executive`, `/manager`, `/team`, `/insight`, `/executive/overview` — MVP 기간 공존

### 다음 세션에서 수정할 파일

이슈 #2 (DB 마이그레이션):
- `~/Taskview/backend/alembic/versions/` — 0003 마이그레이션 파일 신규
- `~/Taskview/backend/app/analytics/*.py` — SQL에서 `raw_` → `raw_redmine_` 일괄 수정
- `~/Taskview/backend/app/etl/*.py` — 동일

이슈 #3 (디자인 시스템):
- `~/Taskview/frontend/src/app/globals.css`
- `~/Taskview/frontend/src/lib/labels.ts` (신규)
- `~/Taskview/frontend/src/lib/format.ts` (신규)
- `~/Taskview/frontend/src/components/Sidebar.tsx`

### 환경 시작 명령

```bash
# DB 시작
/opt/homebrew/opt/postgresql@17/bin/pg_ctl \
  -D /opt/homebrew/var/flowlens-pg17 \
  -l /opt/homebrew/var/flowlens-pg17/server.log start

# 백엔드
cd ~/Taskview/backend && source .venv/bin/activate && \
  uvicorn app.api.main:app --reload --port 8000

# 프론트엔드
cd ~/Taskview/frontend && npm run dev

# Ollama 확인
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep '"name"'
```

### 주요 데이터 현황

- `raw_issues`: 16,092건 (→ 마이그레이션 후 raw_redmine_issues)
- `raw_journals`: 97,302건
- 주요 프로젝트: project_id=29 (만나 플랫폼), open 493건
- 위험 이슈 예시: #10729 (검수 대기 1,300+일), #8745 (847일)

---

## 주의사항

- `~/Taskview/` 디렉터리와 `~/TaskInsight/` 레포는 별개. 코드는 Taskview, 문서는 TaskInsight.
- DB명은 내부적으로 `flowlens` 유지 (데이터 이관 회피 결정 D09)
- `payload` 컬럼은 jsonb가 아닌 json 타입 → `json_array_elements` 사용
- Tailwind 4 다크모드: `@custom-variant dark` 사용. `@media prefers-color-scheme` 블록 충돌 주의
- `lucide-react` 버전 `^0.544.0` 명시 필수
- zsh heredoc에서 `${...}` 충돌 → `python3 - <<'PY'` 패턴 사용

---

## 참조 문서

| 문서 | 경로/URL |
|---|---|
| 마스터 스펙 v2 | `TaskInsight_Spec_v2.md` |
| 원본 스펙 v1 (참고용) | `TaskInsight_Spec.md` |
| PRD | `PRD_TaskView_MVP.md` / [이슈 #1](https://github.com/considerlabs/taskinsight/issues/1) |
| 이슈 트래커 | https://github.com/considerlabs/taskinsight/issues |

---

## 다음 세션 시작 방법

```
TaskInsight_Spec_v2.md와 HANDOFF.md를 읽고 작업을 이어갑니다.

현재 상태: 설계 완료, 이슈 #2(DB 마이그레이션)와 이슈 #3(디자인 시스템)을
병렬로 시작할 수 있습니다.

코드 작업 디렉터리: ~/Taskview/
문서 레포: https://github.com/considerlabs/taskinsight

이슈 #2부터 시작해주세요.
```

---

## 제안 스킬

다음 세션에서 유용한 스킬:

- `/simplify` — 패치 완료 후 코드 품질 검토
- `/caveman-review` — PR 리뷰 시 압축된 피드백
- `/handoff` — 다음 세션 인수인계 시
