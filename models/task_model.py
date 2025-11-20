from pydantic import BaseModel
from typing import Optional

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    completed: bool
    updated_at: str  # ISO8601 format
    deleted: int = 0