from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.auth import User

router = APIRouter()

STAGE_KO = {
    "backlog": "백로그",
    "in_progress": "진행중",
    "review": "검토",
    "blocked": "차단됨",
}


def _pf(project_id: Optional[int], alias: str = "") -> tuple[str, dict]:
    col = f"{alias}.project_id" if alias else "project_id"
    if project_id:
        return f" AND {col} = :project_id", {"project_id": project_id}
    return "", {}


def _fmt_days(days: Optional[float]) -> str:
    if days is None:
        return "—"
    d = float(days)
    if d >= 365:
        return f"{d / 365:.1f}년"
    if d >= 30:
        return f"{round(d / 30)}개월"
    return f"{round(d)}일"


def _fmt_pct(val: Optional[float]) -> str:
    if val is None:
        return "—"
    return f"{float(val):.1f}%"


def _card(
    id: str,
    title: str,
    category: str,
    target: str,
    zone: str,
    data_status: str,
    alert: bool,
    primary_value: str,
    primary_label: str,
    details: list,
    note: Optional[str] = None,
) -> dict:
    return {
        "id": id,
        "title": title,
        "category": category,
        "target": target,
        "zone": zone,
        "data_status": data_status,
        "alert": alert,
        "primary_value": primary_value,
        "primary_label": primary_label,
        "details": details,
        "note": note,
    }


# ─── Card implementations ──────────────────────────────────────────────────────

def _ins_r_001(db: Session, project_id: Optional[int]) -> dict:
    """단계별 정체 — stage별 days_in_stage p50/p85 (정의 보정 예정)."""
    pf, pp = _pf(project_id, "s")
    rows = db.execute(text(f"""
        SELECT
            s.flow_stage,
            COUNT(*) AS cnt,
            ROUND(percentile_disc(0.5) WITHIN GROUP (ORDER BY s.days_in_stage)::numeric, 1) AS p50,
            ROUND(percentile_disc(0.85) WITHIN GROUP (ORDER BY s.days_in_stage)::numeric, 1) AS p85
        FROM fct_issue_snapshot s
        WHERE s.flow_stage != 'done' {pf}
        GROUP BY s.flow_stage
        ORDER BY CASE s.flow_stage
            WHEN 'backlog' THEN 1 WHEN 'in_progress' THEN 2
            WHEN 'review' THEN 3 WHEN 'blocked' THEN 4 ELSE 5 END
    """), pp).fetchall()

    overall = db.execute(text(f"""
        SELECT ROUND(percentile_disc(0.85) WITHIN GROUP (ORDER BY s.days_in_stage)::numeric, 1) AS p85
        FROM fct_issue_snapshot s
        WHERE s.flow_stage != 'done' {pf}
    """), pp).fetchone()
    p85_overall = float(overall.p85 or 0) if overall and overall.p85 else 0

    details = []
    max_p85 = 0.0
    worst_stage = None
    for r in rows:
        p85_val = float(r.p85 or 0)
        if p85_val > max_p85:
            max_p85 = p85_val
            worst_stage = r
        details.append({
            "label": STAGE_KO.get(r.flow_stage, r.flow_stage),
            "value": _fmt_days(r.p85),
            "secondary": f"중위 {_fmt_days(r.p50)} · {r.cnt}건",
            "highlight": p85_overall > 0 and p85_val > p85_overall * 1.5,
        })

    alert = p85_overall > 0 and max_p85 > p85_overall * 1.5
    primary_val = _fmt_days(float(worst_stage.p85)) if worst_stage else "—"
    primary_lbl = f"{STAGE_KO.get(worst_stage.flow_stage, '')} p85" if worst_stage else "—"

    return _card(
        id="INS-R-001", title="단계별 정체", category="흐름", target="both",
        zone="alert" if alert else "monitoring",
        data_status="approx", alert=alert,
        primary_value=primary_val, primary_label=primary_lbl,
        details=details,
        note="days_in_stage 단계구간 재집계 예정 (SV4)",
    )


