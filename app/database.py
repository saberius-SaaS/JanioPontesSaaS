"""
Configuração de conexão com o banco de dados PostgreSQL (Cloud SQL).
Carrega variáveis do .env e expõe a engine e a session factory.
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from urllib.parse import quote_plus

load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Encode password to handle special characters like @ safely
encoded_password = quote_plus(DB_PASSWORD)

if DB_HOST.startswith("/cloudsql"):
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@/{DB_NAME}?host={DB_HOST}"
else:
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args={"options": "-c timezone=America/Sao_Paulo"})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from sqlalchemy import event
from sqlalchemy import text

def get_db():
    """Dependency injection para rotas FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@event.listens_for(SessionLocal, "after_begin")
def set_tenant_on_begin(session, transaction, connection):
    """
    Reaplica as configurações de RLS a cada nova transação do banco.
    Resolve o problema de perda de contexto (SET LOCAL) após um db.commit().
    """
    tenant_id = session.info.get("tenant_id")
    bypass_rls = session.info.get("bypass_rls")
    
    if bypass_rls:
        try:
            connection.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        except Exception:
            pass
    elif tenant_id:
        try:
            connection.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
            connection.execute(text("SET LOCAL app.bypass_rls = 'off';"))
        except Exception:
            pass
