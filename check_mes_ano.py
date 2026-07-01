import os
import sqlalchemy
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine

load_dotenv(override=True)
pwd = quote_plus(os.getenv('DB_PASSWORD', ''))
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(url)

with engine.connect() as conn:
    print('Tarefas:', conn.execute(sqlalchemy.text('SELECT DISTINCT mes_ano FROM tarefas')).fetchall())
    print('Historico:', conn.execute(sqlalchemy.text('SELECT DISTINCT mes_ano FROM historico_tarefas')).fetchall())
