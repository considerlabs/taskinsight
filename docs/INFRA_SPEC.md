# TaskInsight — 배포/운영 문서

---

## 1. 서버 요구사항

| 항목 | 최소 사양 | 권장 사양 |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 4코어 | 8코어 |
| RAM | 16GB | 32GB (Ollama LLM 포함 시) |
| 스토리지 | SSD 200GB | SSD 500GB |
| 네트워크 | 사내망 고정 IP | 사내망 고정 IP |
| Docker | 24.0+ | 24.0+ |
| Docker Compose | 2.20+ | 2.20+ |

**Ollama 별도 실행 시:** Ollama는 Mac Studio에서 실행, Docker Compose에서 `OLLAMA_BASE_URL=http://mac-studio-ip:11434` 로 연결.

---

## 2. 초기 설치 절차

```bash
# 1. Docker 설치
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 레포지토리 클론
git clone https://github.com/considerlabs/taskinsight.git
cd taskinsight

# 3. 환경 변수 설정
cp .env.example .env
nano .env  # 값 채우기

# 4. 컨테이너 빌드 & 기동
docker-compose build
docker-compose up -d

# 5. DB 마이그레이션
docker-compose exec backend alembic upgrade head

# 6. 초기 데이터 (이슈 상태/우선순위/관리자 계정)
docker-compose exec backend python -m app.scripts.seed

# 7. (D-day) Redmine 마이그레이션
docker-compose exec backend python -m app.scripts.migrate_from_redmine

# 8. 상태 확인
docker-compose ps
curl http://localhost/health
```

---

## 3. 환경변수 필수 항목 체크리스트

```bash
# .env 설정 전 확인 필수
POSTGRES_PASSWORD     # 강력한 비밀번호 (20자 이상 권장)
JWT_SECRET            # openssl rand -hex 32 으로 생성
ADMIN_EMAIL           # 최초 관리자 이메일
ADMIN_PASSWORD        # 최초 관리자 비밀번호 (로그인 후 즉시 변경)
SMTP_HOST             # 이메일 발송용 SMTP 서버
SMTP_USER             # SMTP 계정
SMTP_PASSWORD         # SMTP 비밀번호
TEAMS_WEBHOOK_URL     # Teams 채널 Incoming Webhook URL
OLLAMA_BASE_URL       # Ollama 서버 주소
APP_BASE_URL          # 서버 접속 URL (예: http://192.168.1.100)
FRONTEND_URL          # 프론트엔드 URL (동일하거나 다른 포트)
```

---

## 4. 서비스 포트 구성

| 서비스 | 내부 포트 | 외부 포트 | 설명 |
|---|---|---|---|
| nginx | 80, 443 | 80, 443 | 진입점 |
| frontend | 3000 | (nginx 통해 접근) | Next.js |
| backend | 8000 | (nginx 통해 접근) | FastAPI |
| postgres | 5432 | 5433 | DB (외부 직접 접근 차단 권장) |
| redis | 6379 | (내부만) | 캐시 (외부 노출 금지) |

---

## 5. 일상적인 운영 명령

```bash
# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f backend      # 실시간 백엔드 로그
docker-compose logs -f frontend
docker-compose logs --tail=100 backend  # 최근 100줄

# 서비스 재시작
docker-compose restart backend
docker-compose restart frontend

# 전체 재시작 (DB는 유지)
docker-compose stop backend frontend nginx
docker-compose start backend frontend nginx

# 헬스체크
curl http://localhost/health

# DB 접속
docker-compose exec db psql -U taskinsight -d taskinsight

# 수동 배치 실행
docker-compose exec backend python -c "
from app.scheduler import run_nightly_batch
run_nightly_batch()
"
```

---

## 6. 업데이트 배포 절차

```bash
# 1. 코드 업데이트
git pull origin main

# 2. 이미지 재빌드
docker-compose build backend frontend

# 3. 마이그레이션 (있을 경우)
docker-compose exec backend alembic upgrade head

# 4. 무중단 재시작 (백엔드 → 프론트엔드 순서)
docker-compose up -d --no-deps backend
sleep 10
docker-compose up -d --no-deps frontend

# 5. 상태 확인
docker-compose ps
curl http://localhost/health
```

---

## 7. 백업 및 복구

```bash
# DB 백업
docker-compose exec db pg_dump -U taskinsight taskinsight | \
  gzip > /backup/taskinsight_$(date +%Y%m%d_%H%M%S).sql.gz

# 파일 업로드 백업
docker run --rm \
  -v taskinsight_uploads:/data \
  -v /backup:/backup \
  alpine tar czf /backup/uploads_$(date +%Y%m%d).tar.gz /data

# DB 복구
gunzip -c /backup/taskinsight_20260526.sql.gz | \
  docker-compose exec -T db psql -U taskinsight -d taskinsight

# crontab 설정 (매일 새벽 3시 백업)
# 0 3 * * * /path/to/backup.sh >> /var/log/taskinsight_backup.log 2>&1
```

---

## 8. 장애 대응 절차

### 8.1 서비스 응답 없음

```bash
# 1. 컨테이너 상태 확인
docker-compose ps

# 2. 로그 확인
docker-compose logs --tail=50 backend

# 3. 재시작
docker-compose restart backend

# 4. DB 연결 확인
docker-compose exec backend python -c "
from app.db import SessionLocal
from sqlalchemy import text
db = SessionLocal()
print(db.execute(text('SELECT 1')).scalar())
db.close()
"
```

### 8.2 DB 연결 실패

```bash
# DB 컨테이너 상태 확인
docker-compose ps db
docker-compose logs db

# DB 재시작
docker-compose restart db
# DB 기동 후 30초 대기 후 백엔드 재시작
sleep 30
docker-compose restart backend
```

### 8.3 디스크 용량 부족

```bash
# 용량 확인
df -h
docker system df

# 오래된 Docker 이미지/컨테이너 정리
docker system prune -f

# 오래된 백업 삭제 (30일 이상)
find /backup -name "*.gz" -mtime +30 -delete

# 오래된 알림 정리 (90일 이상 읽은 알림)
docker-compose exec backend python -c "
from app.db import SessionLocal
from sqlalchemy import text
db = SessionLocal()
db.execute(text(\"DELETE FROM notifications WHERE is_read=true AND created_at < NOW()-interval '90 days'\"))
db.commit()
db.close()
print('완료')
"
```

---

## 9. 모니터링 접근 방법

```bash
# 실시간 리소스 사용량
docker stats

# 백엔드 메트릭 (FastAPI 기본)
curl http://localhost/health

# DB 슬로우 쿼리 확인
docker-compose exec db psql -U taskinsight -d taskinsight -c "
SELECT pid, now()-pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now()-pg_stat_activity.query_start) > interval '5 seconds';
"
```

---

## 10. SSL/TLS 설정 (HTTPS)

```bash
# Let's Encrypt 사용 시 (사내 DNS가 외부 접근 가능한 경우)
# certbot certonly --standalone -d your-domain.com
# 인증서를 ./certs/ 에 복사 후 nginx.conf HTTPS 블록 주석 해제

# 자체 서명 인증서 (내부망)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -subj "/CN=taskinsight.internal"

# nginx.conf의 HTTPS 서버 블록 주석 해제 후 재시작
docker-compose restart nginx
```
