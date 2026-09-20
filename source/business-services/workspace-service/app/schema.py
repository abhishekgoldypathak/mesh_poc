from datetime import datetime
from pydantic import BaseModel

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    status: str
    namespace: str
    created_at: datetime

    class Config:
        from_attributes = True