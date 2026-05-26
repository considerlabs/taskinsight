# TaskInsight — 테스트 시나리오

> 각 Phase 완료 후 아래 시나리오를 전부 통과해야 운영 투입 가능.
> 테스트 계정: admin@test.com / manager@test.com / member@test.com / viewer@test.com

---

## 사전 조건 (테스트 환경)

```bash
# 테스트 DB 초기화
docker-compose exec backend python -m app.scripts.seed
docker-compose exec backend python -m app.scripts.create_test_data

# 테스트 계정
# admin@test.com      / TestAdmin123!     (system_admin)
# manager@test.com    / TestManager123!   (project_manager)
# member@test.com     / TestMember123!    (member)
# viewer@test.com     / TestViewer123!    (viewer)
# 테스트 프로젝트: identifier="test-project", name="테스트 프로젝트"
```

---

## Phase 1 테스트 시나리오

### 시나리오 1: 로그인 / 인증

| # | 시나리오 | 입력 | 기대 결과 |
|---|---|---|---|
| 1-1 | 정상 로그인 | admin@test.com / TestAdmin123! | 200 + access_token 반환 + Set-Cookie refresh_token |
| 1-2 | 잘못된 비밀번호 | admin@test.com / wrongpassword | 401 |
| 1-3 | 존재하지 않는 이메일 | nobody@test.com / any | 401 |
| 1-4 | 5회 실패 후 로그인 | 5회 틀린 후 재시도 | 423 (15분 잠금) |
| 1-5 | 만료된 토큰으로 API 호출 | 만료 토큰 | 401 |
| 1-6 | 토큰 없이 보호 경로 접근 | Authorization 헤더 없음 | 401 |
| 1-7 | 비활성 계정 로그인 | is_active=false 계정 | 401 |
| 1-8 | 토큰 갱신 | 유효한 refresh_token 쿠키 | 200 + 새 access_token |
| 1-9 | 로그아웃 | 유효한 토큰 | 200 + refresh_token 무효화 |
| 1-10 | 로그아웃 후 refresh 시도 | 무효화된 refresh_token | 401 |

### 시나리오 2: 권한 체크

| # | 시나리오 | 역할 | 기대 결과 |
|---|---|---|---|
| 2-1 | viewer가 이슈 생성 시도 | viewer | 403 |
| 2-2 | member가 이슈 삭제 시도 | member | 403 |
| 2-3 | member가 프로젝트 생성 시도 | member | 403 |
| 2-4 | manager가 다른 프로젝트 설정 수정 시도 | project_manager | 403 |
| 2-5 | admin이 모든 프로젝트 접근 | system_admin | 200 |
| 2-6 | 프로젝트 멤버가 아닌 사용자가 이슈 조회 | member (비멤버) | 403 |
| 2-7 | viewer가 이슈 목록 조회 | viewer | 200 |

### 시나리오 3: 이슈 CRUD

| # | 시나리오 | 입력 | 기대 결과 |
|---|---|---|---|
| 3-1 | 이슈 생성 (필수값만) | subject만 입력 | 201 + issue 반환 |
| 3-2 | 이슈 생성 (전체 필드) | 모든 필드 입력 | 201 + issue 반환 |
| 3-3 | 제목 없이 이슈 생성 시도 | subject="" | 422 |
| 3-4 | 이슈 조회 | 유효한 issue_id | 200 + issue 상세 |
| 3-5 | 존재하지 않는 이슈 조회 | id=99999 | 404 |
| 3-6 | 이슈 상태 변경 | status_id=2 (진행 중) | 200 + 저널 자동 생성 확인 |
| 3-7 | 완료 상태 변경 | status_id=5 | 200 + closed_at=NOT NULL + done_ratio=100 |
| 3-8 | 잘못된 상태 전환 시도 | 완료→진행 중 (member 역할) | 403 |
| 3-9 | 이슈 목록 조회 | project_id 필터 | 200 + 해당 프로젝트 이슈만 |
| 3-10 | 페이지네이션 | limit=10&offset=0 | 200 + items 최대 10개 + total 포함 |
| 3-11 | 하위 이슈 생성 | parent_id=유효한 이슈 ID | 201 |
| 3-12 | 순환 참조 시도 | parent_id=자기자신 | 400 |
| 3-13 | 다른 프로젝트 이슈를 parent로 설정 | 다른 project_id | 400 |

### 시나리오 4: 저널 (변경 이력)

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 4-1 | 이슈 수정 시 자동 저널 생성 | status_id 변경 | issue_journals에 레코드 생성 |
| 4-2 | notes만 있는 저널 | 상태 변경 없이 notes만 | journal 생성, details 없음 |
| 4-3 | 이슈 생성 시 저널 없음 | 신규 생성 | journals 0건 |
| 4-4 | 변경 없는 수정 | 동일 값으로 PUT | journal 생성 안 함 |

### 시나리오 5: Redmine 마이그레이션

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 5-1 | 마이그레이션 스크립트 실행 | raw_redmine_* 데이터 존재 | users, projects, issues 생성 |
| 5-2 | 멱등성 확인 | 2회 실행 | 중복 없음 (ON CONFLICT DO NOTHING) |
| 5-3 | 이슈 건수 검증 | 마이그레이션 후 | ti_issues ≥ raw_redmine_issues * 0.95 |
| 5-4 | redmine_id 보존 | 마이그레이션된 이슈 | redmine_id = 원본 Redmine ID |
| 5-5 | 부모-자식 연결 | parent_id 있는 이슈 | parent_id 정상 연결 |

