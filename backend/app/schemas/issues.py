from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


# ─── Issue ───────────────────────────────────────────────────────────────────

class IssueCreate(BaseModel):
    project_id: int
    subject: str
    description: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    version_id: Optional[int] = None
    category_id: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    is_private: bool = False


class IssueUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status_id: Optional[int] = None
    priority_id: Optional[int] = None
    assignee_id: Optional[int] = None
    parent_id: Optional[int] = None
    version_id: Optional[int] = None
    category_id: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    done_ratio: Optional[int] = None
    is_private: Optional[bool] = None
    notes: Optional[str] = None  # 변경 코멘트 → ti_journals.notes


class IssueOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    project_name: Optional[str] = None
    subject: str
    description: Optional[str]
    status_id: Optional[int]
    status_name: Optional[str] = None
    flow_stage: Optional[str] = None
    priority_id: Optional[int]
    priority_name: Optional[str] = None
    priority_color: Optional[str] = None
    assignee_id: Optional[int]
    assignee_name: Optional[str] = None
    author_id: int
    author_name: Optional[str] = None
    parent_id: Optional[int]
    version_id: Optional[int]
    version_name: Optional[str] = None
    category_id: Optional[int]
    category_name: Optional[str] = None
    done_ratio: int
    estimated_hours: Optional[float]
    is_private: bool
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    start_date: Optional[date]
    due_date: Optional[date]
    redmine_id: Optional[int]


# ─── Journal ──────────────────────────────────────────────────────────────────

class JournalDetailOut(BaseModel):
    model_config = {"from_attributes": True}

    property: str
    prop_key: str
    old_value: Optional[str]
    new_value: Optional[str]


class JournalOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    issue_id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    notes: Optional[str]
    created_at: datetime
    details: List[JournalDetailOut] = []


class JournalCreate(BaseModel):
    notes: str


# ─── Attachment ───────────────────────────────────────────────────────────────

class AttachmentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    issue_id: Optional[int]
    filename: str
    content_type: Optional[str]
    filesize: Optional[int]
    created_by: Optional[int]
    created_by_name: Optional[str] = None
    created_at: datetime
    download_url: Optional[str] = None


# ─── Time Entry ───────────────────────────────────────────────────────────────

class TimeEntryCreate(BaseModel):
    hours: float
    activity: Optional[str] = None
    spent_on: date
    comments: Optional[str] = None


class TimeEntryOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    issue_id: Optional[int]
    project_id: int
    user_id: int
    user_name: Optional[str] = None
    hours: float
    activity: Optional[str]
    spent_on: date
    comments: Optional[str]
    created_at: datetime


# ─── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    identifier: str
    name: str
    description: Optional[str] = None
    is_public: bool = False


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class ProjectOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    identifier: str
    name: str
    description: Optional[str]
    status: str
    is_public: bool
    created_at: datetime


class VersionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "open"
    due_date: Optional[date] = None


class VersionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    name: str
    description: Optional[str]
    status: str
    due_date: Optional[date]


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    name: str


class MemberAdd(BaseModel):
    user_id: int
    role: str = "member"


class MemberOut(BaseModel):
    model_config = {"from_attributes": True}

    user_id: int
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: str


# ─── Notification ─────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    event_type: str
    payload: dict
    is_read: bool
    created_at: datetime
