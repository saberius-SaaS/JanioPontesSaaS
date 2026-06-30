import os, psycopg2
from dotenv import load_dotenv

load_dotenv('.env', override=True)

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

cur.execute("SET LOCAL app.bypass_rls = 'on'")

cur.execute("""
    SELECT id, cliente, obrigacao, status, departamento, responsavel, vencimento 
    FROM tarefas 
    WHERE departamento = 'FISCAL' 
      AND status != 'ENTREGUE'
""")
t = cur.fetchall()
print("Tarefas nao entregues no FISCAL:")
for r in t: print(r)

cur.execute("""
    SELECT id, cliente, obrigacao, status, departamento, responsavel, vencimento 
    FROM historico_tarefas 
    WHERE departamento = 'FISCAL' 
      AND status != 'ENTREGUE'
""")
ht = cur.fetchall()
print("\nHistorico nao entregue no FISCAL:")
for r in ht: print(r)

conn.close()
