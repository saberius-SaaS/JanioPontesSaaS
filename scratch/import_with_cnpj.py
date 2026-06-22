import csv
import requests
import time
import os
import sys

# Adiciona o diretório raiz ao sys.path para conseguirmos importar a aplicação FastAPI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.cliente import Cliente

# ==============================================================================
# CONFIGURAÇÕES DA API DO CHATWOOT
# ==============================================================================
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://chat.janiopontes.com.br")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1")
API_ACCESS_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "SEU_TOKEN_DE_ACESSO_AQUI")

# Caminho para o arquivo CSV de contatos
CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), "contatos_escritorio.csv")

# ==============================================================================

def limpar_cnpj(cnpj_str):
    if not cnpj_str: return None
    return ''.join(filter(str.isdigit, str(cnpj_str)))

def import_contacts(csv_path):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts"
    
    headers = {
        "Content-Type": "application/json",
        "api_access_token": API_ACCESS_TOKEN
    }

    db = SessionLocal()

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            sucesso = 0
            falhas = 0
            
            for row in reader:
                row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                
                name = row_lower.get("nome")
                email = row_lower.get("email")
                phone = row_lower.get("telefone")
                cnpj_planilha = row_lower.get("cnpj")
                
                # Formatando telefone
                if phone and not phone.startswith('+'):
                    phone = f"+55{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"
                
                # Preparando os Custom Attributes
                custom_attributes = {}
                
                # Busca automática pelo CNPJ no nosso banco de dados
                if cnpj_planilha:
                    cnpj_limpo = limpar_cnpj(cnpj_planilha)
                    # Procurar no banco
                    # Como o banco pode ter o CNPJ com ou sem máscara, buscamos com ILIKE ou limpamos antes.
                    # Vamos tentar uma busca simples primeiro
                    cliente_db = db.query(Cliente).filter(Cliente.cnpj.ilike(f"%{cnpj_limpo}%")).first()
                    
                    if cliente_db:
                        custom_attributes["empresa_nome"] = cliente_db.cliente
                        custom_attributes["empresa_id"] = str(cliente_db.id)
                        custom_attributes["empresa_cnpj"] = cliente_db.cnpj
                    else:
                        print(f"⚠️ Atenção: CNPJ {cnpj_planilha} não encontrado no banco para o contato {name}.")
                        custom_attributes["empresa_cnpj"] = cnpj_planilha

                payload = {
                    "name": name,
                    "email": email,
                    "phone_number": phone,
                }

                if custom_attributes:
                    payload["custom_attributes"] = custom_attributes
                
                # Remove nulos
                payload = {k: v for k, v in payload.items() if v}

                print(f"Importando: {name}...")
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    print(f"✅ Sucesso: {name}")
                    sucesso += 1
                else:
                    print(f"❌ Erro ao importar {name}: {response.text}")
                    falhas += 1
                
                time.sleep(0.2)
                
        print("\n--- RESUMO DA IMPORTAÇÃO ---")
        print(f"Contatos importados com sucesso: {sucesso}")
        print(f"Falhas: {falhas}")

    except Exception as e:
        print(f"Ocorreu um erro ao processar o arquivo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import_contacts(CSV_FILE_PATH)
