import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from sqlalchemy import text
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

print(f"Periodo: {inicio_mes} a {fim_mes} | Hoje: {hoje}")

pendentes = db.query(Tarefa).filter(
    Tarefa.status.notin_(['ENTREGUE']),
    Tarefa.vencimento != None,
    Tarefa.vencimento < fim_mes
).count()

entregues_ativas = db.query(Tarefa).filter(
    Tarefa.status == 'ENTREGUE',
    Tarefa.vencimento != None,
    Tarefa.vencimento >= inicio_mes,
    Tarefa.vencimento < fim_mes
).count()

entregues_historico = db.query(HistoricoTarefa).filter(
    HistoricoTarefa.status == 'ENTREGUE',
    HistoricoTarefa.vencimento != None,
    HistoricoTarefa.vencimento >= inicio_mes,
    HistoricoTarefa.vencimento < fim_mes
).count()

atrasadas = db.query(Tarefa).filter(
    Tarefa.status == 'PENDENTE',
    Tarefa.vencimento != None,
    Tarefa.vencimento <= hoje
).count()

print(f"\nPendentes (nao-entregue, vcto < fim_mes): {pendentes}")
print(f"Entregues ativas (ENTREGUE, vcto no mes): {entregues_ativas}")
print(f"Entregues historico (ENTREGUE, vcto no mes): {entregues_historico}")
print(f"Total Entregues: {entregues_ativas + entregues_historico}")
print(f"Risco Legal (PENDENTE, vcto <= hoje): {atrasadas}")
print(f"\n--- GAS ref: Pendentes=543, Entregas=1335, Risco=214 ---")
