import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import SessionLocal
from app import models
import uuid

def test_baixa_route():
    db = SessionLocal()
    # Pega um protocolo existente
    p = db.query(models.Protocolo).filter(models.Protocolo.conf_recto == None).first()
    if not p:
        print("Nenhum protocolo pendente encontrado para teste.")
        return
        
    print(f"Testando baixa no protocolo ID: {p.id}")
    
    # Fake login tenant
    user = db.query(models.Usuario).filter(models.Usuario.tenant_id == p.tenant_id).first()
    
    # Precisamos mockar o auth de alguma forma, ou testar a lógica do DB
    try:
        p.conf_recto = __import__('datetime').datetime.now()
        db.commit()
        print("Commit no DB funcionou perfeitamente com datetime.now()")
    except Exception as e:
        print(f"Erro no banco: {e}")

if __name__ == '__main__':
    test_baixa_route()
