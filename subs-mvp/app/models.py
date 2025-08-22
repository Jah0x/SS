from pydantic import BaseModel, Field
from uuid import UUID

class AssignRequest(BaseModel):
    login: str = Field(..., min_length=1)

class RevokeRequest(BaseModel):
    login: str | None = None
    uid: UUID | None = None

class UIDStatus(BaseModel):
    uid: UUID
    status: str
    pool: str

class AssignResponse(BaseModel):
    uid: UUID
