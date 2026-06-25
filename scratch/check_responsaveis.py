import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import SessionLocal
from sqlalchemy import text
from app.models import Tarefa, HistoricoTarefa, Equipe

db = SessionLocal()
db.execute(text("SET SESSION app.bypass_rls = 'on';"))

print('Tarefas:', [r[0] for r in db.query(Tarefa.responsavel).distinct().all()])
print('Equipes:', [r[0] for r in db.query(Equipe.nome).all()])
