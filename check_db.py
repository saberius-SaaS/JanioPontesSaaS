import os, psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

cur.execute("SET LOCAL app.bypass_rls = 'on'")
cur.execute("SELECT id, cliente, obrigacao, acao, status_envio, protocolo, email, link_arquivo, data FROM protocolos ORDER BY data DESC LIMIT 5")
rows = cur.fetchall()
print("=== ULTIMOS PROTOCOLOS ===")
for r in rows:
    print(f"  ID: {r[0]}")
    print(f"  Cliente: {r[1]}")
    print(f"  Obrigacao: {r[2]}")
    print(f"  Acao: {r[3]}")
    print(f"  Status Envio: {r[4]}")
    print(f"  Protocolo: {r[5]}")
    print(f"  Email: {r[6]}")
    print(f"  Link Arquivo: '{r[7]}'")
    print(f"  Data: {r[8]}")
    print("  ---")

print()

cur.execute("SET LOCAL app.bypass_rls = 'on'")
cur.execute("SELECT id, cliente, obrigacao, acao, status FROM tarefas WHERE status = 'ENTREGUE' ORDER BY id DESC LIMIT 5")
rows2 = cur.fetchall()
print("=== ULTIMAS TAREFAS ENTREGUES ===")
for r in rows2:
    print(f"  {r}")

conn.close()
