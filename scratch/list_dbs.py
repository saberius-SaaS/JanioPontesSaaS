import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")

conn_string = f"host={DB_HOST} dbname=postgres port=5432 user={DB_USER} password={DB_PASSWORD}"
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()
cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
for row in cursor.fetchall():
    print(row[0])
