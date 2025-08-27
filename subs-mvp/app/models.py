from __future__ import annotations

from datetime import datetime
from typing import Union
from uuid import UUID

from pydantic import BaseModel, Field


class AssignReq(BaseModel):
    login: str = Field(..., min_length=1)
    uid: UUID | None = None


class AssignResp(BaseModel):
    uid: UUID


class RevokeReq(BaseModel):
    login: str = Field(..., min_length=1)


class StatusByLogin(BaseModel):
    login: str
    user_id: int
    uid: UUID | None = None
    assigned_at: datetime | None = None
    active: bool


class StatusByUid(BaseModel):
    uid: UUID
    pool: str
    status: str
    updated_at: datetime
    user_id: int | None = None
    assigned_at: datetime | None = None


StatusResp = Union[StatusByLogin, StatusByUid]
