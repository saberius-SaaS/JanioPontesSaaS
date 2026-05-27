import os
import sys
from sqlalchemy import text
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine

with engine.connect() as conn:
    conn.execute(text("SET SESSION app.bypass_rls = 'on';"))
    res = conn.execute(text("SELECT email, nivel FROM usuarios")).fetchall()
    print("Todos os usuários:")
    for r in res:
        print(f"{r[0]} - {r[1]}")