---

## Phase 2 테스트 시나리오

### 시나리오 6: 코멘트

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 6-1 | 코멘트 추가 | notes="테스트 코멘트" | 201 + journal 생성 |
| 6-2 | 빈 코멘트 추가 시도 | notes="" | 422 |
| 6-3 | @멘션 포함 코멘트 | "@홍길동 확인 요청" | 201 + 홍길동에게 알림 발송 |
| 6-4 | 본인 코멘트 수정 | 본인 journal_id | 200 |
| 6-5 | 타인 코멘트 수정 시도 | 다른 사람의 journal_id (member 역할) | 403 |
| 6-6 | 코멘트 삭제 (manager) | project_manager 역할 | 200 |

### 시나리오 7: 파일 첨부

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 7-1 | 정상 파일 업로드 | 1MB PDF | 201 + attachment 반환 |
| 7-2 | 최대 크기 초과 | 21MB 파일 | 400 |
| 7-3 | 차단 확장자 업로드 시도 | .exe 파일 | 400 |
| 7-4 | 파일 다운로드 | 유효한 attachment_id | 200 + 파일 내용 |
| 7-5 | 파일 삭제 | attachment_id (본인 업로드) | 204 |
| 7-6 | 이슈당 50개 초과 | 51번째 업로드 | 400 |

### 시나리오 8: 알림

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 8-1 | 이슈 배정 알림 | assignee_id 변경 | 새 담당자 알림 1건 생성 |
| 8-2 | 본인 담당 이슈 알림 수신 안 함 | 본인이 배정 | 알림 0건 |
| 8-3 | 알림 목록 조회 | GET /v1/notifications | 200 + 본인 알림만 |
| 8-4 | 알림 읽음 처리 | PUT /v1/notifications/{id}/read | is_read=true |
| 8-5 | 전체 읽음 처리 | PUT /v1/notifications/read-all | 모든 알림 is_read=true |

---

## Phase 3 테스트 시나리오

### 시나리오 9: 타임 트래킹

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 9-1 | 시간 기록 추가 | hours=2.5, spent_on=오늘 | 201 |
| 9-2 | 0.1시간 입력 (최소 이하) | hours=0.1 | 400 |
| 9-3 | 25시간 입력 (최대 초과) | hours=25 | 400 |
| 9-4 | 미래 날짜 입력 | spent_on=내일 | 400 |
| 9-5 | 본인 기록 수정 | 본인 time_entry_id | 200 |
| 9-6 | 타인 기록 수정 시도 | 타인 time_entry_id (member) | 403 |
| 9-7 | 프로젝트 합산 조회 | GET /v1/projects/{id}/time-entries | 200 + 합산값 포함 |

---

## Phase 4 테스트 시나리오

### 시나리오 10: 분석 통합

| # | 시나리오 | 조건 | 기대 결과 |
|---|---|---|---|
| 10-1 | 이슈 완료 후 분석 즉시 반영 | issues 완료 → GET /v1/flow/stages | flow_stage=done 카운트 증가 |
| 10-2 | 새 이슈 생성 후 대시보드 반영 | POST /v1/issues → GET /v1/dashboard/summary | backlog_count 증가 |
| 10-3 | 기존 분석 API 정상 동작 | GET /v1/flow/stages | 200 (기존과 동일) |
| 10-4 | LLM 설명 신규 이슈 | GET /v1/flow/issue/{새이슈id}/explanation | 200 + explanation 반환 |

---

## 경계값 / 엣지 케이스 테스트

| # | 시나리오 | 기대 결과 |
|---|---|---|
| E-1 | subject 500자 입력 | 201 |
| E-2 | subject 501자 입력 | 422 |
| E-3 | description 빈 값 | 201 (선택 필드) |
| E-4 | 한글 이슈 제목 | 201 + 정상 저장/조회 |
| E-5 | 특수문자 제목 `#&<>"'` | 201 + XSS 이스케이프 확인 |
| E-6 | 동시 이슈 생성 (10개 동시) | 201 * 10, ID 충돌 없음 |
| E-7 | 비공개 이슈 viewer 조회 시도 | 404 (이슈 존재 여부도 노출 안 함) |
| E-8 | SQL Injection 시도 | `'; DROP TABLE issues;--` 입력 | 정상 저장 (이스케이프 처리) |
| E-9 | 매우 큰 offset | offset=1000000 | 200 + items=[] |
| E-10 | limit=0 | 200 + items=[] |

---

## 성능 테스트 기준

| 시나리오 | 목표 |
|---|---|
| 이슈 목록 조회 (1,000건) | p95 < 800ms |
| 이슈 상세 조회 | p95 < 500ms |
| 이슈 생성 | p95 < 300ms |
| 동시 사용자 50명 로그인 | 오류율 0% |
| 동시 사용자 50명 이슈 목록 조회 | p95 < 1000ms |
| 파일 업로드 10MB | p95 < 5000ms |

---

## 테스트 데이터 생성 스크립트 위치

```
backend/app/scripts/create_test_data.py
```

실행 후 생성되는 데이터:
- 사용자 4명 (admin/manager/member/viewer)
- 프로젝트 2개 (test-project, test-project-2)
- 이슈 100건 (다양한 상태/우선순위/담당자)
- 저널 200건
- 시간 기록 50건
