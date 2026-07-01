import os
import re
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine
from urllib.parse import quote_plus

load_dotenv(override=True)

pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(url)

try:
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text("SET LOCAL app.bypass_rls = 'on'"))
        # Tarefas
        query_t = sqlalchemy.text("SELECT id, mes_ano FROM tarefas WHERE length(mes_ano) > 7")
        tarefas = conn.execute(query_t).fetchall()
        count_t = 0
        for row in tarefas:
            match = re.search(r'(\d{2}/\d{4})$', row.mes_ano)
            if match:
                new_mes = match.group(1)
                update_t = sqlalchemy.text("UPDATE tarefas SET mes_ano = :mes WHERE id = :id")
                conn.execute(update_t, {"mes": new_mes, "id": row.id})
                count_t += 1
                
        # Historico
        query_h = sqlalchemy.text("SELECT id, mes_ano FROM historico_tarefas WHERE length(mes_ano) > 7")
        historico = conn.execute(query_h).fetchall()
        count_h = 0
        for row in historico:
            match = re.search(r'(\d{2}/\d{4})$', row.mes_ano)
            if match:
                new_mes = match.group(1)
                update_h = sqlalchemy.text("UPDATE historico_tarefas SET mes_ano = :mes WHERE id = :id")
                conn.execute(update_h, {"mes": new_mes, "id": row.id})
                count_h += 1

        print(f"Fixed {count_t} tarefas and {count_h} historico_tarefas!")
except Exception as e:
    print("Erro:", e)
