"""Dashboard 지표 쿼리 — Speed / Effectiveness / Quality."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_speed(db: Session, project_id: int | None = None) -> dict:
    where = "flow_stage != 'done'" if not project_id else f"flow_stage != 'done' AND project_id = {project_id}"
    p_where = "" if not project_id else f"AND project_id = {project_id}"

    # 평균 전체 소요일 (완료 이슈 기준)
    lead = db.execute(text(f"""
        SELECT
            ROUND(AVG(total_days)::numeric, 1)   AS avg_lead_time,
            ROUND(AVG(days_in_stage)::numeric, 1) AS avg_cycle_time
        FROM fct_issue_snapshot
        WHERE flow_stage = 'done' {p_where}
    """)).fetchone()

    # 주간 완료량 (이번 주 vs 지난 주)
    tp = db.execute(text(f"""
        SELECT
            SUM(CASE WHEN date >= DATE_TRUNC('week', NOW()) THEN completed_count ELSE 0 END) AS this_week,
            SUM(CASE WHEN date >= DATE_TRUNC('week', NOW()) - INTERVAL '7 days'
                      AND date < DATE_TRUNC('week', NOW()) THEN completed_count ELSE 0 END)  AS last_week
        FROM fct_throughput_daily
        WHERE date >= DATE_TRUNC('week', NOW()) - INTERVAL '7 days'
        {p_where}
    """)).fetchone()

    # Monte Carlo 간이 예측 (P50: 남은 backlog / 평균 weekly throughput)
    backlog_count = db.execute(text(f"""
        SELECT COUNT(*) FROM fct_issue_snapshot
        WHERE flow_stage IN ('backlog', 'in_progress', 'review', 'blocked')
        {p_where}
    """)).scalar() or 0

    weekly_avg = db.execute(text(f"""
        SELECT COALESCE(AVG(weekly_sum), 0)
        FROM (
            SELECT DATE_TRUNC('week', date) AS wk, SUM(completed_count) AS weekly_sum
            FROM fct_throughput_daily
            WHERE date >= NOW() - INTERVAL '12 weeks'
            {p_where}
            GROUP BY 1
        ) w
    """)).scalar() or 0

    p50_weeks = round(backlog_count / weekly_avg) if weekly_avg > 0 else None

    this_week = int(tp.this_week or 0)
    last_week = int(tp.last_week or 0)

    return {
        "avg_lead_time_days":  float(lead.avg_lead_time  or 0),
        "avg_cycle_time_days": float(lead.avg_cycle_time or 0),
        "weekly_throughput":   this_week,
        "throughput_delta":    this_week - last_week,
        "forecast_p50_weeks":  p50_weeks,
        "backlog_count":       backlog_count,
    }


def get_effectiveness(db: Session, project_id: int | None = None) -> dict:
    p_where = "" if not project_id else f"AND project_id = {project_id}"

    # WIP 총계
    wip = db.execute(text(f"""
        SELECT COUNT(*) AS total_wip,
               COUNT(*) FILTER (WHERE assigned_to_id IS NULL) AS unassigned
        FROM fct_issue_snapshot
        WHERE flow_stage IN ('in_progress', 'review') {p_where}
    """)).fetchone()

    # 구성원별 WIP → Gini 계수 간이 계산
    assignee_counts = db.execute(text(f"""
        SELECT assigned_to_id, COUNT(*) AS cnt
        FROM fct_issue_snapshot
        WHERE flow_stage IN ('in_progress', 'review')
          AND assigned_to_id IS NOT NULL
          {p_where}
        GROUP BY assigned_to_id
        ORDER BY cnt DESC
    """)).fetchall()

    gini = 0.0
    if assignee_counts:
        counts = [r.cnt for r in assignee_counts]
        n = len(counts)
        total = sum(counts)
        if total > 0 and n > 1:
            counts_sorted = sorted(counts)
            cumsum = sum((i + 1) * c for i, c in enumerate(counts_sorted))
            gini = round((2 * cumsum) / (n * total) - (n + 1) / n, 3)

    # 상위 3명 WIP 비율
    top3_count = sum(r.cnt for r in assignee_counts[:3]) if assignee_counts else 0
    total_wip = int(wip.total_wip or 0)
    top3_ratio = round(top3_count / total_wip, 2) if total_wip > 0 else 0.0

    return {
        "total_wip":       total_wip,
        "unassigned":      int(wip.unassigned or 0),
        "gini_index":      gini,
        "top3_wip_ratio":  top3_ratio,
        "assignee_counts": [{"user_id": r.assigned_to_id, "wip": r.cnt} for r in assignee_counts[:10]],
    }


def get_quality(db: Session, project_id: int | None = None) -> dict:
    p_where = "" if not project_id else f"AND project_id = {project_id}"

    # 재작업 비율
    q = db.execute(text(f"""
        SELECT
            COUNT(*)                                    AS total,
            COUNT(*) FILTER (WHERE is_rework)           AS rework_count,
            COUNT(*) FILTER (WHERE flow_stage = 'done'
                                AND is_rework)          AS rework_closed
        FROM fct_issue_snapshot
        WHERE 1=1 {p_where}
    """)).fetchone()

    total = int(q.total or 0)
    rework_count = int(q.rework_count or 0)
    rework_rate = round(rework_count / total, 3) if total > 0 else 0.0

    # 이상 신호: 체류일 365일 초과 OR 위험점수 80+
    anomalies = db.execute(text(f"""
        SELECT COUNT(*) AS cnt,
               COUNT(*) FILTER (WHERE total_days > 1000) AS extreme_count
        FROM fct_issue_snapshot
        WHERE (days_in_stage > 365 OR risk_score >= 80)
          AND flow_stage NOT IN ('done') {p_where}
    """)).fetchone()

    return {
        "total_issues":    total,
        "rework_count":    rework_count,
        "rework_rate":     rework_rate,
        "anomaly_count":   int(anomalies.cnt or 0),
        "extreme_count":   int(anomalies.extreme_count or 0),
    }
