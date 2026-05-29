# HANDOFF — TaskInsight_V 재설계 작업 인수인계

> **목적:** 이 파일을 읽은 AI/개발자는 추가 컨텍스트 없이 TaskInsight_V 레포 생성 → 문서 업로드 → 이슈 등록까지 완료할 수 있다.
> **작성일:** 2026-05-29
> **작성 주체:** 분석·검증 세션 (Claude)
> **수행 주체:** gh CLI + git 인증된 환경 (사람 또는 에이전트)
> **원본 저장소:** https://github.com/considerlabs/taskinsight (공개, Python, main)

---

## 0. 한 줄 요약

기존 TaskInsight MVP(Redmine 분석 SEI 대시보드, 개발 완료)를 코드·이슈 수준까지 검증한 결과를 토대로, 자체 도구 데이터 기반 인사이트 카드 14종 + Phase 2 데이터 요구사항을 반영한 재설계 문서 세트와 이슈 체계를 TaskInsight_V 신규 레포에 구축한다.

---

## 1. 작업 범위 (사용자 원 요청)

1. 기존 TaskInsight 개발문서를 분석·검증하여 재설계 내용이 반영된 동일 포맷 문서로 재작성한다.
2. GitHub의 모든 문서(docs/) + 소스 + 등록 이슈 + 닫힌 이슈를 분석·검증한다.
3. TaskInsight_V 레포를 생성하고, 작성된 파일을 업로드하며, 이슈별로 나누어 등록한다.

⚠️ 분석 세션의 한계: 분석 세션(Claude)은 GitHub 쓰기 권한이 없어 레포 생성/push/이슈 등록을 직접 수행하지 못했다. 따라서 본 handoff의 §6 스크립트를 인증된 환경에서 실행하여 완료해야 한다.

---

## 2. 원본 저장소 검증 결과 (사실 확인 완료)

### 2.1 저장소 메타
- 공개(private: false), 언어 Python, 기본 브랜치 main
- open_issues_count: 2 (PRD 2건만 open, 슬라이스 전부 closed)
- 실제 데이터(이슈 #1 본문 기준): raw_issues 16,092건, raw_journals 97,302건, 만나 플랫폼 open 493건
  - 참고: 첨부문서엔 16,111건으로 기재 — 수집 시점 차이, 작업엔 영향 없음

### 2.2 이슈 체계 (검증 완료)
- 부모 PRD → [Slice N] 자식 구조. body는 "## Parent / ## What to build / ## Acceptance criteria / ## Blocked by" 포맷.
- #1: PRD MVP(open), #16: PRD 업무관리 Phase1(open)
- #2~#15, #17~#25: [Slice N] 자식, 대부분 closed/completed
  - 예) #2 DB마이그 0003, #3 디자인시스템, #4 Connector추상화, #5 Flow API, #24 마일스톤, #25 Redmine마이그
- TaskInsight_V는 이 컨벤션을 그대로 따른다.

### 2.3 소스 구조 (검증 완료)
backend/app/
  api/routers/  flow.py, dashboard.py, reports.py, connectors.py
  etl/populate.py         ← 마트 ETL (핵심)
  narrator/               issue_explainer.py, weekly_report.py
  connectors/             base.py + redmine(active) + 8개 coming_soon
  scripts/                migrate_from_redmine.py, seed.py, create_test_data.py
  schemas/                auth.py, issues.py, common.py
  alembic/versions/       0001_raw_redmine, 0002_mart, 0003_mvp
frontend/app/             flow, dashboard, reports/weekly, settings
docs/                     11개 .md + adr/ 4개

### 2.4 ★ 코드 수준 핵심 발견 (재설계의 근거)

실제 소스를 읽어 확인한 사실. 이전 추정이 코드로 확정/수정됨.

