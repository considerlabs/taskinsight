# TaskInsight — 보안 명세

---

## 1. 인증 흐름

```
[로그인]
사용자 → POST /v1/auth/login {email, password}
         ↓
         1. 이메일로 users 조회
         2. locked_until > NOW() → 423 반환
         3. bcrypt.verify(password, password_hash)
         4. 실패: login_fail_count++, 5회 → locked_until = NOW()+15분
         5. 성공: login_fail_count=0, last_login_at=NOW()
         6. Access Token(15분) 생성
         7. Refresh Token(30일) 생성 → SHA-256 해시 → DB 저장
         ↓
         Response: {access_token} + Set-Cookie: refresh_token (HttpOnly)

[API 호출]
사용자 → Authorization: Bearer {access_token}
         ↓
         1. JWT 서명 검증
         2. exp 확인
         3. sub(user_id)로 users 조회 → is_active 확인
         ↓
         current_user 주입

[토큰 갱신]
사용자 → POST /v1/auth/refresh (쿠키 자동 포함)
         ↓
         1. 쿠키에서 refresh_token 추출
         2. SHA-256 해시 → DB 조회
         3. used_at IS NOT NULL → 재사용 감지 → 해당 user 전체 세션 revoke → 401
         4. revoked = TRUE → 401
         5. expires_at < NOW() → 401
         6. used_at = NOW() 기록 + 새 Refresh Token 발급
         ↓
         Response: 새 access_token + Set-Cookie: 새 refresh_token
```

---

## 2. 권한 체크 패턴

### 백엔드 의존성

```python
# backend/app/auth/dependencies.py

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """JWT 검증 + 사용자 조회. 모든 인증 필요 엔드포인트에서 사용."""
    ...

async def require_system_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """시스템 관리자만 접근 허용."""
    if not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="시스템 관리자 권한이 필요합니다.")
    return current_user

def require_project_role(*roles: ProjectRole):
    """프로젝트 역할 기반 접근 제어 팩토리.
    
    사용 예:
        @router.put("/{project_id}")
        def update_project(
            project_id: int,
            current_user: User = Depends(require_project_role("manager")),
        ): ...
    """
    async def dependency(
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_system_admin:
            return current_user
        membership = db.execute(
            text("SELECT role FROM project_members WHERE project_id = :pid AND user_id = :uid"),
            {"pid": project_id, "uid": str(current_user.id)},
        ).fetchone()
        if not membership or membership.role not in roles:
            raise HTTPException(status_code=403, detail="이 작업에 대한 권한이 없습니다.")
        return current_user
    return dependency
```

### 데이터 접근 규칙 (서비스 레이어)

```python
# 이슈 조회 시 반드시 프로젝트 멤버십 확인
def get_issue(issue_id: int, current_user: User, db: Session) -> Issue:
    issue = db.execute(text("SELECT * FROM issues WHERE id = :id"), {"id": issue_id}).fetchone()
    if not issue:
        raise HTTPException(404)
    
    # 멤버십 확인
    if not current_user.is_system_admin:
        member = db.execute(
            text("SELECT 1 FROM project_members WHERE project_id = :pid AND user_id = :uid"),
            {"pid": issue.project_id, "uid": str(current_user.id)},
        ).fetchone()
        if not member:
            raise HTTPException(403)
    
    return issue
```

---

## 3. SQL 인젝션 방지

**규칙: 모든 DB 쿼리는 파라미터 바인딩 사용. f-string으로 사용자 입력 삽입 절대 금지.**

```python
# ✅ 올바른 방법
db.execute(
    text("SELECT * FROM issues WHERE project_id = :pid AND title ILIKE :q"),
    {"pid": project_id, "q": f"%{search_query}%"}
)

# ❌ 절대 금지
db.execute(text(f"SELECT * FROM issues WHERE title LIKE '%{search_query}%'"))
```

**예외:** 동적 ORDER BY 컬럼명은 화이트리스트로 검증 후 f-string 사용 허용.

```python
ALLOWED_SORT_COLUMNS = {"created_at", "updated_at", "priority", "due_date"}
if sort_by not in ALLOWED_SORT_COLUMNS:
    raise HTTPException(400, "유효하지 않은 정렬 기준입니다.")
# 이 경우에만 f-string 허용:
db.execute(text(f"SELECT * FROM issues ORDER BY {sort_by} {order_dir}"), params)
```

---

## 4. 파일 업로드 보안

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain", "text/markdown",
    "application/zip",
    "application/x-gzip",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

def validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"허용되지 않는 파일 형식: {file.content_type}")
    # 실제 파일 헤더 검사 (MIME 스푸핑 방지)
    header = await file.read(512)
    await file.seek(0)
    detected = magic.from_buffer(header, mime=True)
    if detected not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, "파일 형식이 확장자와 일치하지 않습니다.")

def safe_stored_path(upload_dir: str, attachment_id: str, filename: str) -> str:
    """경로 탐색 공격 방지: UUID 기반 저장 경로."""
    ext = Path(filename).suffix.lower()
    year_month = datetime.now().strftime("%Y/%m")
    return os.path.join(upload_dir, "attachments", year_month, f"{attachment_id}{ext}")
```

---

## 5. CORS 설정

사내망 전용이므로 `localhost`와 실제 서버 IP만 허용.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        f"http://{settings.server_host}",       # 사내 서버 IP
        f"http://{settings.server_hostname}",   # 사내 서버 호스트명
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## 6. 속도 제한 (Rate Limiting)

Redis 기반.

| 엔드포인트 | 제한 |
|---|---|
| `POST /v1/auth/login` | IP당 10회/분 |
| `POST /v1/auth/refresh` | 사용자당 30회/분 |
| `POST /v1/issues/{id}/attachments` | 사용자당 10회/분 |
| 일반 API | 사용자당 300회/분 |

---

## 7. 감사 로그

모든 데이터 변경은 `issue_journals`에 자동 기록. 추가로 다음 이벤트는 별도 로그:

| 이벤트 | 기록 방법 |
|---|---|
| 로그인 성공/실패 | Python logging (INFO/WARNING) |
| 사용자 계정 변경 | Python logging (INFO) |
| 프로젝트 설정 변경 | Python logging (INFO) |
| 파일 다운로드 | Python logging (INFO) |

---

## 8. 환경변수 (`.env`)

```bash
# DB
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=taskinsight
POSTGRES_USER=taskinsight
POSTGRES_PASSWORD=<strong_password>

# JWT
JWT_SECRET_KEY=<64자 이상 랜덤 문자열>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Redis
REDIS_URL=redis://localhost:6379/0

# 파일 업로드
UPLOAD_DIR=/data/taskinsight/uploads
MAX_FILE_SIZE_MB=20

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_TIMELINE=qwen3.6:35b-a3b
OLLAMA_MODEL_NARRATIVE=qwen2.5-coder:14b

# 서버 정보 (CORS용)
SERVER_HOST=192.168.1.100
SERVER_HOSTNAME=taskinsight.company.local

# Redmine (기존 유지)
REDMINE_BASE_URL=http://redmine.mannaplanet.co.kr:5555/redmine
REDMINE_API_KEY=<redacted>
```
