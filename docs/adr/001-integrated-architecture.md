# ADR-001: 업무관리와 분석을 단일 시스템으로 통합

**날짜:** 2026-05-26  
**상태:** 확정

## 결정
업무관리(이슈 트래킹)와 SEI 분석 대시보드를 하나의 FastAPI 백엔드, 하나의 PostgreSQL 인스턴스에 통합한다.

## 근거
- Redmine sync 지연(최대 1시간) 없이 분석이 즉시 반영됨
- 단일 Docker Compose로 배포 단순화
- 100명 규모에서 마이크로서비스 오버엔지니어링

## 결과
- `issues` 테이블이 `fct_issue_snapshot` ETL의 주요 소스가 됨
- 이슈 저장 시 `background_tasks`로 ETL 부분 갱신 트리거
- 외부 Redmine 커넥터는 유지 (마이그레이션 및 병행 운영용)
