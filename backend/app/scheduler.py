"""APScheduler — 새벽 2시 LLM 배치 + ETL 자동 연계."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.db import SessionLocal

log = logging.getLogger(__name__)


def _get_active_connector_config() -> dict | None:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT config FROM connector_instance WHERE is_active = TRUE ORDER BY id LIMIT 1")
        ).fetchone()
        return row.config if row else None
    finally:
        db.close()


def run_nightly_etl() -> None:
    """매일 새벽 2시: Redmine sync → ETL → LLM 배치 (위험점수 상위 20건)."""
    log.info("야간 배치 시작")
    config = _get_active_connector_config()
    if not config:
        log.warning("활성 connector_instance 없음 — 배치 건너뜀")
        return

    db = SessionLocal()
    try:
        from app.collector.redmine_collector import sync_redmine
        from app.etl.populate import run_etl
        from app.narrator.issue_explainer import explain_issue

        # 1) Redmine sync
        sync_result = sync_redmine(config, db)
        log.info("Sync 완료: %s", sync_result)

        # 2) ETL
        etl_result = run_etl(db)
        log.info("ETL 완료: %s", etl_result)

        # 3) 위험점수 상위 20건 LLM 설명 사전 생성
        top20 = db.execute(text("""
            SELECT s.issue_id
            FROM fct_issue_snapshot s
            LEFT JOIN fct_issue_explanation e ON e.issue_id = s.issue_id
            WHERE s.flow_stage NOT IN ('done')
              AND (e.issue_id IS NULL OR e.is_stale = TRUE)
            ORDER BY s.risk_score DESC NULLS LAST
            LIMIT 20
        """)).fetchall()

        for row in top20:
            try:
                explain_issue(row.issue_id, db)
                log.info("LLM 설명 생성: issue_id=%s", row.issue_id)
            except Exception as e:
                log.warning("LLM 설명 실패 issue_id=%s: %s", row.issue_id, e)

        log.info("야간 배치 완료 — LLM 생성 %d건", len(top20))

    except Exception as e:
        log.error("야간 배치 오류: %s", e, exc_info=True)
    finally:
        db.close()


def run_etl_only() -> None:
    """sync 완료 후 ETL만 실행 (callback용)."""
    log.info("ETL 트리거")
    db = SessionLocal()
    try:
        from app.etl.populate import run_etl
        result = run_etl(db)
        log.info("ETL 완료: %s", result)
    except Exception as e:
        log.error("ETL 오류: %s", e, exc_info=True)
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    # 매일 새벽 2시 — Redmine sync + ETL + LLM 배치
    scheduler.add_job(
        run_nightly_etl,
        trigger=CronTrigger(hour=2, minute=0),
        id="nightly_etl",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    return scheduler


_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


def start_scheduler() -> None:
    s = get_scheduler()
    if not s.running:
        s.start()
        log.info("스케줄러 시작 (새벽 2시 야간 배치 등록)")


def stop_scheduler() -> None:
    s = get_scheduler()
    if s.running:
        s.shutdown(wait=False)
        log.info("스케줄러 종료")
