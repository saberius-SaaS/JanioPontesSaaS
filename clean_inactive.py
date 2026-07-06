import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Add path to load app
sys.path.append("g:\\Meu Drive\\JanioPontesSaas")

from app.database import SessionLocal
from app.models import Cliente, Tarefa

def run_cleanup():
    db: Session = SessionLocal()
    try:
        # Find inactive clients
        inativos = db.query(Cliente).filter(Cliente.status == 'INATIVO').all()
        nomes_inativos = [c.cliente for c in inativos]
        
        print(f"Encontrados {len(nomes_inativos)} clientes inativos.")
        
        if not nomes_inativos:
            return
            
        # Find tasks that are not ENTREGUE for these clients
        tarefas = db.query(Tarefa).filter(
            Tarefa.cliente.in_(nomes_inativos),
            Tarefa.status != 'ENTREGUE'
        ).all()
        
        print(f"Encontradas {len(tarefas)} tarefas pendentes/atrasadas para clientes inativos.")
        
        # Delete them
        for t in tarefas:
            db.delete(t)
            
        db.commit()
        print("Limpeza concluída com sucesso.")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_cleanup()
