from turtle import title
from pydantic import BaseModel

class Task(BaseModel):
    id: Optional[int] = None
    title: str
    completed: int
    updated_at: str
    deleted: int