import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from datetime import date

load_dotenv(override=True)

pwd = quote_plus(os.getenv("DB_PASSWORD", ""))
url = f"postgresql://{os.getenv('DB_USER')}:{pwd}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(url)

try:
    with engine.begin() as conn:
        # Procurar todas as tarefas ENTREGUE que nao estao no historico
        # Vamos olhar diretamente para DB
        query = sqlalchemy.text('''
            SELECT id, cliente, obrigacao, status, id_controle, protocolo
            FROM tarefas 
            WHERE status = 'ENTREGUE'
            AND protocolo NOT IN (SELECT protocolo FROM historico_tarefas WHERE protocolo IS NOT NULL)
            AND id_controle NOT IN (SELECT id_controle FROM historico_tarefas WHERE id_controle IS NOT NULL)
        ''')
        orphans = conn.execute(query).fetchall()
        
        print("Encontradas:", len(orphans))
        for row in orphans:
            print(f"- {row.cliente} | {row.obrigacao} (Protocolo: {row.protocolo})")
            
            # Atualizar apenas essa tarefa específica!
            update_query = sqlalchemy.text('''
                UPDATE tarefas 
                SET status = 'PENDENTE', protocolo = NULL 
                WHERE id = :task_id
            ''')
            conn.execute(update_query, {"task_id": row.id})
            
            # Se houver um protocolo orfão, excluí-lo também
            if row.protocolo:
                del_prot = sqlalchemy.text('''
                    DELETE FROM protocolos WHERE protocolo = :prot
                ''')
                conn.execute(del_prot, {"prot": row.protocolo})
                
            print(f"✅ Tarefa {row.obrigacao} corrigida com sucesso e voltou para PENDENTE!")
except Exception as e:
    print("Erro:", e)
