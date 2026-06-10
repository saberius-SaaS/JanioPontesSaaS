import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")

for db in ["chatwoot", "chatwoot_production"]:
    try:
        conn = psycopg2.connect(f"host={DB_HOST} dbname={db} port=5432 user={DB_USER} password={DB_PASSWORD}")
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'platform_apps';")
        tables = [row[0] for row in cursor.fetchall()]
        if tables:
            print(f"Table platform_apps FOUND in {db}")
        else:
            print(f"Table platform_apps NOT FOUND in {db}")
    except Exception as e:
        print(e)
