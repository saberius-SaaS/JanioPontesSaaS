import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid

from app.main import app
from app.database import get_db
from app.models.base import Base

# Utiliza banco em memória do SQLite para rodar os testes rapidamente.
# StaticPool + check_same_thread=False garante que todas as conexões
# compartilhem o mesmo banco em memória (evita problema de tabelas não encontradas).
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

from app.api.deps import require_login, verify_scheduler_key
from app.models.usuario import Usuario

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    def override_require_login():
        return Usuario(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            email="test@janiopontes.com.br",
            nome="Test User",
            ativo=True,
            nivel="ADMIN"
        )
        
    def override_verify_scheduler_key():
        return True
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_login] = override_require_login
    app.dependency_overrides[verify_scheduler_key] = override_verify_scheduler_key
    
    yield TestClient(app)
    
    del app.dependency_overrides[get_db]
    del app.dependency_overrides[require_login]
    del app.dependency_overrides[verify_scheduler_key]
