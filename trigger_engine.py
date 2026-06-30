import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)

from sqlalchemy import text
from app.database import SessionLocal
from app.core.task_engine import run_task_engine
from app.models import Cliente

db = SessionLocal()
db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
cliente = db.query(Cliente).first()
if cliente:
    res = run_task_engine(db, cliente.tenant_id)
    print("Motor de Tarefas executado com sucesso:", res)
else:
    print("Nenhum cliente encontrado para rodar o motor.")
db.close()
