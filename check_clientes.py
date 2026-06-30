import sys
import os

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.cliente import Cliente

def main():
    db = SessionLocal()
    try:
        clientes = db.query(Cliente).filter(Cliente.status == "ATIVO").all()
        
        sem_nenhuma = []
        incompletos = []
        
        for c in clientes:
            vazios = 0
            if not c.fiscal: vazios += 1
            if not c.contabil: vazios += 1
            if not c.pessoal: vazios += 1
            if not c.societario: vazios += 1
            
            if vazios == 4:
                sem_nenhuma.append(c)
            elif vazios > 0:
                incompletos.append((c, vazios))
                
        print(f"Total de clientes ATIVOS: {len(clientes)}")
        print(f"Clientes sem NENHUMA equipe: {len(sem_nenhuma)}")
        for c in sem_nenhuma:
            print(f"- {c.cliente} (CNPJ: {c.cnpj})")
            
        print(f"\nClientes faltando 1 ou mais equipes: {len(incompletos)}")
        for c, v in incompletos[:20]: # show first 20
            print(f"- {c.cliente} (Faltam {v} equipes)")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()
