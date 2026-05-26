# TaskInsight — 릴리즈 체크리스트

> 각 Phase 완료 후 아래 체크리스트 **전체 통과** 시 운영 투입.
> 통과 못 한 항목은 투입 전 반드시 해결.

---

## Phase 1 — 기반 (인증 + 이슈 CRUD)

### 코드 품질
- [ ] `docker-compose build` 오류 없음
- [ ] TypeScript 컴파일 오류 0개 (`npm run build`)
- [ ] Python 타입 오류 없음 (mypy 또는 pyright)
- [ ] 불필요한 `print()`, `console.log()` 제거
- [ ] 환경변수 하드코딩 없음 (코드 전체 grep)

### DB
- [ ] `alembic upgrade head` 오류 없음 (신규 DB)
- [ ] `alembic downgrade -1` 후 `upgrade head` 재실행 정상
- [ ] seed.py 실행 후 이슈 상태 8개, 우선순위 4개 확인
- [ ] 관리자 계정 로그인 정상

### 기능 테스트 (TEST_SCENARIOS.md 참고)
- [ ] 시나리오 1 (로그인) — 1-1 ~ 1-10 전부 통과
- [ ] 시나리오 2 (권한) — 2-1 ~ 2-7 전부 통과
- [ ] 시나리오 3 (이슈 CRUD) — 3-1 ~ 3-13 전부 통과
- [ ] 시나리오 4 (저널) — 4-1 ~ 4-4 전부 통과
- [ ] 경계값 테스트 — E-1 ~ E-10 전부 통과

### 마이그레이션
- [ ] 스테이징 환경에서 migrate_from_redmine.py 성공 실행
- [ ] 이슈 건수 검증: ti_issues ≥ raw_redmine_issues × 95%
- [ ] 부모-자식 연결 정상
- [ ] 저널 연결 정상

### 보안
- [ ] JWT_SECRET 설정됨 (기본값 아님)
- [ ] ADMIN_PASSWORD 기본값 아님
- [ ] POSTGRES_PASSWORD 기본값 아님
- [ ] CORS 설정: APP_BASE_URL만 허용
- [ ] 파일 업로드: .exe 차단 확인
- [ ] SQL Injection 테스트: E-8 통과

### 프론트엔드
- [ ] 비로그인 상태에서 `/issues` 접근 시 `/login` redirect
- [ ] 로그인 성공 후 홈 페이지 로딩
- [ ] viewer 역할로 이슈 생성 버튼 숨김
- [ ] 401 응답 시 자동 로그아웃 + redirect

### 배포 환경
- [ ] `docker-compose ps` 모든 컨테이너 Up
- [ ] `curl http://localhost/health` → `{"status":"ok"}`
- [ ] Nginx 80 포트 정상 응답
- [ ] DB 헬스체크 통과
- [ ] Redis 헬스체크 통과

---

## Phase 2 — 협업 (코멘트 + 파일 + 알림)

### Phase 1 체크리스트 전부 재확인 (기존 기능 회귀 없음)

### 기능 테스트
- [ ] 시나리오 6 (코멘트) — 6-1 ~ 6-6 전부 통과
- [ ] 시나리오 7 (파일 첨부) — 7-1 ~ 7-6 전부 통과
- [ ] 시나리오 8 (알림) — 8-1 ~ 8-5 전부 통과

### 알림
- [ ] Teams Webhook URL 설정됨
- [ ] Teams 테스트 메시지 발송 성공
- [ ] SMTP 설정됨 + 테스트 이메일 발송 성공
- [ ] 이슈 배정 시 담당자 Teams 알림 수신 확인
- [ ] 이슈 배정 시 담당자 이메일 수신 확인
- [ ] 본인 배정 시 알림 미발송 확인

### 파일
- [ ] 20MB 이하 파일 업로드/다운로드 정상
- [ ] 21MB 파일 400 오류
- [ ] .exe 업로드 400 오류
- [ ] Docker volume 마운트 확인: 재시작 후 파일 유지

---

## Phase 3 — 심화 (타임 트래킹 + 커스텀 필드)

### Phase 1~2 체크리스트 전부 재확인

### 기능 테스트
- [ ] 시나리오 9 (타임 트래킹) — 9-1 ~ 9-7 전부 통과

### 타임 트래킹
- [ ] 프로젝트 합산 조회 정상 (이슈별 합계 + 전체 합계)
- [ ] 기한 D-1 알림 배치 스케줄러 등록 확인 (`docker-compose logs backend | grep scheduler`)

---

## Phase 4 — 분석 통합

### Phase 1~3 체크리스트 전부 재확인

### 기능 테스트
- [ ] 시나리오 10 (분석 통합) — 10-1 ~ 10-4 전부 통과

### 분석 기능
- [ ] `/v1/flow/stages` 정상 응답
- [ ] `/v1/dashboard/summary` 정상 응답
- [ ] `/v1/reports/weekly/generate` 정상 응답
- [ ] 새 이슈 생성 후 `/v1/flow/stages` 카운트 변화 확인

### Redmine 연동 종료
- [ ] connector_instance is_active = FALSE 확인
- [ ] Redmine sync 스케줄러 비활성화 확인
- [ ] 기존 `/v1/connectors/sync` 호출 시 "비활성화됨" 응답

---

## D-day 마이그레이션 체크리스트

### 실행 전
- [ ] 팀 공지 완료 (최소 1일 전)
- [ ] 스테이징 마이그레이션 성공 확인
- [ ] DB 백업 완료 (`taskinsight_preD_날짜.sql.gz` 존재)
- [ ] 최신 Redmine 동기화 완료
- [ ] 유지보수 페이지 준비

### 실행 중
- [ ] Alembic 마이그레이션 오류 없음
- [ ] seed.py 실행 완료
- [ ] migrate_from_redmine.py 완료 + 건수 검증 통과
- [ ] 샘플 이슈 10개 수동 확인 (제목/상태/담당자 일치)

### 실행 후
- [ ] 서비스 정상 응답 (`/health` = ok)
- [ ] 관리자 로그인 성공
- [ ] 팀원 임시 비밀번호 변경 완료 안내
- [ ] Redmine 접속 제한 공지 (1주 후 읽기 전용 전환 예정)

---

## 성능 체크 (모든 Phase 공통)

```bash
# 이슈 목록 API 응답 시간 측정
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost/v1/issues?limit=50" > /dev/null

# 목표: p95 < 800ms (개인 PC에서 측정 시 참고값)
# 실제 측정: 동시 사용자 50명 부하 테스트 필요
```

| API | 목표 | 확인 결과 |
|---|---|---|
| GET /v1/issues (50건) | < 800ms | |
| GET /v1/issues/{id} | < 500ms | |
| POST /v1/issues | < 300ms | |
| GET /v1/dashboard/summary | < 1500ms | |
