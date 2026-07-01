import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
conn.autocommit = False
cur = conn.cursor()
try:
    cur.execute("SET LOCAL app.bypass_rls = 'on'")
    cur.execute("UPDATE tarefas SET mes_ano = RIGHT(mes_ano, 7) WHERE length(mes_ano) > 7")
    print(f'Tarefas atualizadas: {cur.rowcount}')
    
    cur.execute("UPDATE historico_tarefas SET mes_ano = RIGHT(mes_ano, 7) WHERE length(mes_ano) > 7")
    print(f'Historico atualizado: {cur.rowcount}')
    conn.commit()
except Exception as e:
    print('Erro:', e)
finally:
    conn.close()
