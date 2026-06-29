import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    
    # Check what would be auto-archived
    query = """
    SELECT t.id, t.cliente, t.obrigacao, t.mes_ano as t_mes_ano, h.mes_ano as h_mes_ano
    FROM tarefas t
    JOIN historico_tarefas h 
      ON t.cliente = h.cliente 
      AND t.obrigacao = h.obrigacao
      AND (
        t.mes_ano = h.mes_ano OR 
        '01/' || t.mes_ano = h.mes_ano OR 
        RIGHT(h.mes_ano, 7) = t.mes_ano
      )
    WHERE t.status IN ('PENDENTE', 'ATRASADO')
    """
    
    r = conn.execute(text(query)).fetchall()
    print(f"Encontradas {len(r)} tarefas duplicadas (que ja estao no historico):")
    for row in r[:20]:
        print(f"  {row[1]} | {row[2]} | Tarefa: {row[3]} | Hist: {row[4]}")