def _ins_r_002(db: Session, project_id: Optional[int]) -> dict:
    """리드타임 분포 — 완료 이슈 total_days p50/p85."""
    pf, pp = _pf(project_id, "s")
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS cnt,
            ROUND(percentile_disc(0.5) WITHIN GROUP (ORDER BY s.total_days)::numeric, 1) AS p50,
            ROUND(percentile_disc(0.85) WITHIN GROUP (ORDER BY s.total_days)::numeric, 1) AS p85
        FROM fct_issue_snapshot s
        WHERE s.closed_on IS NOT NULL {pf}
    """), pp).fetchone()

    p50 = float(row.p50 or 0) if row and row.p50 else 0
    p85 = float(row.p85 or 0) if row and row.p85 else 0
    cnt = row.cnt if row else 0
    alert = p50 > 0 and p85 > p50 * 3

    return _card(
        id="INS-R-002", title="리드타임 분포", category="흐름", target="both",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=_fmt_days(p50), primary_label="완료 이슈 중위",
        details=[
            {"label": "중위값 (p50)", "value": _fmt_days(p50), "secondary": ""},
            {"label": "상위 15% (p85)", "value": _fmt_days(p85), "secondary": f"분석 대상 {cnt:,}건"},
        ],
    )


def _ins_r_003(db: Session, project_id: Optional[int]) -> dict:
    """유입 vs 처리 비율 — 처리측 실측, 유입 미수집."""
    pf_tp = " AND project_id = :project_id" if project_id else ""
    pp = {"project_id": project_id} if project_id else {}
    row = db.execute(text(f"""
        SELECT ROUND(AVG(completed_count)::numeric, 1) AS weekly_avg
        FROM fct_throughput_daily
        WHERE date >= NOW() - INTERVAL '4 weeks' {pf_tp}
    """), pp).fetchone()

    weekly = float(row.weekly_avg or 0) if row and row.weekly_avg else 0
    return _card(
        id="INS-R-003", title="유입 vs 처리 비율", category="속도", target="decision",
        zone="monitoring", data_status="approx", alert=False,
        primary_value=f"{weekly:.0f}건", primary_label="주간 완료 (4주 평균)",
        details=[
            {"label": "주간 완료 (4주 평균)", "value": f"{weekly:.0f}건", "secondary": "실측"},
            {"label": "주간 유입", "value": "—", "secondary": "SV1 수집 후 활성"},
        ],
        note="유입 이벤트 로그(SV1) 수집 후 유입/처리 비율 산출 가능",
    )


def _ins_r_004(db: Session, project_id: Optional[int]) -> dict:
    """blocked 지속시간."""
    pf, pp = _pf(project_id, "s")
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS cnt,
            ROUND(AVG(s.days_in_stage)::numeric, 1) AS avg_days,
            ROUND(percentile_disc(0.85) WITHIN GROUP (ORDER BY s.days_in_stage)::numeric, 1) AS p85
        FROM fct_issue_snapshot s
        WHERE s.flow_stage = 'blocked' {pf}
    """), pp).fetchone()

    cnt = row.cnt if row else 0
    avg = float(row.avg_days or 0) if row and row.avg_days else 0
    p85 = float(row.p85 or 0) if row and row.p85 else 0
    alert = cnt > 0 and p85 > 14

    return _card(
        id="INS-R-004", title="blocked 지속시간", category="속도", target="manager",
        zone="alert" if alert else "monitoring",
        data_status="approx", alert=alert,
        primary_value=_fmt_days(p85) if cnt > 0 else "없음",
        primary_label="차단 이슈 p85",
        details=[
            {"label": "차단 이슈", "value": f"{cnt}건", "secondary": ""},
            {"label": "평균 지속", "value": _fmt_days(avg), "secondary": ""},
            {"label": "상위 15% (p85)", "value": _fmt_days(p85), "secondary": ""},
        ],
    )


def _ins_r_005(db: Session, project_id: Optional[int]) -> dict:
    """전이 vs 활동(stall) — field_change_events 없음, mock."""
    return _card(
        id="INS-R-005", title="전이 vs 활동(stall)", category="속도", target="manager",
        zone="monitoring", data_status="mock", alert=False,
        primary_value="—", primary_label="stall 비율",
        details=[],
        note="field_change_events 수집(SV1) 후 산출 가능",
    )


def _ins_r_006(db: Session, project_id: Optional[int]) -> dict:
    """재오픈율 — is_rework (review→in_progress)."""
    pf, pp = _pf(project_id, "s")
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE s.is_rework) AS rework_count
        FROM fct_issue_snapshot s
        WHERE 1=1 {pf}
    """), pp).fetchone()

    total = row.total if row else 0
    rework = row.rework_count if row else 0
    rate = rework * 100.0 / total if total > 0 else 0
    alert = rate > 20

    return _card(
        id="INS-R-006", title="재오픈율", category="품질", target="both",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=_fmt_pct(rate), primary_label="review 반려 기준",
        details=[
            {"label": "재작업 이슈", "value": f"{rework:,}건", "secondary": ""},
            {"label": "전체 이슈", "value": f"{total:,}건", "secondary": ""},
        ],
    )


def _ins_r_007(db: Session, project_id: Optional[int]) -> dict:
    """WIP 동시진행 — 현시점 스냅샷."""
    pf, pp = _pf(project_id, "s")
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS wip_count,
            COUNT(DISTINCT s.assigned_to_id) FILTER (WHERE s.assigned_to_id IS NOT NULL) AS assignee_count
        FROM fct_issue_snapshot s
        WHERE s.flow_stage = 'in_progress' {pf}
    """), pp).fetchone()

    wip = row.wip_count if row else 0
    assignees = row.assignee_count if row else 0
    per_person = round(wip / assignees, 1) if assignees > 0 else 0

    return _card(
        id="INS-R-007", title="WIP 동시진행", category="부하", target="manager",
        zone="monitoring", data_status="approx", alert=False,
        primary_value=f"{wip}건", primary_label="현재 진행중",
        details=[
            {"label": "진행중 이슈", "value": f"{wip}건", "secondary": ""},
            {"label": "담당자 수", "value": f"{assignees}명", "secondary": ""},
            {"label": "1인당 WIP", "value": f"{per_person:.1f}건", "secondary": ""},
        ],
        note="일별 WIP 추이는 daily_issue_state 수집(SV1) 후 가능",
    )


def _ins_r_008(db: Session, project_id: Optional[int]) -> dict:
    """마일스톤 번다운 — milestone_baselines 미수집, mock."""
    return _card(
        id="INS-R-008", title="마일스톤 번다운", category="예측가능성", target="both",
        zone="monitoring", data_status="mock", alert=False,
        primary_value="—", primary_label="범위 변화율",
        details=[],
        note="milestone_baselines 수집(SV2) 후 scope creep 측정 가능",
    )


def _ins_r_009(db: Session, project_id: Optional[int]) -> dict:
    """에이징 백로그 — updated_on 일괄 갱신으로 일시 비활성."""
    return _card(
        id="INS-R-009", title="에이징 백로그", category="위험", target="manager",
        zone="disabled", data_status="disabled", alert=False,
        primary_value="—", primary_label="—",
        details=[],
        note="Redmine updated_on 일괄 갱신으로 13주 비활성. 신규 데이터 누적 후 활성화.",
    )


