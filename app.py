import datetime
from http.client import HTTPException
from typing import Optional
from fastapi import FastAPI, HTTPException as FastAPIHTTPException
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
            "GET /tasks": "Listar tareas (usa ?deleted=0/1/all)",
            "GET /tasks/deleted": "Listar solo tareas eliminadas",
            "POST /tasks": "Crear nueva tarea",
            "GET /tasks/{id}": "Obtener tarea por ID",
            "PUT /tasks/{id}": "Actualizar tarea",
            "PUT /tasks/{id}/restore": "Restaurar tarea eliminada",
            "DELETE /tasks/{id}": "Eliminar tarea (soft delete)"
        }
    }

# Modelo para crear/actualizar tareas
class TaskCreate(BaseModel):
    title: str
    completed: Optional[bool] = False

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None

@app.get("/tasks")
def getTasks(deleted: Optional[str] = "0"):
    """
    Listar tareas con filtro por estado de eliminación.
    
    Parámetros:
    - deleted: "0" (activas), "1" (eliminadas), "all" (todas)
    """
    if deleted == "all":
        query = tasks.select()
    elif deleted == "1":
        query = tasks.select().where(tasks.c.deleted == 1)
    else:  # "0" por defecto
        query = tasks.select().where(tasks.c.deleted == 0)
    
    result = conn.execute(query).fetchall()
    task_list = []
    for row in result:
        task_dict = dict(row._mapping)
        # Convertir updated_at a formato ISO8601
        if task_dict.get('updated_at'):
            task_dict['updated_at'] = task_dict['updated_at'].isoformat()
        # Convertir completed de int a bool
        task_dict['completed'] = bool(task_dict.get('completed', 0))
        task_list.append(task_dict)
    return task_list

@app.get("/tasks/deleted")
def getDeletedTasks():
    """Listar solo las tareas eliminadas (papelera)"""
    result = conn.execute(tasks.select().where(tasks.c.deleted == 1)).fetchall()
    task_list = []
    for row in result:
        task_dict = dict(row._mapping)
        # Convertir updated_at a formato ISO8601
        if task_dict.get('updated_at'):
            task_dict['updated_at'] = task_dict['updated_at'].isoformat()
        # Convertir completed de int a bool
        task_dict['completed'] = bool(task_dict.get('completed', 0))
        task_list.append(task_dict)
    return task_list

@app.get("/tasks/{id}")
def list_id(id: int):
    result = conn.execute(tasks.select().where(tasks.c.id == id)).first()
    if not result:
        raise FastAPIHTTPException(status_code=404, detail="Tarea no encontrada")
    
    task_dict = dict(result._mapping)
    # Convertir updated_at a formato ISO8601
    if task_dict.get('updated_at'):
        task_dict['updated_at'] = task_dict['updated_at'].isoformat()
    # Convertir completed de int a bool
    task_dict['completed'] = bool(task_dict.get('completed', 0))
    return task_dict

@app.post("/tasks", status_code=201)
def createTask(task: TaskCreate):
    """Crear nueva tarea"""
    new_task = {
        "title": task.title,
        "completed": 1 if task.completed else 0
    }
    result = conn.execute(tasks.insert().values(new_task))
    conn.commit()
    
    # Obtener la tarea recién creada
    created_id = result.lastrowid
    created_task = conn.execute(tasks.select().where(tasks.c.id == created_id)).first()
    
    task_dict = dict(created_task._mapping)
    # Convertir updated_at a formato ISO8601
    if task_dict.get('updated_at'):
        task_dict['updated_at'] = task_dict['updated_at'].isoformat()
    # Convertir completed de int a bool
    task_dict['completed'] = bool(task_dict.get('completed', 0))
    
    return task_dict

@app.put("/tasks/{id}/restore")
def restoreTask(id: int):
    """Restaurar una tarea eliminada (cambiar deleted de 1 a 0)"""
    result = conn.execute(
        tasks.update().where(tasks.c.id == id).values(deleted=0)
    )
    conn.commit()
    
    if result.rowcount == 0:
        raise FastAPIHTTPException(status_code=404, detail="Tarea no encontrada")
    
    # Retornar la tarea restaurada
    restored_task = conn.execute(tasks.select().where(tasks.c.id == id)).first()
    task_dict = dict(restored_task._mapping)
    
    # Convertir updated_at a formato ISO8601
    if task_dict.get('updated_at'):
        task_dict['updated_at'] = task_dict['updated_at'].isoformat()
    # Convertir completed de int a bool
    task_dict['completed'] = bool(task_dict.get('completed', 0))
    
    return task_dict

@app.delete("/tasks/{id}", status_code=204)
def deleteTask(id: int):
    """Soft delete: marca la tarea como eliminada"""
    result = conn.execute(
        tasks.update().where(tasks.c.id == id).values(deleted=1)
    )
    conn.commit()
    
    if result.rowcount == 0:
        raise FastAPIHTTPException(status_code=404, detail="Tarea no encontrada")
    
    return None  # 204 No Content no retorna body

@app.put("/tasks/{id}")
def updateTask(id: int, task: TaskUpdate):
    """Actualizar tarea existente"""
    # Solo actualizar campos que se enviaron
    updated_task = {}
    if task.title is not None:
        updated_task["title"] = task.title
    if task.completed is not None:
        updated_task["completed"] = 1 if task.completed else 0
    
    if not updated_task:
        raise FastAPIHTTPException(status_code=400, detail="No hay campos para actualizar")
    
    result = conn.execute(tasks.update().where(tasks.c.id == id).values(updated_task))
    conn.commit()
    
    if result.rowcount == 0:
        raise FastAPIHTTPException(status_code=404, detail="Tarea no encontrada")
    
    # Retornar la tarea actualizada
    updated = conn.execute(tasks.select().where(tasks.c.id == id)).first()
    task_dict = dict(updated._mapping)
    
    # Convertir updated_at a formato ISO8601
    if task_dict.get('updated_at'):
        task_dict['updated_at'] = task_dict['updated_at'].isoformat()
    # Convertir completed de int a bool
    task_dict['completed'] = bool(task_dict.get('completed', 0))
    
    return task_dict

        
    