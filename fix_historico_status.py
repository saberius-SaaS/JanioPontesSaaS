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
    UPDATE historico_tarefas 
    SET status = 'ENTREGUE' 
    WHERE status != 'ENTREGUE'
""")
updated_count = cur.rowcount
conn.commit()

print(f"✅ Sucesso! {updated_count} registros no histórico foram corrigidos para o status 'ENTREGUE'.")
conn.close()