| # | 발견 | 위치 | 재설계 영향 |
|---|---|---|---|
| F1 | days_in_stage가 단계 무관 "마지막 status 전환 후 경과일" | etl/populate.py populate_issue_snapshot (MAX(t.changed_at)) | INS-R-001 단계별 체류는 fct_state_transition 구간으로 재집계 필수 |
| F2 | is_rework(review→in_progress 전환 존재 여부) 이미 구현됨 | etl/populate.py populate_issue_snapshot | INS-R-006/014 기반 존재. 사유코드만 추가하면 됨 |
| F3 | total_days = closed_on - created_on 정확 구현 | etl/populate.py | INS-R-002 리드타임 유지(PASS) |
| F4 | fct_throughput_daily가 closed_on 기반(journals 전이 아님) | etl/populate.py populate_throughput_daily | INS-R-003 처리율: 유입측은 신규 구현 필요 |
| F5 | ★ risk_score 절대임계치 하드코딩(365/90/30일, 70점) | etl/populate.py _compute_risk_score + flow.py risk_score>=70 | 윤리제약 "절대임계치 금지, 상대기준만" 정면 위반 → 최우선 보정 |
| F6 | LAG() OVER를 CTE로 우회 처리 패턴 이미 사용 | etl/populate.py update_transition_days | CLAUDE.md 코딩규칙 준수 확인됨 |

---

## 3. Phase 1~3 설계 산출물 요약 (이전 세션 결과)

### 3.1 인사이트 카드 14종 (전환검증 결과 포함)

| ID | 제목 | 카테고리 | 대상 | 전환검증 action |
|---|---|---|---|---|
| INS-R-001 | 단계별 정체 | 흐름 | 양쪽 | 정의 보정 (F1: 단계구간 재집계, 결손해소 상향점프) |
| INS-R-002 | 리드타임 분포 | 흐름 | 양쪽 | 유지 (F3: PASS) |
| INS-R-003 | 유입 vs 처리 비율 | 속도 | 의사결정권자 | 정의 보정 (F4: 유입측 신규) |
| INS-R-004 | blocked 지속시간 | 속도 | 중간관리자 | 정의 보정 (재정의) |
| INS-R-005 | 전이 vs 활동(stall) | 속도 | 중간관리자 | 정의 보정 |
| INS-R-006 | 재오픈율 | 품질 | 양쪽 | 정의 보정 (F2: is_rework 확장, 하향점프) |
| INS-R-007 | WIP 동시진행 | 부하 | 중간관리자 | 정의 보정 (스냅샷 기반) |
| INS-R-008 | 마일스톤 번다운 | 예측가능성 | 양쪽 | 정의 보정 (baseline 필요) |
| INS-R-009 | 에이징 백로그 | 위험 | 중간관리자 | 일시 비활성화 13주 (updated_on 일괄갱신 리셋) |
| INS-R-010 | 마감 신뢰도 | 예측가능성 | 의사결정권자 | 유지 (PASS) |
| INS-R-011 | 부하 쏠림(프로젝트) | 부하 | 의사결정권자 | 정의 보정 + 윤리가드 |
| INS-R-012 | 담당자 핑퐁 | 위험 | 중간관리자 | 정의 보정 + 윤리가드 |
| INS-R-013 | 이슈 구조 건강도 | 구조 | 양쪽 | 유지 (PASS) |
| INS-R-014 | review 반려율 | 품질 | 중간관리자 | 정의 보정 (F2: is_rework 기반) |

집계: 유지 3 / 정의보정 10 / 일시비활성화 1.

### 3.2 Phase 2 데이터 요구사항 (도입 로드맵)

| 우선순위 | 항목 | friction | 비고 |
|---|---|---|---|
| 즉시 | field_change_events (append-only 이벤트로그) | 1 자동 | 데이터 척추. WIP/체류 replay 제거 |
| 즉시 | daily_issue_state (일별 스냅샷) | 1 자동 | 배치 파생 |
| 즉시 | milestone_baselines (커밋 스냅샷) | 1 자동 | scope creep 측정 |
| 즉시 | risk_score 상대분포 교체 (F5) | 코드수정 | 윤리위반 시정 최우선 |
| 3개월 | transition_reasons (사유코드 enum) | 2~3 | 재할당/재오픈/반려 분리 |
| 3개월 | issue_blocks (blocked-by 링크) | 2 | 의존성 그래프 |
| 3개월 | issues.source (출처분류) | 2 | 유입 수요신호 |
| 6개월 | work_sessions (자동 시간추정) | 2 | 수동시간기록은 폐기 |
| 폐기 | 수동 시간기록 강제 | 5 | Redmine 20건으로 실패 증명 |
| 폐기 | 개인 단위 멘션 네트워크 노출 | — | 윤리위반 |

