"""주간보고 LLM 서술 생성 (qwen3.6:35b-a3b)."""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 TaskInsight의 주간보고 작성 모듈입니다.
주어진 데이터를 바탕으로 한국어 보고서체(~함, ~됨)로 항목별 1~2문장 서술을 작성하세요.

규칙:
- "약점", "문제점", "부진" 단어 사용 금지
- 개인 평가 금지. 팀 단위 상황 설명만.
- 권장 조치는 권유형(~을 권장합니다)으로 작성
- 각 항목 최대 80자"""


def _get_period(period_weeks: int = 1) -> tuple[date, date]:
    today = date.today()
    # 이번 주 월요일 기준
    monday = today - timedelta(days=today.weekday())
    period_end = monday - timedelta(days=1)          # 지난 일요일
    period_start = period_end - timedelta(weeks=period_weeks) + timedelta(days=1)
    return period_start, period_end


def _get_throughput(db: Session, project_id: Optional[int], period_start: date, period_end: date) -> dict:
    p_where = "" if not project_id else f"AND project_id = {project_id}"
    row = db.execute(text(f"""
        SELECT
            SUM(CASE WHEN date BETWEEN :start AND :end THEN completed_count ELSE 0 END)   AS current_week,
            SUM(CASE WHEN date BETWEEN :prev_start AND :prev_end THEN completed_count ELSE 0 END) AS last_week
        FROM fct_throughput_daily
        WHERE date BETWEEN :prev_start AND :end {p_where}
    """), {
        "start":      period_start,
        "end":        period_end,
        "prev_start": period_start - timedelta(weeks=1),
        "prev_end":   period_start - timedelta(days=1),
    }).fetchone()
    return {
        "current": int(row.current_week or 0),
        "previous": int(row.last_week or 0),
        "delta": int((row.current_week or 0) - (row.last_week or 0)),
    }


def _get_bottleneck(db: Session, project_id: Optional[int]) -> list[dict]:
    p_where = "" if not project_id else f"AND project_id = {project_id}"
    rows = db.execute(text(f"""
        SELECT
            flow_stage,
            COUNT(*) AS issue_count,
            ROUND(AVG(days_in_stage)::numeric, 1) AS avg_days
        FROM fct_issue_snapshot
        WHERE flow_stage NOT IN ('done') {p_where}
        GROUP BY flow_stage
        ORDER BY avg_days DESC NULLS LAST
        LIMIT 3
    """)).fetchall()
    return [
        {"stage": r.flow_stage, "count": r.issue_count, "avg_days": float(r.avg_days or 0)}
        for r in rows
    ]


def _get_forecast(db: Session, project_id: Optional[int]) -> dict:
    p_where = "" if not project_id else f"AND project_id = {project_id}"

    backlog = db.execute(text(f"""
        SELECT COUNT(*) FROM fct_issue_snapshot
        WHERE flow_stage NOT IN ('done') {p_where}
    """)).scalar() or 0

    weekly_avg = db.execute(text(f"""
        SELECT COALESCE(AVG(ws), 1)
        FROM (
            SELECT SUM(completed_count) AS ws
            FROM fct_throughput_daily
            WHERE date >= NOW() - INTERVAL '12 weeks' {p_where}
            GROUP BY DATE_TRUNC('week', date)
        ) t
    """)).scalar() or 1

    weekly_avg = float(weekly_avg)
    p50 = round(backlog / weekly_avg)
    p85 = round(backlog / (weekly_avg * 0.8))
    p95 = round(backlog / (weekly_avg * 0.65))
    return {"p50_weeks": p50, "p85_weeks": p85, "p95_weeks": p95}


def _llm_narrative(throughput: dict, bottleneck: list, forecast: dict) -> str:
    payload = {
        "throughput": throughput,
        "bottleneck_top3": bottleneck,
        "forecast": forecast,
    }
    prompt = f"다음 주간 데이터로 항목별(완료량/정체/예측) 서술을 작성하세요:\n{json.dumps(payload, ensure_ascii=False)}"
    try:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model_timeline,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        log.warning("LLM 서술 생성 실패: %s", e)
        return ""


def generate_weekly_report(
    db: Session,
    project_id: Optional[int] = None,
    period_weeks: int = 1,
) -> dict:
    period_start, period_end = _get_period(period_weeks)
    throughput = _get_throughput(db, project_id, period_start, period_end)
    bottleneck = _get_bottleneck(db, project_id)
    forecast   = _get_forecast(db, project_id)
    narrative  = _llm_narrative(throughput, bottleneck, forecast)

    now = datetime.now(timezone.utc)
    db.execute(text("""
        INSERT INTO fct_weekly_report
            (project_id, period_start, period_end,
             throughput_current, throughput_previous,
             bottleneck_summary,
             forecast_p50_weeks, forecast_p85_weeks, forecast_p95_weeks,
             forecast_change_weeks, narrative_text, generated_at)
        VALUES (
            :project_id, :period_start, :period_end,
            :tp_current, :tp_previous,
            :bottleneck,
            :p50, :p85, :p95,
            :forecast_change, :narrative, :generated_at
        )
    """), {
        "project_id":     project_id,
        "period_start":   period_start,
        "period_end":     period_end,
        "tp_current":     throughput["current"],
        "tp_previous":    throughput["previous"],
        "bottleneck":     json.dumps(bottleneck, ensure_ascii=False),
        "p50":            forecast["p50_weeks"],
        "p85":            forecast["p85_weeks"],
        "p95":            forecast["p95_weeks"],
        "forecast_change": 0,   # TODO: 전주 보고서와 비교
        "narrative":      narrative,
        "generated_at":   now,
    })
    db.commit()

    return {
        "period_start":   str(period_start),
        "period_end":     str(period_end),
        "throughput":     throughput,
        "bottleneck":     bottleneck,
        "forecast":       forecast,
        "narrative_text": narrative,
        "generated_at":   now.isoformat(),
    }
