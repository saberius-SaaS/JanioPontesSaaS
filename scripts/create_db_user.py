import os
import sys
import logging
from sqlalchemy import create_engine, text

# Garante que as importações do app funcionem se executado da raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_app_user():
    # Usar a string de conexão de admin atual do .env
    from app.database import DATABASE_URL
    
    # Criar engine
    engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    
    senha_app_user = "AppUser@@2026"
    
    queries = [
        # Cria o usuário se não existir
        text("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN CREATE USER app_user WITH PASSWORD 'AppUser@@2026'; END IF; END $$;"),
        text("ALTER USER app_user WITH PASSWORD 'AppUser@@2026';"),
        
        # Concede permissões básicas
        text("GRANT CONNECT ON DATABASE postgres TO app_user;"),
        text("GRANT USAGE ON SCHEMA public TO app_user;"),
        
        # Concede CRUD em todas as tabelas e views existentes
        text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;"),
        
        # Configura as permissões para futuras tabelas (se o admin criar mais tabelas)
        text("ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;"),
        
        # Permissões em sequências (IDs)
        text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;"),
        text("ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_user;")
    ]

    try:
        with engine.connect() as conn:
            for q in queries:
                conn.execute(q)
            logging.info("✅ Usuário 'app_user' criado com sucesso e permissões granulares aplicadas!")
            logging.info("🔐 Senha do novo usuário: AppUser@@2026")
    except Exception as e:
        logging.error(f"❌ Erro ao criar app_user: {str(e)}")

if __name__ == "__main__":
    create_app_user()
