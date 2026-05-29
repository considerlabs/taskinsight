from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import flow, connectors, dashboard, reports, insights
from app.api.routers import auth, users, projects, issues, time_entries, attachments, notifications

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="TaskInsight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/v1/auth",       tags=["auth"])
app.include_router(users.router,       prefix="/v1/users",      tags=["users"])
app.include_router(projects.router,    prefix="/v1/projects",   tags=["projects"])
app.include_router(issues.router,        prefix="/v1/projects/{project_id}/issues", tags=["issues"])
app.include_router(time_entries.router,  prefix="/v1/time-entries",   tags=["time-entries"])
app.include_router(attachments.router,   prefix="/v1/attachments",    tags=["attachments"])
app.include_router(notifications.router, prefix="/v1/notifications",  tags=["notifications"])
app.include_router(insights.router,      prefix="/v1/insights",      tags=["insights"])
app.include_router(flow.router,          prefix="/v1/flow",          tags=["flow"])
app.include_router(dashboard.router,   prefix="/v1/dashboard",  tags=["dashboard"])
app.include_router(reports.router,     prefix="/v1/reports",    tags=["reports"])
app.include_router(connectors.router,  prefix="/v1/connectors", tags=["connectors"])


@app.on_event("startup")
def startup() -> None:
    from app.scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    from app.scheduler import stop_scheduler
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# 관리용 엔드포인트
@app.post("/admin/etl")
def trigger_etl_admin():
    """즉시 ETL 실행 (개발/디버그용)."""
    from app.etl.populate import run_etl
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        result = run_etl(db)
        return {"ok": True, "result": result}
    finally:
        db.close()
