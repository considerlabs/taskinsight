from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.dashboard import get_speed, get_effectiveness, get_quality
from app.db import get_db

router = APIRouter()


@router.get("/summary")
def dashboard_summary(
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Speed + Effectiveness + Quality 3섹션 요약."""
    speed         = get_speed(db, project_id)
    effectiveness = get_effectiveness(db, project_id)
    quality       = get_quality(db, project_id)

    return {
        "speed":         speed,
        "effectiveness": effectiveness,
        "quality":       quality,
    }
