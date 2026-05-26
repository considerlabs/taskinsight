from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str
    role: str = "member"


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
