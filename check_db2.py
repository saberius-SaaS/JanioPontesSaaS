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
cur.execute("SELECT cliente, email, responsavel, fiscal, email_fiscal FROM clientes LIMIT 5")
for row in cur.fetchall():
    print(row)
conn.close()
