# TaskInsight — 로깅 & 모니터링 정책

---

## 1. 로그 정책

### 1.1 로그 레벨 기준

| 레벨 | 사용 기준 | 예시 |
|---|---|---|
| DEBUG | 개발 환경 상세 디버그 | SQL 쿼리, 함수 진입/종료 |
| INFO | 정상 동작 기록 | 이슈 생성, 로그인 성공, ETL 완료 |
| WARNING | 주의 필요하지만 서비스 영향 없음 | 알림 발송 실패, Ollama 지연 |
| ERROR | 에러 발생 (서비스 부분 영향) | DB 쿼리 실패, API 오류 |
| CRITICAL | 서비스 중단 수준 | DB 연결 불가, 스토리지 가득 참 |

### 1.2 로그 포맷

**개발 환경:**
```
2026-05-26 10:30:00 INFO     app.api.routers.issues  POST /v1/issues 201 (45ms) user_id=1
```

**프로덕션 환경 (JSON):**
```json
{
  "timestamp": "2026-05-26T10:30:00.123Z",
  "level": "INFO",
  "logger": "app.api.routers.issues",
  "message": "이슈 생성",
  "method": "POST",
  "path": "/v1/issues",
  "status_code": 201,
  "duration_ms": 45,
  "user_id": 1,
  "issue_id": 12345
}
```

### 1.3 반드시 로깅해야 할 이벤트

```python
# INFO 레벨
logger.info("이슈 생성: issue_id=%d user_id=%d project_id=%d", issue.id, user.id, issue.project_id)
logger.info("이슈 상태 변경: issue_id=%d %s→%s user_id=%d", issue.id, old_status, new_status, user.id)
logger.info("로그인 성공: user_id=%d email=%s ip=%s", user.id, user.email, client_ip)
logger.info("로그인 실패: email=%s ip=%s", email, client_ip)
logger.info("파일 업로드: issue_id=%d filename=%s size=%d user_id=%d", ...)
logger.info("ETL 완료: duration=%.1fs issues=%d", duration, count)
logger.info("LLM 설명 생성: issue_id=%d model=%s duration=%.1fs", ...)

# WARNING 레벨
logger.warning("알림 발송 실패: user_id=%d event=%s error=%s", ...)
logger.warning("Ollama 응답 지연: issue_id=%d duration=%.1fs", ...)
logger.warning("계정 잠금: email=%s fail_count=%d", ...)

# ERROR 레벨
logger.error("이슈 저장 실패: error=%s", exc, exc_info=True)
logger.error("DB 쿼리 오류: query=%s error=%s", query, exc, exc_info=True)
```

### 1.4 민감 정보 로깅 금지

```python
# 절대 로그에 기록하면 안 되는 것
# - 비밀번호 (평문/해시 모두)
# - JWT 토큰 내용
# - API 키
# - 개인 이메일 내용
# - Redmine API 키
```

---

## 2. 로그 저장 및 조회

### 2.1 Docker 로그 설정

```yaml
# docker-compose.yml에 추가
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

### 2.2 로그 조회 명령

```bash
# 실시간 로그
docker-compose logs -f backend

# 최근 100줄
docker-compose logs --tail=100 backend

# 시간 범위 필터
docker-compose logs --since="2026-05-26T09:00:00" --until="2026-05-26T10:00:00" backend

# 에러만 필터
docker-compose logs backend 2>&1 | grep "ERROR\|CRITICAL"

# 특정 이슈 관련 로그
docker-compose logs backend 2>&1 | grep "issue_id=10729"
```

### 2.3 로그 보관

```bash
# 로그 파일 수동 아카이브 (월별)
docker-compose logs --since="2026-05-01" --until="2026-05-31" backend > \
  /backup/logs/backend_2026-05.log
gzip /backup/logs/backend_2026-05.log
```

---

## 3. 헬스체크 & 가용성 모니터링

### 3.1 헬스체크 엔드포인트

```python
# GET /health
{
  "status": "ok",
  "version": "0.2.0",
  "db": "ok",           # DB 연결 확인
  "redis": "ok",        # Redis 연결 확인
  "ollama": "ok|unavailable",  # Ollama는 경고만 (선택적)
  "uptime_seconds": 86400
}
```

### 3.2 자동 헬스체크 스크립트

```bash
#!/bin/bash
# /usr/local/bin/taskinsight-healthcheck.sh
# cron: */5 * * * * (5분마다 실행)

HEALTH_URL="http://localhost/health"
TEAMS_WEBHOOK="$TEAMS_WEBHOOK_URL"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$response" != "200" ]; then
  curl -X POST "$TEAMS_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"message\",\"attachments\":[{\"contentType\":\"application/vnd.microsoft.card.adaptive\",\"content\":{\"type\":\"AdaptiveCard\",\"version\":\"1.4\",\"body\":[{\"type\":\"TextBlock\",\"text\":\"🚨 TaskInsight 헬스체크 실패! HTTP=$response\",\"color\":\"attention\"}]}}]}"
fi
```

### 3.3 모니터링 지표 (수동 확인용)

```bash
# DB 활성 연결 수
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"

# 최근 1시간 슬로우 쿼리 (5초 이상)
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 5000
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# 테이블별 크기
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT relname AS table, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
"

# Redis 메모리
docker-compose exec redis redis-cli info memory | grep used_memory_human

# 디스크 사용량
df -h
docker system df
```

---

## 4. 알림 정책

### 4.1 시스템 알림 수신자

system_admin 이메일로 발송:

| 상황 | 알림 채널 |
|---|---|
| 헬스체크 실패 | Teams + 이메일 |
| DB 연결 실패 | Teams + 이메일 |
| 디스크 90% 초과 | Teams + 이메일 |
| 야간 백업 실패 | 이메일 |
| ETL 실패 | 이메일 |
| 마이그레이션 스크립트 오류 | 이메일 |

### 4.2 오류 임계값

| 오류 유형 | 임계값 | 알림 |
|---|---|---|
| 5xx 응답 | 분당 10회 이상 | WARNING |
| DB 쿼리 타임아웃 | 5초 이상 | WARNING |
| LLM 응답 없음 | 120초 | WARNING (서비스 영향 없음) |
| 파일 업로드 실패 | 연속 5회 | ERROR |

---

## 5. 감사 로그 (Audit Log)

감사 로그는 `issue_journals` 테이블이 담당합니다 (별도 감사 테이블 없음).

모든 이슈 변경 → `issue_journals` + `issue_journal_details`에 영구 저장.

**조회 예시:**
```sql
-- 특정 이슈의 전체 변경 이력
SELECT j.created_at, u.display_name, j.notes, jd.prop_key, jd.old_value, jd.new_value
FROM issue_journals j
JOIN users u ON j.user_id = u.id
LEFT JOIN issue_journal_details jd ON jd.journal_id = j.id
WHERE j.issue_id = 10729
ORDER BY j.created_at;

-- 오늘 상태 변경된 이슈 목록
SELECT DISTINCT i.id, i.subject, jd.old_value, jd.new_value
FROM issues i
JOIN issue_journals j ON j.issue_id = i.id
JOIN issue_journal_details jd ON jd.journal_id = j.id
WHERE jd.prop_key = 'status_id'
  AND j.created_at >= CURRENT_DATE;
```
