import datetime
from http.client import HTTPException
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
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

def task_to_dict(row):
    task_dict = dict(row._mapping)
    # Convertir updated_at a ISO8601 si existe
    if 'updated_at' in task_dict and task_dict['updated_at']:
        if isinstance(task_dict['updated_at'], datetime):
            task_dict['updated_at'] = task_dict['updated_at'].isoformat()
        else:
            # Si es string de fecha, parsearlo
            try:
                dt = datetime.fromisoformat(str(task_dict['updated_at']))
                task_dict['updated_at'] = dt.isoformat()
            except:
                task_dict['updated_at'] = str(task_dict['updated_at'])
    return task_dict

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

@app.get("/tasks")
def get_tasks():
    """
    Obtener todas las tareas no eliminadas
    """
    try:
        result = conn.execute(
            tasks.select().fetchall()
        ).fetchall()
        
        return [task_to_dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener tareas: {str(e)}")


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    """
    Crear una nueva tarea con ID auto-generado
    """
    try:
        # Obtener el máximo ID actual
        max_id_result = conn.execute(
            "SELECT MAX(id) as max_id FROM tasks"
        ).fetchone()
        max_id = max_id_result[0] if max_id_result[0] else 0
        new_id = max_id + 1
        
        # Crear timestamp actual
        now = datetime.utcnow()
        
        # Crear nueva tarea
        new_task = {
            "id": new_id,
            "title": task.title,
            "completed": task.completed if task.completed is not None else 0,
            "updated_at": now,
            "deleted": 0
        }
        
        conn.execute(tasks.insert().values(new_task))
        conn.commit()
        
        # Devolver la tarea creada en formato ISO8601
        return {
            "id": new_id,
            "title": task.title,
            "completed": new_task["completed"],
            "updated_at": now.isoformat(),
            "deleted": 0
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear tarea: {str(e)}")

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """
    Obtener una tarea específica por ID
    """
    try:
        result = conn.execute(
            tasks.select().where(tasks.c.id == task_id).where(tasks.c.deleted == 0)
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Tarea con ID {task_id} no encontrada")
        
        return task_to_dict(result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener tarea: {str(e)}")

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    """
    Actualizar una tarea existente
    """
    try:
        # Verificar que existe
        existing = conn.execute(
            tasks.select().where(tasks.c.id == task_id).where(tasks.c.deleted == 0)
        ).fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Tarea con ID {task_id} no encontrada")
        
        # Preparar datos a actualizar
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        if task.title is not None:
            update_data["title"] = task.title
        
        if task.completed is not None:
            update_data["completed"] = task.completed
        
        # Actualizar
        conn.execute(
            tasks.update().where(tasks.c.id == task_id).values(update_data)
        )
        conn.commit()
        
        # Obtener tarea actualizada
        updated = conn.execute(
            tasks.select().where(tasks.c.id == task_id)
        ).fetchone()
        
        return task_to_dict(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar tarea: {str(e)}")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    """
    Eliminar una tarea (soft delete - marca como deleted=1)
    """
    try:
        # Verificar que existe
        existing = conn.execute(
            tasks.select().where(tasks.c.id == task_id).where(tasks.c.deleted == 0)
        ).fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail=f"Tarea con ID {task_id} no encontrada")
        
        # Soft delete
        conn.execute(
            tasks.update().where(tasks.c.id == task_id).values({
                "deleted": 1,
                "updated_at": datetime.utcnow()
            })
        )
        conn.commit()
        
        return {
            "message": f"Tarea {task_id} eliminada exitosamente",
            "id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar tarea: {str(e)}")

# Health check
@app.get("/health")
def health_check():
    """Verificar estado de la API y conexión a la base de datos"""
    try:
        # Test de conexión a la BD
        conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }