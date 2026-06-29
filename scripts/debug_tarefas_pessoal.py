import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    
    r = conn.execute(text("SELECT id_controle, cliente, obrigacao, mes_ano, status, responsavel FROM tarefas WHERE departamento = 'PESSOAL' ORDER BY cliente LIMIT 15"))
    print("=== TAREFAS (Ativas) - PESSOAL ===")
    for row in r:
        print(f"  {row[4]:8} | {row[3]} | {row[1][:20]} | {row[2][:20]} | {row[5]}")

    r2 = conn.execute(text("SELECT id_controle, cliente, obrigacao, mes_ano, status, responsavel, protocolo FROM historico_tarefas WHERE departamento = 'PESSOAL' ORDER BY cliente LIMIT 15"))
    print("\n=== HISTORICO (Entregues) - PESSOAL ===")
    for row in r2:
        print(f"  {row[4]:8} | {row[3]} | {row[1][:20]} | {row[2][:20]} | proto={row[6]}")
