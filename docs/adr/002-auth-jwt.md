# ADR-002: 인증 방식 — JWT (이메일+비밀번호)

**날짜:** 2026-05-26  
**상태:** 확정

## 결정
JWT HS256 방식. Access Token 15분, Refresh Token 30일.

## 토큰 전략
- Access Token: 메모리 (localStorage 저장, HttpOnly 쿠키는 CORS 복잡도로 제외)
- Refresh Token: HttpOnly 쿠키 (`/v1/auth/refresh` 경로만 접근)
- Refresh Token은 DB `user_refresh_tokens` 테이블에 저장 (로그아웃 시 무효화)

## Access Token 페이로드
```json
{
  "sub": "user-uuid",
  "email": "user@company.com",
  "is_system_admin": false,
  "exp": 1234567890
}
```

## 근거
- 사내망 전용으로 HTTPS 없어도 내부에서는 허용 (운영 시 Nginx에서 HTTPS 권장)
- LDAP/AD 없으므로 자체 계정 관리
- Refresh Token DB 저장으로 강제 로그아웃 가능

## 보안 규칙
- 비밀번호: bcrypt cost factor 12
- 로그인 실패 5회 → 계정 15분 잠금
- Refresh Token 재사용 감지: 한 번 사용된 토큰 재사용 시 해당 사용자 전체 세션 무효화
