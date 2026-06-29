import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
load_dotenv(override=True)
pwd = quote_plus(os.getenv('DB_PASSWORD', ''))
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(url, connect_args={'connect_timeout': 5})
try:
    with engine.connect() as conn:
        print('Tarefas sem responsavel:', conn.execute(text("SELECT count(*) FROM tarefas WHERE status IN ('PENDENTE','ATRASADO') AND responsavel IS NULL")).scalar())
        resps = conn.execute(text("SELECT responsavel, count(*) FROM tarefas WHERE status IN ('PENDENTE','ATRASADO') GROUP BY responsavel ORDER BY count(*) DESC LIMIT 20")).fetchall()
        for r in resps:
            print(r)
except Exception as e:
    print(e)
