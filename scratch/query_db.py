import os
from dotenv import load_dotenv
load_dotenv('G:/Meu Drive/JanioPontesSaas/.env')
import psycopg2

try:
    conn = psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT")
    )

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM historico_tarefas")
    print(f"COUNT historico_tarefas: {cur.fetchone()}")
    
    cur.execute("SELECT id_tarefa, cliente, email, link_arquivo FROM protocolos ORDER BY data DESC LIMIT 5")
    rows = cur.fetchall()
    print("PROTOCOLOS:")
    for row in rows:
        print(row)
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
