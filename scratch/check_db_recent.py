import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, data, cliente, obrigacao, acao, status_envio, protocolo, link_arquivo, email FROM protocolos ORDER BY data DESC LIMIT 3;")
    print("Últimos Protocolos:")
    for row in cursor.fetchall():
        print(row)
        
    cursor.execute("SELECT id, cliente, obrigacao, acao, status, responsavel, protocolo FROM tarefas ORDER BY id DESC LIMIT 3;")
    print("\nÚltimas Tarefas:")
    for row in cursor.fetchall():
        print(row)

except Exception as e:
    print(f"Erro: {e}")
