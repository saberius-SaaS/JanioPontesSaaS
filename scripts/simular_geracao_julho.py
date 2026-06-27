"""
Simulação: Geração de tarefas para Julho/2026 (dry-run, sem gravar no banco).
"""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database import SessionLocal
from app.models import Tenant
from app.core.task_engine import run_task_engine

def main():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).first()
        if not tenant:
            print("❌ Tenant não encontrado.")
            return

        db.execute(text("SET SESSION app.bypass_rls = 'on';"))

        # Simula o dia 1º de Julho de 2026
        data_simulada = datetime.date(2026, 7, 1)

        # Abre um SAVEPOINT para reverter tudo depois
        nested = db.begin_nested()

        resultado = run_task_engine(db, str(tenant.id), force_competencia=data_simulada)

        print(f"\n{'='*60}")
        print(f"  SIMULAÇÃO DE GERAÇÃO — Competência: {resultado['mes_referencia']}")
        print(f"{'='*60}")
        print(f"  Tarefas que SERIAM criadas:    {resultado['novas']}")
        print(f"  Tarefas que SERIAM atualizadas: {resultado['atualizadas']}")
        print(f"{'='*60}")

        if resultado['novas'] > 0:
            print(f"\n  ✅ CONFIRMADO: O motor GERARÁ {resultado['novas']} tarefas em 01/07/2026.")
            print(f"     O Cloud Scheduler disparará automaticamente às 01:00.")
        else:
            print(f"\n  ⚠️  ATENÇÃO: Nenhuma tarefa seria gerada. Verifique as regras e perfis.")

        # ROLLBACK do savepoint — nada é gravado no banco
        nested.rollback()
        print(f"\n  🔒 Nenhuma alteração foi salva (simulação apenas).\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
