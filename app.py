from fastapi import FastAPI
from config.db_config import conn
from schema.task_schema import tasks
from fastapi.middleware.cors import CORSMiddleware
from models.task_model import Task

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/tasks")
def getTasks():
    """Obtener todas las tareas"""
    result = conn.execute(tasks.select()).fetchall()
    return [dict(row._mapping) for row in result]

@app.post("/task")
def createTask(task: Task):
    """Crear una nueva tarea"""
    new_task = {
        "title": task.title,
        "completed": task.completed,
        "deleted": task.deleted
    }
    result = conn.execute(tasks.insert().values(new_task))
    conn.commit()
    return {"message": "Tarea creada exitosamente"}