def _ins_r_010(db: Session, project_id: Optional[int]) -> dict:
    """마감 신뢰도 — due_date 기반."""
    pf, pp = _pf(project_id)
    row = db.execute(text(f"""
        SELECT
            COUNT(*) FILTER (WHERE due_date IS NOT NULL AND closed_on IS NOT NULL) AS with_due,
            COUNT(*) FILTER (
                WHERE due_date IS NOT NULL AND closed_on IS NOT NULL
                  AND DATE(closed_on AT TIME ZONE 'UTC') <= due_date
            ) AS on_time
        FROM raw_redmine_issues
        WHERE 1=1 {pf}
    """), pp).fetchone()

    with_due = row.with_due if row else 0
    on_time = row.on_time if row else 0
    rate = on_time * 100.0 / with_due if with_due > 0 else 0
    alert = with_due > 10 and rate < 60

    return _card(
        id="INS-R-010", title="마감 신뢰도", category="예측가능성", target="decision",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=_fmt_pct(rate), primary_label="기한 내 완료율",
        details=[
            {"label": "기한 내 완료", "value": f"{on_time:,}건", "secondary": ""},
            {"label": "마감일 있는 완료", "value": f"{with_due:,}건", "secondary": ""},
        ],
    )


def _ins_r_011(db: Session, project_id: Optional[int]) -> dict:
    """부하 쏠림(프로젝트) — 프로젝트 단위 집계, 개인 분해 없음."""
    pf, pp = _pf(project_id, "s")
    rows = db.execute(text(f"""
        SELECT p.name AS project_name, COUNT(*) AS open_count
        FROM fct_issue_snapshot s
        JOIN dim_project p ON p.project_id = s.project_id
        WHERE s.flow_stage != 'done' {pf}
        GROUP BY p.project_id, p.name
        ORDER BY open_count DESC
        LIMIT 5
    """), pp).fetchall()

    total_row = db.execute(text(f"""
        SELECT COUNT(*) AS total FROM fct_issue_snapshot s WHERE s.flow_stage != 'done' {pf}
    """), pp).fetchone()
    total = total_row.total if total_row else 0

    details = []
    for r in rows:
        pct = r.open_count * 100.0 / total if total > 0 else 0
        details.append({
            "label": r.project_name,
            "value": f"{r.open_count}건",
            "secondary": f"{pct:.0f}%",
        })

    top_pct = (rows[0].open_count * 100.0 / total) if rows and total > 0 else 0
    alert = top_pct > 60

    return _card(
        id="INS-R-011", title="부하 쏠림(프로젝트)", category="부하", target="decision",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=f"{top_pct:.0f}%",
        primary_label=f"{rows[0].project_name} 집중도" if rows else "—",
        details=details,
    )


def _ins_r_012(db: Session, project_id: Optional[int]) -> dict:
    """담당자 핑퐁 — 3회 이상 재할당 이슈 수. 개인 식별 없음."""
    if project_id:
        pingpong_sql = """
            SELECT COUNT(*) AS pingpong_count
            FROM (
                SELECT j.journalized_id
                FROM raw_redmine_journals j
                JOIN raw_redmine_issues i ON i.id = j.journalized_id AND i.project_id = :project_id,
                     jsonb_array_elements(j.payload::jsonb->'details') AS d
                WHERE (d->>'prop_key') = 'assigned_to_id'
                  AND (d->>'old_value') IS NOT NULL
                  AND (d->>'value') IS NOT NULL
                GROUP BY j.journalized_id
                HAVING COUNT(*) >= 3
            ) sub
        """
        total_sql = "SELECT COUNT(*) AS total FROM fct_issue_snapshot WHERE project_id = :project_id"
        pp = {"project_id": project_id}
    else:
        pingpong_sql = """
            SELECT COUNT(*) AS pingpong_count
            FROM (
                SELECT j.journalized_id
                FROM raw_redmine_journals j,
                     jsonb_array_elements(j.payload::jsonb->'details') AS d
                WHERE (d->>'prop_key') = 'assigned_to_id'
                  AND (d->>'old_value') IS NOT NULL
                  AND (d->>'value') IS NOT NULL
                GROUP BY j.journalized_id
                HAVING COUNT(*) >= 3
            ) sub
        """
        total_sql = "SELECT COUNT(*) AS total FROM fct_issue_snapshot"
        pp = {}

    pingpong_row = db.execute(text(pingpong_sql), pp).fetchone()
    total_row = db.execute(text(total_sql), pp).fetchone()

    pingpong = pingpong_row.pingpong_count if pingpong_row else 0
    total = total_row.total if total_row else 0
    rate = pingpong * 100.0 / total if total > 0 else 0
    alert = rate > 5

    return _card(
        id="INS-R-012", title="담당자 핑퐁", category="위험", target="manager",
        zone="alert" if alert else "monitoring",
        data_status="approx", alert=alert,
        primary_value=f"{pingpong}건", primary_label="3회 이상 재할당",
        details=[
            {"label": "핑퐁 이슈", "value": f"{pingpong}건", "secondary": ""},
            {"label": "전체 이슈 대비", "value": _fmt_pct(rate), "secondary": ""},
        ],
    )