### 3.3 윤리 가드레일 (절대 위반 금지)
1. 개인 단위 비교/순위/단일점수 금지
2. 절대 임계치 금지, 조직 내부 상대 기준만 (★F5 시정 대상)
3. 평가 목적 사용 금지, 의사결정 지원만
4. 개인 생산성 데이터는 본인만 열람 (work_sessions raw)

---

## 4. 작성해야 할 문서 (TaskInsight_V/docs/)

기존 11개 문서와 동일 포맷 유지하되 재설계 반영. 우선순위 순.

| 파일 | 내용 | 기존 대비 변경점 |
|---|---|---|
| docs/INSIGHT_CARDS.md | 14종 카드 명세 (§3.1 표 + 개별 상세) | 신규 |
| docs/insights/INS-R-0NN.json | 카드별 JSON 스키마 14개 | 신규 |
| docs/PHASE2_DATA_REQUIREMENTS.md | §3.2 데이터 요구사항 | 신규 |
| docs/SCHEMA.md | 기존 + field_change_events, daily_issue_state, milestone_baselines, transition_reasons, issue_blocks 추가 | 테이블 5종 추가 |
| docs/CONTEXT.md | 기존 + 재설계 배경, F1~F6 발견 | 보완 |
| docs/MIGRATION_IMPACT.md | 전환영향도 보고서 + 사용자 공지문 | 신규 |
| docs/ETHICS_GUARDRAILS.md | §3.3 + risk_score 상대분포 교체 명세 | 신규 |
| docs/PRD_V.md | 재설계 PRD (이전 세션 작성분) | 신규 |
| docs/UI_SPEC_V.md | 카드 UI(3영역, 전환구분선, 기준재설정 배지) | 신규 |

문서 본문은 이전 세션 답변에 작성됨. 그대로 복사하여 각 파일로 배치.

---

## 5. 등록할 이슈 (TaskInsight_V)

| 이슈 | 제목 | 시점 | 근거 |
|---|---|---|---|
| PRD | TaskInsight_V — 인사이트 카드 시스템 | — | 부모 |
| SV1 | 데이터 척추: append-only 이벤트로그 + 일별 스냅샷 | 즉시 | WIP replay 제거 |
| SV2 | 마일스톤 commitment baseline 스냅샷 | 즉시 | baseline 미존재 |
| SV3 | risk_score 절대임계치 → 상대분포 교체 (윤리) | 즉시 | ★F5 윤리위반 시정 |
| SV4 | 단계별 체류 재집계 (INS-R-001) | 3개월 | F1 |
| SV5 | 전이 사유코드 (INS-R-006/012/014) | 3개월 | F2 확장 |
| SV6 | 인사이트 카드 14종 + 마이그레이션 경계처리 | 3개월 | UI 통합 |

---

## 6. 실행 스크립트 (gh CLI + git 인증 환경에서 실행)

