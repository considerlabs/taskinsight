"""이슈 타임라인 LLM 설명 생성 (qwen3.6:35b-a3b)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

SYSTEM_PROMPT = """당신은 TaskInsight의 이슈 분석 모듈입니다.
주어진 이슈의 타임라인 데이터를 바탕으로 한국어 보고서체(~함, ~됨)로
3~4문장 설명을 작성하세요.

규칙:
- "약점", "문제점", "부진" 단어 사용 금지 → "함께 살펴볼 영역"
- 개인 평가 금지. 상황 설명만.
- 권장 조치 1~2가지 제안 (권유형: ~을 권장합니다)
- 최대 150자"""


def build_issue_context(issue_id: int, db: Session) -> Optional[dict[str, Any]]:
    issue = db.execute(
        text("""
            SELECT s.issue_id, s.subject, s.created_on, s.flow_stage,
                   s.assigned_to_id, s.total_days, s.days_in_stage, s.risk_score,
                   u.display_name AS assignee_name
            FROM fct_issue_snapshot s
            LEFT JOIN dim_user u ON u.user_id = s.assigned_to_id
            WHERE s.issue_id = :issue_id
        """),
        {"issue_id": issue_id},
    ).fetchone()

    if not issue:
        return None

    transitions = db.execute(
        text("""
            SELECT from_stage, to_stage, changed_at, days_in_from
            FROM fct_state_transition
            WHERE issue_id = :issue_id
            ORDER BY changed_at
        """),
        {"issue_id": issue_id},
    ).fetchall()

    # 담당자 변경 저널 (payload에서 파싱)
    assignee_changes = db.execute(
        text("""
            SELECT j.created_on, j.user_id,
                   json_array_elements(j.payload->'details') AS detail
            FROM raw_redmine_journals j
            WHERE j.journalized_id = :issue_id
              AND j.payload->'details' IS NOT NULL
        """),
        {"issue_id": issue_id},
    ).fetchall()

    # 코멘트 있는 저널 (최대 10건)
    comments = db.execute(
        text("""
            SELECT j.created_on, u.display_name AS author, j.notes
            FROM raw_redmine_journals j
            LEFT JOIN dim_user u ON u.user_id = j.user_id
            WHERE j.journalized_id = :issue_id
              AND j.notes IS NOT NULL AND j.notes != ''
            ORDER BY j.created_on DESC
            LIMIT 10
        """),
        {"issue_id": issue_id},
    ).fetchall()

    return {
        "issue": {
            "id": issue.issue_id,
            "subject": issue.subject,
            "created_on": str(issue.created_on)[:10] if issue.created_on else None,
            "current_status": issue.flow_stage,
            "current_assignee": issue.assignee_name,
        },
        "state_transitions": [
            {
                "from": t.from_stage,
                "to": t.to_stage,
                "at": str(t.changed_at)[:10] if t.changed_at else None,
                "days_in_from": round(float(t.days_in_from or 0), 1),
            }
            for t in transitions
        ],
        "comments": [
            {
                "at": str(c.created_on)[:10] if c.created_on else None,
                "author": c.author,
                "text": c.notes[:200] if c.notes else "",
            }
            for c in comments
        ],
        "metrics": {
            "total_days": round(float(issue.total_days or 0), 1),
            "current_stage": issue.flow_stage,
            "days_in_current_stage": round(float(issue.days_in_stage or 0), 1),
            "risk_score": issue.risk_score,
        },
    }


def explain_issue(issue_id: int, db: Session) -> Optional[dict]:
    ctx = build_issue_context(issue_id, db)
    if not ctx:
        return None

    prompt = f"다음 이슈 데이터를 분석하세요:\n{ctx}"

    try:
        resp = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model_timeline,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.3},
            },
            timeout=120,
        )
        resp.raise_for_status()
        explanation = resp.json()["message"]["content"].strip()
    except Exception as e:
        explanation = f"분석 생성 중 오류 발생: {e}"

    now = datetime.now(timezone.utc)
    db.execute(
        text("""
            INSERT INTO fct_issue_explanation (issue_id, explanation, generated_at, model_version, is_stale)
            VALUES (:issue_id, :explanation, :generated_at, :model_version, FALSE)
            ON CONFLICT (issue_id) DO UPDATE SET
                explanation = EXCLUDED.explanation,
                generated_at = EXCLUDED.generated_at,
                model_version = EXCLUDED.model_version,
                is_stale = FALSE
        """),
        {
            "issue_id": issue_id,
            "explanation": explanation,
            "generated_at": now,
            "model_version": settings.ollama_model_timeline,
        },
    )
    db.commit()

    return {"explanation": explanation, "generated_at": now, "model_version": settings.ollama_model_timeline}
