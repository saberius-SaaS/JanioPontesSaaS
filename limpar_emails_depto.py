"""
Script de limpeza dos campos email_fiscal, email_contabil, email_pessoal, email_societario.
NAO altera: email (geral), fiscal, contabil, pessoal, societario (equipes).

Modo seguro: primeiro faz dry-run, depois pede confirmacao.
"""
import os, sys, psycopg2
from dotenv import load_dotenv

load_dotenv('.env', override=True)

conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT', '5432')
)
cur = conn.cursor()
cur.execute("SET LOCAL app.bypass_rls = 'on'")

# 1. Dry-run: mostra o que sera afetado
cur.execute("""
    SELECT cliente, email_fiscal, email_contabil, email_pessoal, email_societario
    FROM clientes
    WHERE email_fiscal IS NOT NULL AND email_fiscal != ''
       OR email_contabil IS NOT NULL AND email_contabil != ''
       OR email_pessoal IS NOT NULL AND email_pessoal != ''
       OR email_societario IS NOT NULL AND email_societario != ''
    ORDER BY cliente
""")
rows = cur.fetchall()

print("=" * 60)
print("DRY-RUN: Clientes que terao emails departamentais limpos")
print("(Campos: email_fiscal, email_contabil, email_pessoal, email_societario)")
print("NAO serao alterados: email geral, equipes (fiscal, contabil, pessoal, societario)")
print("=" * 60)
print(f"\nTotal de clientes afetados: {len(rows)}\n")

for r in rows:
    print(f"  - {r[0]}")

print(f"\n{'=' * 60}")
resp = input("Confirma a limpeza? (digite SIM para executar): ")

if resp.strip() != "SIM":
    print("Operacao cancelada.")
    conn.close()
    sys.exit(0)

# 2. Executa a limpeza
cur.execute("""
    UPDATE clientes
    SET email_fiscal = NULL,
        email_contabil = NULL,
        email_pessoal = NULL,
        email_societario = NULL
    WHERE email_fiscal IS NOT NULL AND email_fiscal != ''
       OR email_contabil IS NOT NULL AND email_contabil != ''
       OR email_pessoal IS NOT NULL AND email_pessoal != ''
       OR email_societario IS NOT NULL AND email_societario != ''
""")
affected = cur.rowcount
conn.commit()
print(f"\nPronto! {affected} clientes tiveram os emails departamentais limpos.")
print("Os campos de equipe e email geral permanecem intactos.")
conn.close()
