from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg.types.json import Jsonb
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector, COMING_SOON
from app.db import get_db

router = APIRouter()


class ConnectorUpdateRequest(BaseModel):
    instance_name: Optional[str] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class TestConnectionRequest(BaseModel):
    connector_type: str
    config: dict


@router.get("/instances")
def list_instances(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT id, connector_type, instance_name, config, is_active, updated_at FROM connector_instance ORDER BY id")
    ).fetchall()

    instances = [
        {
            "id": r.id,
            "connector_type": r.connector_type,
            "instance_name": r.instance_name,
            "config": {k: v for k, v in r.config.items() if k != "api_key"},  # api_key 마스킹
            "is_active": r.is_active,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]
    return {"instances": instances, "coming_soon": COMING_SOON}


@router.post("/test")
def test_connection(req: TestConnectionRequest):
    try:
        connector = get_connector(req.connector_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = connector.test_connection(req.config)
    return result


@router.put("/{instance_id}")
def update_instance(
    instance_id: int,
    req: ConnectorUpdateRequest,
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("SELECT id, config FROM connector_instance WHERE id = :id"),
        {"id": instance_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="연동 설정을 찾을 수 없습니다.")

    updates = []
    params: dict = {"id": instance_id}

    if req.instance_name is not None:
        updates.append("instance_name = :name")
        params["name"] = req.instance_name

    if req.config is not None:
        merged = {**row.config, **req.config}
        updates.append("config = :config")
        params["config"] = Jsonb(merged)

    if req.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = req.is_active

    if not updates:
        return {"ok": True}

    updates.append("updated_at = NOW()")
    db.execute(
        text(f"UPDATE connector_instance SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    db.commit()
    return {"ok": True}


@router.post("/{instance_id}/sync")
def trigger_sync(instance_id: int, db: Session = Depends(get_db)):
    """지금 동기화 — Redmine 수집 + ETL 트리거."""
    from app.collector.redmine_collector import sync_redmine
    from app.etl.populate import run_etl

    row = db.execute(
        text("SELECT id, connector_type, config FROM connector_instance WHERE id = :id AND is_active = TRUE"),
        {"id": instance_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="활성 연동 설정을 찾을 수 없습니다.")

    config = row.config
    try:
        sync_result = sync_redmine(config, db)
        etl_result  = run_etl(db)
        return {"ok": True, "sync": sync_result, "etl": etl_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
