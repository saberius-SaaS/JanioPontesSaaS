import sys
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente antes de importar qualquer coisa do app
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.certificado import CertificadoDigital

def clean_duplicates():
    db = SessionLocal()
    try:
        certificados = db.query(CertificadoDigital).all()
        
        groups = {}
        for c in certificados:
            key = (str(c.tenant_id), str(c.cliente_id), c.tipo, c.vencimento)
            if key not in groups:
                groups[key] = []
            groups[key].append(c)
        
        removed_count = 0
        for key, certs in groups.items():
            if len(certs) > 1:
                certs_to_delete = certs[1:]
                for c in certs_to_delete:
                    db.delete(c)
                    removed_count += 1
                    
        db.commit()
        print(f"Limpeza concluida. {removed_count} registros duplicados removidos.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_duplicates()
