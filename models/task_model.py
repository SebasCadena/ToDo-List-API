from turtle import title
from pydantic import BaseModel

class Task(BaseModel):
    id: int
    title: str
    completed: int
    updated_at: str
    deleted: int