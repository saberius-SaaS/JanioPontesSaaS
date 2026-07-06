import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add path to load app
sys.path.append("g:\\Meu Drive\\JanioPontesSaas")

from app.database import SessionLocal
from app.models import Cliente, Tarefa

def run_cleanup():
    db: Session = SessionLocal()
    # Ativar bypass RLS para ler todos os tenants
    db.info["bypass_rls"] = True
    
    try:
        # Tentar forçar o bypass explicitamente na conexao atual
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        
        # Encontrar clientes inativos
        inativos = db.query(Cliente).filter(Cliente.status == 'INATIVO').all()
        nomes_inativos = [c.cliente for c in inativos]
        
        print(f"Encontrados {len(nomes_inativos)} clientes inativos.")
        
        if not nomes_inativos:
            return
            
        # Encontrar tarefas pendentes/atrasadas destes clientes
        tarefas = db.query(Tarefa).filter(
            Tarefa.cliente.in_(nomes_inativos),
            Tarefa.status != 'ENTREGUE'
        ).all()
        
        print(f"Encontradas {len(tarefas)} tarefas pendentes/atrasadas para clientes inativos.")
        
        if tarefas:
            for t in tarefas:
                db.delete(t)
            db.commit()
            print("Limpeza das tarefas concluída com sucesso no banco de produção.")
        else:
            print("Nenhuma tarefa precisava ser limpa.")
            
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_cleanup()
