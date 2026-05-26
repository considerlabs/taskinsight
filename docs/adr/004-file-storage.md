# ADR-004: 파일 첨부 저장 전략

**날짜:** 2026-05-26  
**상태:** 확정

## 결정
파일은 서버 로컬 디스크에 저장. S3 등 외부 스토리지 미사용.

## 디렉터리 구조
```
$UPLOAD_DIR/                  # 환경변수로 설정 (예: /data/taskinsight/uploads)
└── attachments/
    └── {year}/
        └── {month}/
            └── {uuid}.{ext}  # 원본 파일명 대신 UUID 사용 (경로 탐색 공격 방지)
```

## 보안 규칙
- 파일명 정규화: UUID로 저장, 원본 파일명은 DB에만 저장
- 확장자 화이트리스트: jpg, jpeg, png, gif, webp, pdf, doc, docx, xls, xlsx, ppt, pptx, txt, md, zip, tar.gz
- 실행 파일 금지: exe, sh, bat, ps1, py, js 등
- 최대 크기: 50MB
- 다운로드 시 `Content-Disposition: attachment; filename*=UTF-8''...` 헤더 설정
- 인증된 사용자 + 프로젝트 멤버만 다운로드 가능

## 근거
- 사내망 전용, 외부 스토리지 불필요
- 서버 디스크 용량으로 충분 (100명 x 50MB x 1000건 = ~5TB 최대)
- Docker volume으로 마운트하여 백업 용이
