import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

load_dotenv(override=True)
pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
host = os.getenv("DB_HOST")
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{host}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

print(f"Conectando a: {host}...")

engine = create_engine(url, connect_args={"connect_timeout": 5})

try:
    with engine.connect() as conn:
        print("Conexao OK!")
        
        # 1. Total de tarefas
        total = conn.execute(text("SELECT count(*) FROM tarefas")).scalar()
        print(f"\nTotal tarefas: {total}")
        
        # 2. Tarefas por status
        rows = conn.execute(text("SELECT status, count(*) FROM tarefas GROUP BY status")).fetchall()
        print(f"Por status: {rows}")
        
        # 3. Responsaveis unicos em tarefas pendentes
        resps = conn.execute(text("SELECT DISTINCT responsavel FROM tarefas WHERE status IN ('PENDENTE','ATRASADO') LIMIT 20")).fetchall()
        print(f"\nResponsaveis em tarefas pendentes:")
        for r in resps:
            print(f"  - {r[0]}")
            
        # 4. Usuario fiscal
        user = conn.execute(text("SELECT id, nome, email, nivel FROM usuarios WHERE email = 'fiscal@janiopontes.com.br'")).fetchone()
        if user:
            print(f"\nUsuaria fiscal: nome={user[1]}, email={user[2]}, nivel={user[3]}")
            
            # Equipes dela
            equipes = conn.execute(text("""
                SELECT e.nome, e.departamento 
                FROM equipes e 
                JOIN equipe_membros em ON em.equipe_id = e.id 
                WHERE em.usuario_id = :uid
            """), {"uid": user[0]}).fetchall()
            print(f"Equipes: {equipes}")
        else:
            print("\nUsuaria fiscal@janiopontes.com.br NAO encontrada!")
            
except Exception as e:
    print(f"ERRO de conexao: {e}")
