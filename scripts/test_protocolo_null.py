import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("SET SESSION app.bypass_rls = 'on';"))
print('Historico nulos:', db.execute(text("SELECT COUNT(*) FROM historico_tarefas WHERE protocolo != '' AND protocolo IS NOT NULL AND (conf_recto IS NULL OR conf_recto = '')")).scalar())
print('Tarefas nulos:', db.execute(text("SELECT COUNT(*) FROM tarefas WHERE protocolo != '' AND protocolo IS NOT NULL")).scalar())
