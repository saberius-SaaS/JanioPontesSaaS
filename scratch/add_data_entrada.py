"""Script para adicionar coluna data_entrada na tabela clientes."""
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

password = quote_plus("AppUser@@2026")
engine = create_engine(f"postgresql://postgres:{password}@35.247.225.63:5432/postgres")
conn = engine.connect()
conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS data_entrada DATE"))
conn.commit()
conn.close()
print("Coluna data_entrada criada com sucesso!")
