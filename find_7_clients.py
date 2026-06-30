import os, psycopg2
from dotenv import load_dotenv
load_dotenv('.env')

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()

cur.execute("SET LOCAL app.bypass_rls = 'on'")
cur.execute('''
    SELECT cliente, fiscal, contabil, pessoal, societario 
    FROM clientes 
    WHERE status = 'ATIVO'
''')
rows = cur.fetchall()

sem_equipe = []
for r in rows:
    cliente, f, c, p, s = r
    # consider empty if None or only spaces or '-' or 'N/A'
    def is_empty(val):
        if not val: return True
        v = val.strip().upper()
        return v in ('', '-', 'N/A', 'NENHUMA')
    
    if is_empty(f) and is_empty(c) and is_empty(p) and is_empty(s):
        sem_equipe.append(cliente)

print(f"Total encontrados: {len(sem_equipe)}")
for c in sem_equipe:
    print(f"- {c}")

conn.close()
