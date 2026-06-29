import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Bypass RLS
    conn.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    
    # All distinct responsaveis in tasks
    r = conn.execute(text("SELECT DISTINCT responsavel, departamento, status FROM tarefas WHERE status IN ('PENDENTE','ATRASADO') ORDER BY departamento, responsavel LIMIT 50"))
    print("=== Responsaveis em tarefas pendentes/atrasadas ===")
    for row in r:
        print(f"  resp=[{row[0]}] dept=[{row[1]}] status=[{row[2]}]")

    # Check clientes pessoal field
    r2 = conn.execute(text("SELECT DISTINCT cliente, pessoal FROM clientes WHERE pessoal IS NOT NULL AND pessoal != '' LIMIT 20"))
    print()
    print("=== Campo 'pessoal' nos clientes ===")
    for row in r2:
        print(f"  cliente=[{row[0]}] pessoal=[{row[1]}]")

    # User Marcia
    r3 = conn.execute(text("SELECT u.nome, u.email, u.nivel FROM usuarios u WHERE u.email ILIKE '%%pessoal%%' OR u.nome ILIKE '%%marcia%%'"))
    print()
    print("=== Usuario Marcia/pessoal ===")
    for row in r3:
        print(f"  [{row[0]}] - {row[1]} (nivel={row[2]})")

    # Her teams
    r4 = conn.execute(text("SELECT u.nome, u.email, e.nome as equipe FROM usuarios u JOIN usuarios_equipes ue ON u.id = ue.usuario_id JOIN equipes e ON e.id = ue.equipe_id WHERE u.email ILIKE '%%pessoal%%' OR u.nome ILIKE '%%marcia%%'"))
    print()
    print("=== Equipes da Marcia ===")
    for row in r4:
        print(f"  [{row[0]}] -> equipe [{row[2]}]")

    # Equipes
    r5 = conn.execute(text("SELECT nome, departamento FROM equipes"))
    print()
    print("=== Todas as equipes ===")
    for row in r5:
        print(f"  [{row[0]}] - {row[1]}")
