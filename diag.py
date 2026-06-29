import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

load_dotenv(override=True)
pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
host = os.getenv("DB_HOST")
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{host}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(url, connect_args={"connect_timeout": 5})

try:
    with engine.connect() as conn:
        # Listar TODOS os schemas
        schemas = conn.execute(text("SELECT schema_name FROM information_schema.schemata")).fetchall()
        print("Schemas:", [s[0] for s in schemas])
        
        # Listar TODAS as tabelas do schema public
        tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")).fetchall()
        print(f"\nTabelas em public ({len(tables)}):")
        for t in tables:
            count = conn.execute(text(f'SELECT count(*) FROM "{t[0]}"')).scalar()
            print(f"  {t[0]}: {count} registros")

        # Listar todos os databases
        dbs = conn.execute(text("SELECT datname FROM pg_database WHERE datistemplate = false")).fetchall()
        print(f"\nDatabases disponiveis: {[d[0] for d in dbs]}")
            
except Exception as e:
    print(f"ERRO: {e}")
