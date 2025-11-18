from sqlalchemy import Table
from config.db_config import metadata, engine

#Importar ya existentes
tasks = Table("tasks", metadata, autoload_with=engine)