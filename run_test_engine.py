import os
import sys
from sqlalchemy import text
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import SessionLocal
from app import models
from app.core.task_engine import run_task_engine

def main():
    print("====================================")
    print("[*] INICIANDO MOTOR DE TAREFAS (TESTE) ")
    print("====================================")
    db = SessionLocal()
    try:
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        cliente = db.query(models.Cliente).first()
        if not cliente:
            print("[X] Erro: Nenhum cliente encontrado na base.")
            return
            
        print(f"[*] Processando cruzamento de {db.query(models.Cliente).count()} Clientes x {db.query(models.RegraObrigacao).count()} Regras...")
        
        resultado = run_task_engine(db, str(cliente.tenant_id))
        
        print("\n[OK] PROCESSAMENTO CONCLUIDO!")
        print(f"[*] Mes de Referencia: {resultado['mes_referencia']}")
        print(f"[*] Novas Tarefas Geradas: {resultado['novas']}")
        print(f"[*] Tarefas Existentes Atualizadas: {resultado['atualizadas']}")
        print("====================================")
    except Exception as e:
        print(f"Erro durante execução: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