def _ins_r_013(db: Session, project_id: Optional[int]) -> dict:
    """이슈 구조 건강도 — parent_id / estimated_hours."""
    pf, pp = _pf(project_id)
    row = db.execute(text(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE parent_id IS NOT NULL) AS with_parent,
            COUNT(*) FILTER (WHERE estimated_hours > 0) AS with_estimate
        FROM raw_redmine_issues
        WHERE 1=1 {pf}
    """), pp).fetchone()

    total = row.total if row else 0
    with_parent = row.with_parent if row else 0
    with_estimate = row.with_estimate if row else 0
    parent_pct = with_parent * 100.0 / total if total > 0 else 0
    estimate_pct = with_estimate * 100.0 / total if total > 0 else 0
    alert = total > 100 and estimate_pct < 30

    return _card(
        id="INS-R-013", title="이슈 구조 건강도", category="구조", target="both",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=_fmt_pct(estimate_pct), primary_label="예상시간 입력률",
        details=[
            {"label": "전체 이슈", "value": f"{total:,}건", "secondary": ""},
            {"label": "부모 이슈 있음", "value": _fmt_pct(parent_pct), "secondary": ""},
            {"label": "예상시간 입력", "value": _fmt_pct(estimate_pct), "secondary": ""},
        ],
    )


def _ins_r_014(db: Session, project_id: Optional[int]) -> dict:
    """review 반려율 — review→in_progress 전환 이슈."""
    pf, pp = _pf(project_id, "s")
    rejected_row = db.execute(text(f"""
        SELECT COUNT(DISTINCT t.issue_id) AS rejected
        FROM fct_state_transition t
        JOIN fct_issue_snapshot s ON s.issue_id = t.issue_id
        WHERE t.from_stage = 'review' AND t.to_stage = 'in_progress' {pf}
    """), pp).fetchone()

    reviewed_row = db.execute(text(f"""
        SELECT COUNT(DISTINCT t.issue_id) AS reviewed
        FROM fct_state_transition t
        JOIN fct_issue_snapshot s ON s.issue_id = t.issue_id
        WHERE t.to_stage = 'review' {pf}
    """), pp).fetchone()

    rejected = rejected_row.rejected if rejected_row else 0
    reviewed = reviewed_row.reviewed if reviewed_row else 0
    rate = rejected * 100.0 / reviewed if reviewed > 0 else 0
    alert = rate > 25

    return _card(
        id="INS-R-014", title="review 반려율", category="품질", target="manager",
        zone="alert" if alert else "monitoring",
        data_status="real", alert=alert,
        primary_value=_fmt_pct(rate), primary_label="검토 반려율",
        details=[
            {"label": "반려 건수", "value": f"{rejected}건", "secondary": ""},
            {"label": "검토 통과 건수", "value": f"{reviewed}건", "secondary": ""},
        ],
    )


# ─── Drill-down endpoint ──────────────────────────────────────────────────────

_ISSUE_SELECT = """
    SELECT
        s.issue_id,
        s.subject,
        s.flow_stage,
        p.name   AS project_name,
        u.display_name AS assignee_name,
        s.days_in_stage,
        s.total_days,
        s.is_rework
    FROM fct_issue_snapshot s
    JOIN dim_project p ON p.project_id = s.project_id
    LEFT JOIN dim_user u ON u.user_id = s.assigned_to_id
"""

_MOCK_CARDS = {"INS-R-003", "INS-R-005", "INS-R-008", "INS-R-009"}


@router.get("/cards/{card_id}/issues")
def get_card_issues(
    card_id: str,
    project_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """카드별 드릴다운 이슈 목록."""
    if card_id in _MOCK_CARDS:
        return {"card_id": card_id, "issues": [], "total": 0, "limit": limit, "offset": offset,
                "note": "데이터 수집 후 이슈 목록 제공 예정"}

    pf, pp = _pf(project_id, "s")
    pp = {**pp, "limit": limit, "offset": offset}

    if card_id == "INS-R-001":
        where = f"WHERE s.flow_stage != 'done' {pf}"
        order = "s.days_in_stage DESC NULLS LAST"

    elif card_id == "INS-R-002":
        where = f"WHERE s.closed_on IS NOT NULL {pf}"
        order = "s.total_days DESC NULLS LAST"

    elif card_id == "INS-R-004":
        where = f"WHERE s.flow_stage = 'blocked' {pf}"
        order = "s.days_in_stage DESC NULLS LAST"

    elif card_id == "INS-R-006":
        where = f"WHERE s.is_rework = TRUE {pf}"
        order = "s.total_days DESC NULLS LAST"

    elif card_id == "INS-R-007":
        where = f"WHERE s.flow_stage = 'in_progress' {pf}"
        order = "s.days_in_stage DESC NULLS LAST"

    elif card_id == "INS-R-010":
        rows = db.execute(text(f"""
            {_ISSUE_SELECT}
            JOIN raw_redmine_issues ri ON ri.id = s.issue_id
            WHERE ri.due_date IS NOT NULL AND ri.closed_on IS NOT NULL
              AND DATE(ri.closed_on AT TIME ZONE 'UTC') > ri.due_date {pf}
            ORDER BY (DATE(ri.closed_on AT TIME ZONE 'UTC') - ri.due_date) DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """), pp).fetchall()
        count = db.execute(text(f"""
            SELECT COUNT(*) AS total FROM raw_redmine_issues ri
            JOIN fct_issue_snapshot s ON s.issue_id = ri.id
            WHERE ri.due_date IS NOT NULL AND ri.closed_on IS NOT NULL
              AND DATE(ri.closed_on AT TIME ZONE 'UTC') > ri.due_date {pf}
        """), pp).fetchone()
        return {
            "card_id": card_id,
            "issues": [_row_to_issue(r) for r in rows],
            "total": count.total if count else 0,
            "limit": limit, "offset": offset,
        }

    elif card_id == "INS-R-011":
        where = f"WHERE s.flow_stage != 'done' {pf}"
        order = "s.project_id, s.days_in_stage DESC NULLS LAST"

    elif card_id == "INS-R-012":
        pid_join = "JOIN raw_redmine_issues ri ON ri.id = j.journalized_id AND ri.project_id = :project_id" if project_id else ""
        pingpong_ids_sql = f"""
            SELECT DISTINCT j.journalized_id AS issue_id
            FROM raw_redmine_journals j {pid_join},
                 jsonb_array_elements(j.payload::jsonb->'details') AS d
            WHERE (d->>'prop_key') = 'assigned_to_id'
              AND (d->>'old_value') IS NOT NULL AND (d->>'value') IS NOT NULL
            GROUP BY j.journalized_id HAVING COUNT(*) >= 3
        """
        rows = db.execute(text(f"""
            {_ISSUE_SELECT}
            WHERE s.issue_id IN ({pingpong_ids_sql}) {pf}
            ORDER BY s.days_in_stage DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """), pp).fetchall()
        count = db.execute(text(f"""
            SELECT COUNT(*) AS total FROM fct_issue_snapshot s
            WHERE s.issue_id IN ({pingpong_ids_sql}) {pf}
        """), pp).fetchone()
        return {
            "card_id": card_id,
            "issues": [_row_to_issue(r) for r in rows],
            "total": count.total if count else 0,
            "limit": limit, "offset": offset,
        }

    elif card_id == "INS-R-013":
        where = f"WHERE (s.issue_id NOT IN (SELECT id FROM raw_redmine_issues WHERE estimated_hours > 0)) {pf}"
        order = "s.total_days DESC NULLS LAST"

    elif card_id == "INS-R-014":
        rows = db.execute(text(f"""
            {_ISSUE_SELECT}
            WHERE s.issue_id IN (
                SELECT DISTINCT t.issue_id FROM fct_state_transition t
                WHERE t.from_stage = 'review' AND t.to_stage = 'in_progress'
            ) {pf}
            ORDER BY s.total_days DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """), pp).fetchall()
        count = db.execute(text(f"""
            SELECT COUNT(*) AS total FROM fct_issue_snapshot s
            WHERE s.issue_id IN (
                SELECT DISTINCT t.issue_id FROM fct_state_transition t
                WHERE t.from_stage = 'review' AND t.to_stage = 'in_progress'
            ) {pf}
        """), pp).fetchone()
        return {
            "card_id": card_id,
            "issues": [_row_to_issue(r) for r in rows],
            "total": count.total if count else 0,
            "limit": limit, "offset": offset,
        }

    else:
        raise HTTPException(status_code=404, detail=f"Unknown card_id: {card_id}")

    rows = db.execute(text(f"{_ISSUE_SELECT} {where} ORDER BY {order} LIMIT :limit OFFSET :offset"), pp).fetchall()
    count = db.execute(text(f"SELECT COUNT(*) AS total FROM fct_issue_snapshot s {where}"), pp).fetchone()
    return {
        "card_id": card_id,
        "issues": [_row_to_issue(r) for r in rows],
        "total": count.total if count else 0,
        "limit": limit, "offset": offset,
    }


def _row_to_issue(r) -> dict:
    return {
        "issue_id": r.issue_id,
        "subject": r.subject,
        "flow_stage": r.flow_stage,
        "project_name": r.project_name,
        "assignee_name": r.assignee_name,
        "days_in_stage": round(float(r.days_in_stage or 0), 1),
        "total_days": round(float(r.total_days or 0), 1),
        "is_rework": r.is_rework,
    }


# ─── Main endpoint ─────────────────────────────────────────────────────────────

@router.get("/cards")
def get_insight_cards(
    project_id: Optional[int] = Query(None),
    period_months: int = Query(6, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """14종 인사이트 카드. 의사결정자·중간관리자용."""
    cards = [
        _ins_r_001(db, project_id),
        _ins_r_002(db, project_id),
        _ins_r_003(db, project_id),
        _ins_r_004(db, project_id),
        _ins_r_005(db, project_id),
        _ins_r_006(db, project_id),
        _ins_r_007(db, project_id),
        _ins_r_008(db, project_id),
        _ins_r_009(db, project_id),
        _ins_r_010(db, project_id),
        _ins_r_011(db, project_id),
        _ins_r_012(db, project_id),
        _ins_r_013(db, project_id),
        _ins_r_014(db, project_id),
    ]

    zone_rank = {"alert": 0, "monitoring": 1, "disabled": 2}
    cards.sort(key=lambda c: zone_rank.get(c["zone"], 1))

    return {
        "cards": cards,
        "alert_count": sum(1 for c in cards if c["alert"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
