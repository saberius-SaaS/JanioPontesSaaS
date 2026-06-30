import os, psycopg2
from dotenv import load_dotenv

load_dotenv('.env', override=True)

print("Conectando ao banco...")
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
print("Conectado.")
cur = conn.cursor()

cur.execute("SET LOCAL app.bypass_rls = 'on'")

import unicodedata
def normalize(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn').upper().strip()

print("Buscando clientes...")
cur.execute("SELECT cliente, responsavel, fiscal, contabil, pessoal, societario FROM clientes WHERE status = 'ATIVO'")
clientes_data = cur.fetchall()

clientes_map = {}
for r in clientes_data:
    clientes_map[r[0]] = {
        'responsavel': r[1],
        'fiscal': r[2],
        'contabil': r[3],
        'pessoal': r[4],
        'societario': r[5]
    }

print("Buscando tarefas pendentes...")
cur.execute("SELECT id, cliente, departamento, responsavel FROM tarefas WHERE status IN ('PENDENTE', 'ATRASADO', 'REVISAO')")
tarefas = cur.fetchall()

updated = 0
for t in tarefas:
    t_id, t_cliente, t_dep, t_resp = t
    
    cli = clientes_map.get(t_cliente)
    if not cli: continue
    
    dep_norm = normalize(t_dep)
    
    novo_resp = cli['responsavel'] or "SISTEMA"
    if "FISCAL" in dep_norm: novo_resp = cli['fiscal'] or novo_resp
    elif "CONTABIL" in dep_norm: novo_resp = cli['contabil'] or novo_resp
    elif "PESSOAL" in dep_norm: novo_resp = cli['pessoal'] or novo_resp
    elif "SOCIETARIO" in dep_norm: novo_resp = cli['societario'] or novo_resp
    
    if t_resp != novo_resp:
        print(f"Atualizando tarefa de {t_cliente} ({t_dep}) para {novo_resp}")
        cur.execute("UPDATE tarefas SET responsavel = %s WHERE id = %s", (novo_resp, t_id))
        updated += 1

print("Fazendo commit...")
conn.commit()
print(f"✅ {updated} tarefas foram realocadas para as equipes corretas.")
conn.close()
