# ADR-003: 실시간 알림 — SSE (Server-Sent Events)

**날짜:** 2026-05-26  
**상태:** 확정

## 결정
실시간 알림은 WebSocket이 아닌 SSE(Server-Sent Events)로 구현한다.

## 근거
- 알림은 서버→클라이언트 단방향이므로 SSE로 충분
- WebSocket 대비 구현 단순, Nginx 프록시 설정 간단
- FastAPI에서 `StreamingResponse`로 네이티브 지원

## 구현 방식
```
GET /v1/notifications/stream
Authorization: Bearer {token}
Accept: text/event-stream

← 이벤트 발생 시:
data: {"type": "issue_assigned", "issue_id": 123, "message": "새 이슈가 배정되었습니다"}
```

## 대안 고려
- WebSocket: 양방향 통신 필요 시 (현재는 불필요)
- Polling: 5초마다 요청 → 100명 x 12req/min = 1200req/min. 불필요한 부하.