```bash
#!/usr/bin/env bash
# bootstrap_taskinsight_v.sh
# 사전조건: gh auth login 완료, git 설치, 본 handoff와 같은 폴더에 docs 원본 준비
set -euo pipefail
ORG="considerlabs"; REPO="TaskInsight_V"

echo "==> 1. 레포 생성 + 클론"
gh repo create "$ORG/$REPO" --public \
  --description "TaskInsight 재설계: 자체도구 데이터 기반 인사이트 카드 14종 (코드검증 반영)" \
  --clone
cd "$REPO"; mkdir -p docs/insights

echo "==> 2. 문서 배치"
# 이전 세션이 작성한 본문을 각 파일로 작성 (예시 2개. 나머지는 §4 표대로 동일 패턴)
cat > docs/INSIGHT_CARDS.md <<'EOF'
# TaskInsight_V — 인사이트 카드 명세 (14종)
(본문: 분석세션 §3.1 + 카드별 상세를 여기 배치)
EOF
cat > docs/PHASE2_DATA_REQUIREMENTS.md <<'EOF'
# TaskInsight_V — Phase 2 데이터 요구사항
(본문: 분석세션 §3.2 로드맵 배치)
EOF
# TODO: SCHEMA.md, MIGRATION_IMPACT.md, ETHICS_GUARDRAILS.md, PRD_V.md, UI_SPEC_V.md 동일 패턴

git add -A
git commit -m "docs: TaskInsight_V 재설계 문서 초기 커밋 (인사이트 카드 14종 + Phase2 요구사항, 코드검증 반영)"
git push -u origin main

echo "==> 3. PRD(부모 이슈) 생성"
PRD_URL=$(gh issue create --repo "$ORG/$REPO" \
  --title "PRD: TaskInsight_V — 인사이트 카드 시스템 (자체도구 데이터 기반)" \
  --body "## Problem Statement
기존 TaskInsight MVP는 Redmine 데이터(시간기록 20건·사유 자유텍스트·스냅샷 없음) 한계로 '건강한 인계 vs 책임표류', '마감 옮겨 지킨 척' 등 핵심 의사결정 질문에 답 못함. 코드검증 결과 risk_score가 절대임계치(365일/90일/70점) 하드코딩되어 윤리제약(상대기준만) 위반 확인.

## Solution
append-only 이벤트로그 + 사유코드 체계로 인사이트 카드 14종 구현. 절대임계치를 조직 내부 상대분포로 교체.

## 코드검증으로 확정된 보정 (실제 소스 대조)
- [x] F1: fct_issue_snapshot.days_in_stage가 단계무관 → 단계구간 재집계
- [x] F2: is_rework(review→in_progress) 이미 구현 → 사유코드만 추가
- [x] F3: total_days(closed_on-created_on) 정확 → 리드타임 유지
- [x] F4: fct_throughput_daily가 closed_on 기반 → 유입측 신규
- [x] F5: risk_score 절대임계치 하드코딩 → 상대분포 교체 (최우선)

## 슬라이스
SV1~SV6 (자식 이슈 참조)")
echo "PRD: $PRD_URL"
PRD_NUM="${PRD_URL##*/}"

echo "==> 4. 슬라이스 이슈 등록"
declare -a SLICES=(
"[SV1] 데이터 척추: append-only 이벤트로그 + 일별 스냅샷|field_change_events·daily_issue_state 테이블 신설. ETL hook으로 모든 issues 필드변경 자동 append. WIP·체류를 replay 없이 즉시 산출.|alembic 0008 신규|friction1 자동수집|즉시"
"[SV2] 마일스톤 commitment baseline 스냅샷|milestone_baselines 테이블. 마일스톤 시작시 범위·due_date 동결. INS-R-008 scope creep 측정.|alembic 0008|friction1|즉시"
"[SV3] risk_score 절대임계치 → 상대분포 교체 (윤리)|_compute_risk_score와 flow.py risk_score>=70 하드코딩 제거. 조직 내부 백분위(p85 등) 기반 교체. 윤리제약 '절대임계치 금지' 준수.|etl/populate.py·flow.py 수정|코드수정|즉시"
"[SV4] 단계별 체류 재집계 (INS-R-001)|days_in_stage를 fct_state_transition 구간으로 분해. stage별 p50/p85 산출. unknown버킷 분리.|etl 보정|medium|3개월"
"[SV5] 전이 사유코드 (INS-R-006/012/014)|transition_reasons 테이블. 재할당/재오픈/반려 enum 사유. is_rework 기반 확장. 정상인계 vs 실제문제 분리.|enum 드롭다운|friction2~3|3개월"
"[SV6] 인사이트 카드 14종 + 마이그레이션 경계처리|카드 UI(상단부상/모니터링/비활성화 3영역). 전환구분선·기준재설정 배지. 에이징 13주 비활성. 개인분해 차단 가드.|frontend+API|high|3개월"
)
for s in "${SLICES[@]}"; do
  IFS='|' read -r title body schema friction phase <<< "$s"
  blocked=$([ "$phase" = "즉시" ] && echo "None — can start immediately" || echo "$ORG/$REPO#$PRD_NUM 의 SV1(데이터 척추) 완료 후")
  gh issue create --repo "$ORG/$REPO" --title "$title" --body "## Parent
$ORG/$REPO#$PRD_NUM

## What to build
$body

## 스키마/구현
$schema

## 입력부담
$friction

## 도입시점
$phase

## Acceptance criteria
- [ ] 기능 구현 완료
- [ ] 윤리제약(상대기준·개인분해 차단) 준수
- [ ] 마이그레이션 경계 처리(해당 시)
- [ ] 기존 flow/dashboard/reports/connectors 회귀 없음

## Blocked by
$blocked"
  echo "등록: $title"
done

echo "==> 완료: https://github.com/$ORG/$REPO"
