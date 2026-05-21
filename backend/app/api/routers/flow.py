from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db

router = APIRouter()

STAGE_ORDER = ["backlog", "in_progress", "review", "done", "blocked"]


@router.get("/stages")
def get_stages(
    project_id: Optional[int] = Query(None),
    period_months: int = Query(6, ge=1, le=120),
    db: Session = Depends(get_db),
):
    """단계별 이슈 건수 + 평균 체류일. 펀넬 차트용."""
    where = ["flow_stage != 'done'"]
    params: dict = {}

    if project_id:
        where.append("project_id = :project_id")
        params["project_id"] = project_id

    where_sql = " AND ".join(where)

    rows = db.execute(
        text(f"""
            SELECT
                flow_stage,
                COUNT(*) AS issue_count,
                ROUND(AVG(days_in_stage)::numeric, 1) AS avg_days_in_stage,
                ROUND(AVG(total_days)::numeric, 1) AS avg_total_days,
                COUNT(*) FILTER (WHERE risk_score >= 70) AS high_risk_count
            FROM fct_issue_snapshot
            WHERE {where_sql}
            GROUP BY flow_stage
            ORDER BY
                CASE flow_stage
                    WHEN 'backlog'      THEN 1
                    WHEN 'in_progress'  THEN 2
                    WHEN 'review'       THEN 3
                    WHEN 'blocked'      THEN 4
                    ELSE 5
                END
        """),
        params,
    ).fetchall()

    # 주간 완료량 (fct_throughput_daily 기반)
    throughput_params: dict = {"weeks": period_months * 4}
    if project_id:
        throughput_params["project_id"] = project_id
        throughput_sql = """
            SELECT COALESCE(SUM(completed_count), 0) AS total,
                   COALESCE(AVG(completed_count), 0) AS weekly_avg
            FROM fct_throughput_daily
            WHERE date >= NOW() - INTERVAL '1 week'
              AND project_id = :project_id
        """
    else:
        throughput_sql = """
            SELECT COALESCE(SUM(completed_count), 0) AS total,
                   COALESCE(AVG(completed_count), 0) AS weekly_avg
            FROM fct_throughput_daily
            WHERE date >= NOW() - INTERVAL '1 week'
        """

    tp = db.execute(text(throughput_sql), throughput_params).fetchone()

    stages = [
        {
            "stage": r.flow_stage,
            "issue_count": r.issue_count,
            "avg_days_in_stage": float(r.avg_days_in_stage or 0),
            "avg_total_days": float(r.avg_total_days or 0),
            "high_risk_count": r.high_risk_count,
        }
        for r in rows
    ]

    return {
        "stages": stages,
        "weekly_throughput": int(tp.total if tp else 0),
        "weekly_throughput_avg": round(float(tp.weekly_avg if tp else 0), 1),
    }


@router.get("/issues")
def list_issues(
    project_id: Optional[int] = Query(None),
    flow_stage: Optional[str] = Query(None),
    period_months: int = Query(6, ge=1, le=120),
    risk_min: int = Query(0, ge=0, le=100),
    sort_by: str = Query("days_in_stage"),   # days_in_stage | risk_score | total_days
    order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """이슈 목록. 단계/프로젝트/기간/위험점수 필터."""
    allowed_sort = {"days_in_stage", "risk_score", "total_days", "updated_on"}
    if sort_by not in allowed_sort:
        raise HTTPException(status_code=400, detail=f"sort_by는 {allowed_sort} 중 하나여야 합니다.")
    order_dir = "DESC" if order.lower() == "desc" else "ASC"

    where = [f"s.created_on >= NOW() - INTERVAL '{period_months} months'"]
    params: dict = {"limit": limit, "offset": offset}

    if project_id:
        where.append("s.project_id = :project_id")
        params["project_id"] = project_id

    if flow_stage:
        where.append("s.flow_stage = :flow_stage")
        params["flow_stage"] = flow_stage

    if risk_min > 0:
        where.append("s.risk_score >= :risk_min")
        params["risk_min"] = risk_min

    where_sql = " AND ".join(where)

    rows = db.execute(
        text(f"""
            SELECT
                s.issue_id,
                s.subject,
                s.flow_stage,
                s.project_id,
                p.name AS project_name,
                s.assigned_to_id,
                u.display_name AS assignee_name,
                s.days_in_stage,
                s.total_days,
                s.risk_score,
                s.is_rework,
                s.updated_on,
                CASE WHEN e.issue_id IS NOT NULL AND NOT e.is_stale THEN TRUE ELSE FALSE END AS has_explanation
            FROM fct_issue_snapshot s
            LEFT JOIN dim_project p ON p.project_id = s.project_id
            LEFT JOIN dim_user u ON u.user_id = s.assigned_to_id
            LEFT JOIN fct_issue_explanation e ON e.issue_id = s.issue_id
            WHERE {where_sql}
            ORDER BY s.{sort_by} {order_dir} NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).fetchall()

    # 전체 건수 (페이지네이션용)
    count_row = db.execute(
        text(f"""
            SELECT COUNT(*) AS total
            FROM fct_issue_snapshot s
            WHERE {where_sql}
        """),
        params,
    ).fetchone()

    issues = [
        {
            "issue_id": r.issue_id,
            "subject": r.subject,
            "flow_stage": r.flow_stage,
            "project_id": r.project_id,
            "project_name": r.project_name,
            "assigned_to_id": r.assigned_to_id,
            "assignee_name": r.assignee_name,
            "days_in_stage": round(float(r.days_in_stage or 0), 1),
            "total_days": round(float(r.total_days or 0), 1),
            "risk_score": r.risk_score,
            "is_rework": r.is_rework,
            "updated_on": r.updated_on,
            "has_explanation": r.has_explanation,
        }
        for r in rows
    ]

    return {
        "issues": issues,
        "total": count_row.total if count_row else 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/issue/{issue_id}/explanation")
def get_explanation(issue_id: int, db: Session = Depends(get_db)):
    """LLM 이슈 타임라인 설명. 캐시 우선 반환."""
    row = db.execute(
        text("""
            SELECT explanation, generated_at, model_version, is_stale
            FROM fct_issue_explanation
            WHERE issue_id = :issue_id
        """),
        {"issue_id": issue_id},
    ).fetchone()

    if row and not row.is_stale:
        return {
            "issue_id": issue_id,
            "explanation": row.explanation,
            "generated_at": row.generated_at,
            "model_version": row.model_version,
            "cached": True,
        }

    # 캐시 없거나 stale → 온디맨드 생성
    from app.narrator.issue_explainer import explain_issue
    result = explain_issue(issue_id, db)

    if result is None:
        raise HTTPException(status_code=404, detail=f"이슈 {issue_id}를 찾을 수 없습니다.")

    return {
        "issue_id": issue_id,
        "explanation": result["explanation"],
        "generated_at": result["generated_at"],
        "model_version": result["model_version"],
        "cached": False,
    }
