import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine
from urllib.parse import quote_plus

load_dotenv(override=True)
pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(url)

try:
    with engine.connect() as conn:
        print('Solicitacoes:', conn.execute(sqlalchemy.text('SELECT count(*) FROM solicitacoes')).scalar())
        print('Historico:', conn.execute(sqlalchemy.text('SELECT count(*) FROM historico_tarefas')).scalar())
except Exception as e:
    print("Erro:", e)
