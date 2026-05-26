# TaskInsight — Redmine 마이그레이션 계획

---

## 1. 마이그레이션 개요

| 항목 | 내용 |
|---|---|
| 방식 | 일회성 D-day 전환 (점진적 병행 없음) |
| 소요 예상 시간 | 1~2시간 (데이터 규모: 이슈 16,111건, 저널 97,000건 기준) |
| 롤백 가능 여부 | D-day 이전까지 언제든 롤백 가능 (`raw_redmine_*` 데이터 보존) |
| 데이터 손실 | 없음. Redmine 원본 ID(`redmine_id`) 보존. |
| 서비스 중단 | 마이그레이션 실행 중 약 30분 (사전 공지 필요) |

---

## 2. D-day 전 준비 (1주 전)

```bash
# 1. 스테이징 환경에서 마이그레이션 리허설
# 스테이징 = 프로덕션과 동일한 raw_redmine_* 데이터 복사본

# 2. 마이그레이션 스크립트 검증
docker-compose exec backend python -m app.scripts.migrate_from_redmine
# → 오류 없이 완료 확인
# → 이슈 건수 손실 < 5% 확인
# → 저널 연결 정상 확인

# 3. 사용자 목록 검토
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT id, email, display_name, redmine_id FROM users WHERE redmine_id IS NOT NULL ORDER BY id;
"
# → 이메일이 없는 계정 수동 설정 필요 (format: user_{redmine_id}@redmine.local)
```

---

## 3. D-day 전날 (준비)

```bash
# 1. 최종 Redmine 동기화 (가능한 최신 데이터 수집)
docker-compose exec backend python -c "
from app.collector.redmine_collector import sync_redmine
from app.db import SessionLocal
db = SessionLocal()
sync_redmine(db)
db.close()
"

# 2. ETL 실행 (분석 데이터 최신화)
curl -X POST http://localhost/admin/etl

# 3. 현재 상태 스냅샷
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT
  (SELECT COUNT(*) FROM raw_redmine_issues) AS redmine_issues,
  (SELECT COUNT(*) FROM raw_redmine_journals) AS redmine_journals,
  (SELECT COUNT(*) FROM raw_redmine_users) AS redmine_users,
  (SELECT COUNT(*) FROM raw_redmine_projects) AS redmine_projects;
"

# 4. DB 백업
docker-compose exec db pg_dump -U taskinsight taskinsight | \
  gzip > /backup/taskinsight_preD_$(date +%Y%m%d).sql.gz
```

---

## 4. D-day 실행 절차

### 4.1 사전 공지

팀원에게 최소 1일 전 공지:
```
"TaskInsight 시스템 전환 작업으로 [날짜] [시간] ~ [시간] 동안
서비스가 일시 중단됩니다.
전환 후 Redmine 대신 TaskInsight(http://taskinsight.internal)를
업무관리 도구로 사용하게 됩니다."
```

### 4.2 실행 단계

```bash
# Step 1: 서비스 중단 (유지보수 페이지 표시)
# nginx.conf에 503 유지보수 모드 추가 후:
docker-compose restart nginx

# Step 2: Alembic 마이그레이션 (0004~0007)
docker-compose exec backend alembic upgrade head

# Step 3: 시드 데이터
docker-compose exec backend python -m app.scripts.seed

# Step 4: 마이그레이션 실행
docker-compose exec backend python -m app.scripts.migrate_from_redmine
# → 완료까지 약 30~60분

# Step 5: 검증
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT
  (SELECT COUNT(*) FROM users WHERE redmine_id IS NOT NULL) AS users,
  (SELECT COUNT(*) FROM projects WHERE redmine_id IS NOT NULL) AS projects,
  (SELECT COUNT(*) FROM issues WHERE redmine_id IS NOT NULL) AS issues,
  (SELECT COUNT(*) FROM issue_journals WHERE redmine_id IS NOT NULL) AS journals;
"

# Step 6: 이슈 건수 검증
docker-compose exec backend python -c "
from app.db import SessionLocal
from sqlalchemy import text
db = SessionLocal()
redmine = db.execute(text('SELECT COUNT(*) FROM raw_redmine_issues')).scalar()
ti = db.execute(text('SELECT COUNT(*) FROM issues WHERE redmine_id IS NOT NULL')).scalar()
ratio = ti / redmine * 100
print(f'Redmine: {redmine:,}건 → TaskInsight: {ti:,}건 ({ratio:.1f}%)')
if ratio < 95:
    print('⚠️  경고: 5% 이상 손실!')
else:
    print('✅ 검증 통과')
db.close()
"

# Step 7: 서비스 재개
# nginx.conf 유지보수 모드 제거 후:
docker-compose restart nginx

# Step 8: 사용자 임시 비밀번호 재설정 안내 이메일 발송
docker-compose exec backend python -m app.scripts.send_password_reset_emails
```

