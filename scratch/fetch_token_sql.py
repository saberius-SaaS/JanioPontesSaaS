import psycopg2
import secrets
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")

def get_or_create_platform_token():
    conn_string = f"host={DB_HOST} dbname=chatwoot_production port=5432 user={DB_USER} password={DB_PASSWORD}"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    # Check if PlatformApp exists
    cursor.execute("SELECT id FROM platform_apps WHERE name = 'JanioPontes SaaS';")
    app_result = cursor.fetchone()
    
    now = datetime.datetime.now()
    
    if not app_result:
        # Create PlatformApp
        cursor.execute("INSERT INTO platform_apps (name, created_at, updated_at) VALUES (%s, %s, %s) RETURNING id;", 
                       ('JanioPontes SaaS', now, now))
        app_id = cursor.fetchone()[0]
        conn.commit()
    else:
        app_id = app_result[0]

    # Check for token
    cursor.execute("SELECT token FROM access_tokens WHERE owner_type = 'PlatformApp' AND owner_id = %s;", (app_id,))
    token_result = cursor.fetchone()
    
    if token_result:
        print(f"Token encontrado: {token_result[0]}")
    else:
        token = secrets.token_urlsafe(32)
        cursor.execute("INSERT INTO access_tokens (owner_type, owner_id, token, created_at, updated_at) VALUES (%s, %s, %s, %s, %s) RETURNING token;", 
                       ('PlatformApp', app_id, token, now, now))
        new_token = cursor.fetchone()[0]
        conn.commit()
        print(f"Token criado: {new_token}")
        
    cursor.close()
    conn.close()

if __name__ == '__main__':
    get_or_create_platform_token()
