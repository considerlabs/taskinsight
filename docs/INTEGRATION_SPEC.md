# TaskInsight — 외부 연동 명세

---

## 1. Microsoft Teams — Incoming Webhook

### 1.1 설정 방법

1. Teams 채널 → `...` → 연결기 → Incoming Webhook
2. 이름: `TaskInsight 알림`, 아이콘 업로드 (선택)
3. 생성된 URL을 `.env`의 `TEAMS_WEBHOOK_URL`에 저장

### 1.2 페이로드 형식 (Adaptive Card)

```json
{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": [
          {
            "type": "TextBlock",
            "text": "🔔 이슈 배정",
            "weight": "Bolder",
            "size": "Medium"
          },
          {
            "type": "FactSet",
            "facts": [
              { "title": "이슈", "value": "#10729 결제 모듈 검수 대기" },
              { "title": "프로젝트", "value": "만나 플랫폼" },
              { "title": "담당자", "value": "홍길동" },
              { "title": "우선순위", "value": "높음" }
            ]
          }
        ],
        "actions": [
          {
            "type": "Action.OpenUrl",
            "title": "이슈 보기",
            "url": "http://taskinsight.internal/issues/10729"
          }
        ]
      }
    }
  ]
}
```

### 1.3 이벤트별 메시지 형식

| 이벤트 | 제목 | 본문 |
|---|---|---|
| 이슈 배정 | `🔔 이슈가 배정되었습니다` | 이슈 번호/제목/프로젝트/우선순위 |
| 상태 변경 | `📋 이슈 상태 변경` | 이슈 번호/제목/변경 전→후 |
| 코멘트 추가 | `💬 새 코멘트` | 이슈 번호/제목/코멘트 내용(최대 100자) |
| @멘션 | `📢 멘션되었습니다` | 이슈 번호/제목/멘션한 사람 |
| 기한 D-1 | `⏰ 기한 임박` | 이슈 번호/제목/기한일 |
| 이슈 완료 | `✅ 이슈 완료` | 이슈 번호/제목/소요일 |

### 1.4 구현 위치

```
backend/app/notifications/teams.py
```

```python
# 핵심 구현 패턴
import httpx
from app.config import settings

def send_teams_notification(payload: dict) -> bool:
    if not settings.teams_webhook_url:
        return False
    try:
        resp = httpx.post(
            settings.teams_webhook_url,
            json=payload,
            timeout=10.0
        )
        return resp.status_code == 200
    except Exception as e:
        logger.error("Teams 발송 실패: %s", e)
        return False
```

### 1.5 실패 처리

- 타임아웃: 10초
- 실패 시: 로그 기록 후 넘어감 (재시도 없음)
- 연속 3회 실패 시: 로그에 WARNING 레벨 기록

---

## 2. 이메일 (SMTP)

### 2.1 지원 SMTP 서버

| 서버 | HOST | PORT | TLS |
|---|---|---|---|
| Gmail | smtp.gmail.com | 587 | STARTTLS |
| Office 365 | smtp.office365.com | 587 | STARTTLS |
| 자체 SMTP | 환경변수 설정 | 환경변수 설정 | 선택 |

### 2.2 이메일 템플릿 (HTML)

**이슈 배정 알림:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: 'Pretendard', sans-serif; color: #1F2937; }
    .header { background: #2563EB; color: white; padding: 16px; }
    .content { padding: 24px; }
    .issue-box { background: #F3F4F6; border-radius: 8px; padding: 16px; margin: 16px 0; }
    .button { background: #2563EB; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; display: inline-block; }
  </style>
</head>
<body>
  <div class="header">
    <h2>🔔 TaskInsight — 이슈가 배정되었습니다</h2>
  </div>
  <div class="content">
    <p>안녕하세요, <strong>{{display_name}}</strong>님.</p>
    <p>새 이슈가 배정되었습니다.</p>
    <div class="issue-box">
      <p><strong>이슈:</strong> #{{issue_id}} {{subject}}</p>
      <p><strong>프로젝트:</strong> {{project_name}}</p>
      <p><strong>우선순위:</strong> {{priority_name}}</p>
      <p><strong>기한:</strong> {{due_date_or_미지정}}</p>
    </div>
    <a href="{{issue_url}}" class="button">이슈 확인하기</a>
    <p style="margin-top:24px; font-size:12px; color:#6B7280;">
      TaskInsight | 이 알림은 시스템에서 자동으로 발송됩니다.
    </p>
  </div>
</body>
</html>
```

### 2.3 이메일 템플릿 위치

```
backend/app/notifications/templates/
  assigned.html       ← 이슈 배정
  status_changed.html ← 상태 변경
  comment.html        ← 코멘트 추가
  mentioned.html      ← @멘션
  due_soon.html       ← 기한 임박
  completed.html      ← 완료
```

### 2.4 구현 위치

```
backend/app/notifications/email.py
```

```python
# 핵심 구현 패턴
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings

async def send_email_notification(to_email: str, subject: str, html_body: str) -> bool:
    message = MIMEMultipart("alternative")
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
            timeout=30,
        )
        return True
    except Exception as e:
        logger.error("이메일 발송 실패 to=%s: %s", to_email, e)
        return False
```

### 2.5 실패 처리

- 타임아웃: 30초
- 실패 시: 로그 기록 후 넘어감 (1회 재시도 후 포기)
- 이메일 발송 실패가 주요 동작 (이슈 저장 등)을 막지 않음

---

## 3. Ollama (LLM)

### 3.1 연결 설정

```python
OLLAMA_BASE_URL = "http://host.docker.internal:11434"  # Mac Studio 실행 시
OLLAMA_MODEL_TIMELINE = "qwen3.6:35b-a3b"
OLLAMA_MODEL_NARRATIVE = "qwen2.5-coder:14b"
```

### 3.2 호출 패턴 (변경 없음)

```python
# think:False 필수 — Qwen3 모델은 없으면 content 비어있음
resp = httpx.post(
    f"{settings.ollama_base_url}/api/chat",
    json={
        "model": settings.ollama_model_timeline,
        "messages": [...],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.3},
    },
    timeout=120,
)
```

### 3.3 장애 처리

- Ollama 미응답 시: HTTP 504 반환 (타임아웃 120초)
- 분석 기능 (LLM)은 업무관리 기능(이슈 CRUD)과 완전 독립 — Ollama 장애가 이슈 작성에 영향 없음

---

## 4. 연동 테스트 방법

```bash
# Teams Webhook 테스트
curl -X POST "$TEAMS_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"TaskInsight 연동 테스트 ✅"}]}}]}'

# SMTP 테스트
docker-compose exec backend python -c "
import asyncio
from app.notifications.email import send_email_notification
asyncio.run(send_email_notification(
    'admin@example.com',
    '테스트 이메일',
    '<h1>연동 테스트</h1>'
))
"

# Ollama 테스트
curl http://localhost:11434/api/tags | python3 -m json.tool
```