### 4.3 롤백 절차 (문제 발생 시)

```bash
# 마이그레이션 실패 시 롤백
docker-compose exec backend alembic downgrade 0003_mvp

# 백업에서 복구
gunzip -c /backup/taskinsight_preD_$(date +%Y%m%d).sql.gz | \
  docker-compose exec -T db psql -U taskinsight -d taskinsight

# Redmine 계속 사용 가능 (raw_redmine_* 데이터 손상 없음)
```

---

## 5. D-day 이후 조치

### 5.1 즉시 (당일)

```bash
# 관리자 계정 비밀번호 변경
# → admin 계정으로 로그인 후 즉시 비밀번호 변경

# Redmine 연동 설정 변경 (커넥터 비활성화 예정 알림)
# Settings 화면에서 Redmine 연동 상태 확인
```

### 5.2 1주 내

- 팀원 전원 TaskInsight 로그인 확인
- 임시 비밀번호 변경 완료 확인
- 기존 이슈가 정상적으로 이전됐는지 샘플 확인 (상위 10개 이슈 수동 검증)
- 알림 발송 정상 동작 확인

### 5.3 1개월 내 (Phase 4 완료 후)

```bash
# Redmine sync 비활성화 (connector_instance 비활성화)
docker-compose exec db psql -U taskinsight -d taskinsight -c "
UPDATE connector_instance SET is_active = FALSE WHERE connector_type = 'redmine';
"

# raw_redmine_* 테이블 아카이브 (보존, 접근만 제한)
# → 향후 6개월 보관 후 삭제 검토
```

---

## 6. 데이터 매핑 테이블

### Redmine 상태 → TaskInsight 상태

| Redmine status_id | Redmine 이름 | TaskInsight status_id | TaskInsight 이름 |
|---|---|---|---|
| 1 | New | 1 | 신규 |
| 2 | In Progress | 2 | 진행 중 |
| 3 | 검수 요청 | 3 | 검수 요청 |
| 4 | 검수 중 | 4 | 검수 중 |
| 5 | Closed | 5 | 완료 |
| 6 | Rejected | 6 | 반려 |
| 8 | Rework | 8 | 재작업 |
| 9, 16 | Blocked | 7 | 보류 |
| 10, 11, 13, 23, 25 | (기타 완료) | 5 | 완료 |
| 12 | (진행 중 변형) | 2 | 진행 중 |
| 14, 17, 18, 19, 20, 24 | (검수 변형) | 4 | 검수 중 |
| 21, 22 | (재작업 변형) | 8 | 재작업 |

### Redmine 우선순위 → TaskInsight 우선순위

| Redmine priority_id | TaskInsight priority_id |
|---|---|
| 1 (Low) | 1 (낮음) |
| 2 (Normal) | 2 (보통) |
| 3 (High) | 3 (높음) |
| 4 (Urgent) | 4 (긴급) |
| 5 (Immediate) | 4 (긴급) |

---

## 7. 마이그레이션 후 예상 데이터 현황

| 테이블 | 예상 건수 | 비고 |
|---|---|---|
| users | ~85건 | Redmine 사용자 전체 |
| projects | ~4건 | 기존 Redmine 프로젝트 |
| issues | ~16,000건 | 일부 프로젝트 매핑 누락 가능 |
| issue_journals | ~97,000건 | 저널 수집 완료 기준 |
| time_entries | ~20건 | Redmine 공수 기록 |
| custom_field_values | 수천 건 | 커스텀 필드 값 |
