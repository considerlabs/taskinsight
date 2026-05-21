from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.narrator.weekly_report import generate_weekly_report
from app.db import get_db

router = APIRouter()


@router.post("/weekly/generate")
def generate_report(
    project_id: Optional[int] = Query(None),
    period_weeks: int = Query(1, ge=1, le=4),
    db: Session = Depends(get_db),
):
    """주간보고 수동 생성 (버튼 트리거)."""
    result = generate_weekly_report(db, project_id=project_id, period_weeks=period_weeks)
    return result


@router.get("/weekly/latest")
def get_latest_report(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """가장 최근 주간보고 조회."""
    p_where = "" if not project_id else f"AND project_id = {project_id}"
    row = db.execute(text(f"""
        SELECT id, project_id, period_start, period_end,
               throughput_current, throughput_previous,
               bottleneck_summary, forecast_p50_weeks, forecast_p85_weeks,
               forecast_p95_weeks, forecast_change_weeks,
               narrative_text, generated_at
        FROM fct_weekly_report
        WHERE 1=1 {p_where}
        ORDER BY generated_at DESC
        LIMIT 1
    """)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="생성된 보고서가 없습니다. 먼저 생성해주세요.")

    return {
        "id":                  row.id,
        "project_id":          row.project_id,
        "period_start":        str(row.period_start),
        "period_end":          str(row.period_end),
        "throughput": {
            "current":  row.throughput_current,
            "previous": row.throughput_previous,
            "delta":    (row.throughput_current or 0) - (row.throughput_previous or 0),
        },
        "bottleneck":          row.bottleneck_summary,
        "forecast": {
            "p50_weeks":     row.forecast_p50_weeks,
            "p85_weeks":     row.forecast_p85_weeks,
            "p95_weeks":     row.forecast_p95_weeks,
            "change_weeks":  row.forecast_change_weeks,
        },
        "narrative_text":      row.narrative_text,
        "generated_at":        row.generated_at,
    }


@router.get("/weekly/history")
def get_report_history(
    project_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """주간보고 이력 목록."""
    p_where = "" if not project_id else f"AND project_id = {project_id}"
    rows = db.execute(text(f"""
        SELECT id, project_id, period_start, period_end,
               throughput_current, generated_at
        FROM fct_weekly_report
        WHERE 1=1 {p_where}
        ORDER BY generated_at DESC
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    return {
        "reports": [
            {
                "id":           r.id,
                "period_start": str(r.period_start),
                "period_end":   str(r.period_end),
                "throughput":   r.throughput_current,
                "generated_at": r.generated_at,
            }
            for r in rows
        ]
    }
