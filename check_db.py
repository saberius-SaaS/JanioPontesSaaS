import os
import sys
from sqlalchemy import text
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import engine

with engine.connect() as conn:
    res = conn.execute(text("SELECT email, tenant_id FROM usuarios")).fetchall()
    print("Users:", res)
    t = conn.execute(text("SELECT tenant_id, count(*) FROM tarefas GROUP BY tenant_id")).fetchall()
    print("Tarefas por tenant:", t)
