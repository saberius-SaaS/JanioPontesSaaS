import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    
    query_delete = """
    DELETE FROM tarefas
    WHERE id IN (
        SELECT t.id
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
    )
    """
    
    r = conn.execute(text(query_delete))
    conn.commit()
    print(f"Limpeza concluida. {r.rowcount} tarefas duplicadas removidas do painel.")
