import datetime
from http.client import HTTPException
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text
from config.db_config import conn
from schema.task_schema import tasks
from fastapi.middleware.cors import CORSMiddleware
from models.task_model import Task

app = FastAPI(
    title="ToDo List API",
    description="API para gestión de tareas con sincronización offline-first",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    return {
        "message": "ToDo List API - FastAPI",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "GET /tasks": "Listar todas las tareas",
            "POST /tasks": "Crear nueva tarea",
            "GET /tasks/{id}": "Obtener tarea por ID",
            "PUT /tasks/{id}": "Actualizar tarea",
            "DELETE /tasks/{id}": "Eliminar tarea (soft delete)"
        }
    }

# Modelo para crear/actualizar tareas
class TaskCreate(BaseModel):
    title: str
    completed: Optional[int] = 0

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[int] = None
    deleted: Optional[int] = 0

@app.get("/tasks")
def getTasks():
    """Solo usuarios autenticados pueden ver la lista"""
    result = conn.execute(tasks.select()).fetchall()
    return [dict(row._mapping) for row in result]

@app.get("/tasks/{id}")
def list_id(id: int):
    result = conn.execute(tasks.select().where(tasks.c.id == id)).first()
    return dict(result._mapping) if result else {"message": "Tarea no encontrada"}

@app.post("/tasks")
def createTask(task: TaskCreate):
    """Crear nueva tarea"""
    new_task = {
        "title": task.title,
        "completed": task.completed
    }
    conn.execute(tasks.insert().values(new_task))
    conn.commit()
    return {"message": "Tarea creada exitosamente"}

@app.delete("/tasks/{id}")
def deleteTask(id: int):
    result = conn.execute(tasks.delete().where(tasks.c.id == id))
    conn.commit()
    return {"message": "Tarea eliminada"} if result.rowcount > 0 else {"message": "Tarea no encontrada"}

@app.put("/tasks/{id}")
def updateTask(id: int, task: TaskUpdate):
    updated_task = {
        "title": task.title,
        "completed": task.completed,
        "deleted": task.deleted
    }
    result = conn.execute(tasks.update().where(tasks.c.id == id).values(updated_task))
    conn.commit()
    return {"message": "Tarea actualizada"} if result.rowcount > 0 else {"message": "Tarea no encontrada"}

        
    