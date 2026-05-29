import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

db = SessionLocal()

print("--- ÚLTIMOS PROTOCOLOS ---")
protocolos = db.query(models.Protocolo).order_by(models.Protocolo.data.desc()).limit(5).all()
for p in protocolos:
    print(f"ID: {p.id}, Cliente: {p.cliente}, OBR: {p.obrigacao}, Email: {p.email}, Link: {p.link_arquivo}, Ação: {p.acao}")

print("\n--- ÚLTIMOS HISTÓRICOS DE TAREFAS ---")
historicos = db.query(models.HistoricoTarefa).order_by(models.HistoricoTarefa.data_conclusao.desc()).limit(5).all()
for h in historicos:
    print(f"Cliente: {h.cliente}, OBR: {h.obrigacao}, Ação: {h.acao}, Status: {h.status}, Protocolo: {h.protocolo}")

print("\n--- ÚLTIMAS TAREFAS (REVISÃO) ---")
tarefas = db.query(models.Tarefa).filter(models.Tarefa.status == 'REVISAO').order_by(models.Tarefa.id.desc()).limit(5).all()
for t in tarefas:
    print(f"Cliente: {t.cliente}, OBR: {t.obrigacao}, Status: {t.status}, Protocolo: {t.protocolo}")

db.close()
