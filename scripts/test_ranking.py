import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from sqlalchemy import text, func, case, union_all, select
from app.models import Tarefa, HistoricoTarefa
from datetime import date

db = SessionLocal()
db.execute(text("SET SESSION app.bypass_rls = 'on';"))

hoje = date.today()
inicio_mes = date(hoje.year, hoje.month, 1)
if hoje.month == 12:
    fim_mes = date(hoje.year + 1, 1, 1)
else:
    fim_mes = date(hoje.year, hoje.month + 1, 1)

# Consulta Tarefas ativas
stmt1 = select(
    Tarefa.departamento,
    Tarefa.responsavel,
    Tarefa.status,
    Tarefa.id
).where(
    Tarefa.vencimento >= inicio_mes,
    Tarefa.vencimento < fim_mes
)

# Consulta Histórico
stmt2 = select(
    HistoricoTarefa.departamento,
    HistoricoTarefa.responsavel,
    HistoricoTarefa.status,
    HistoricoTarefa.id
).where(
    HistoricoTarefa.vencimento >= inicio_mes,
    HistoricoTarefa.vencimento < fim_mes
)

# União
subq = union_all(stmt1, stmt2).subquery()

# Agrupamento Setorial
setores = db.query(
    subq.c.departamento,
    func.count(subq.c.id).label('total'),
    func.sum(case((subq.c.status == 'ENTREGUE', 1), else_=0)).label('entregues')
).group_by(subq.c.departamento).all()

print("== SETORES ==")
for s in setores:
    print(f"{s.departamento}: {s.total} total, {s.entregues} entregues")

# Agrupamento Equipe
equipe = db.query(
    subq.c.responsavel,
    func.count(subq.c.id).label('total'),
    func.sum(case((subq.c.status == 'ENTREGUE', 1), else_=0)).label('entregues')
).group_by(subq.c.responsavel).all()

print("\n== EQUIPE ==")
for r in equipe:
    if r.total > 0:
        print(f"{r.responsavel}: {r.total} total, {r.entregues} entregues")
