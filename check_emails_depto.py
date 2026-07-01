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
    SELECT cliente, email, email_fiscal, email_contabil, email_pessoal, email_societario
    FROM clientes 
    WHERE status = 'ATIVO'
      AND (email_fiscal IS NOT NULL AND email_fiscal != ''
           OR email_contabil IS NOT NULL AND email_contabil != ''
           OR email_pessoal IS NOT NULL AND email_pessoal != ''
           OR email_societario IS NOT NULL AND email_societario != '')
    ORDER BY cliente
    LIMIT 20
""")

rows = cur.fetchall()
print(f"Amostra de {len(rows)} clientes com emails departamentais preenchidos:\n")
for r in rows:
    print(f"Cliente: {r[0]}")
    print(f"  Email Geral:      {r[1]}")
    print(f"  Email Fiscal:     {r[2]}")
    print(f"  Email Contabil:   {r[3]}")
    print(f"  Email Pessoal:    {r[4]}")
    print(f"  Email Societario: {r[5]}")
    print()

# Contar quantos tem emails departamentais
cur.execute("""
    SELECT COUNT(*) FROM clientes WHERE status = 'ATIVO'
      AND (email_fiscal IS NOT NULL AND email_fiscal != ''
           OR email_contabil IS NOT NULL AND email_contabil != ''
           OR email_pessoal IS NOT NULL AND email_pessoal != ''
           OR email_societario IS NOT NULL AND email_societario != '')
""")
total = cur.fetchone()[0]
print(f"Total de clientes ativos com algum email departamental: {total}")

conn.close()
