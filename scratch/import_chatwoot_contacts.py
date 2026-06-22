import csv
import requests
import time
import os

# ==============================================================================
# CONFIGURAÇÕES DA API DO CHATWOOT
# ==============================================================================
CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://chatwoot.janiopontes.com.br")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1")
API_ACCESS_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "SEU_TOKEN_DE_ACESSO_AQUI")

# Caminho para o arquivo CSV de contatos
CSV_FILE_PATH = "contatos_escritorio.csv"

# ==============================================================================

def import_contacts(csv_path):
    url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/contacts"
    
    headers = {
        "Content-Type": "application/json",
        "api_access_token": API_ACCESS_TOKEN
    }

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            sucesso = 0
            falhas = 0
            
            for row in reader:
                # Normaliza os nomes das chaves para evitar erros de case sensitivity
                # (ex: 'Nome', 'nome', 'NOME')
                row_lower = {k.strip().lower(): v.strip() for k, v in row.items() if k and v}
                
                name = row_lower.get("nome")
                email = row_lower.get("email")
                phone = row_lower.get("telefone")
                empresa = row_lower.get("empresa")
                
                # O Chatwoot exige formato E.164 (ex: +5511999999999) para telefones
                if phone and not phone.startswith('+'):
                    phone = f"+55{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"
                
                payload = {
                    "name": name,
                    "email": email,
                    "phone_number": phone,
                }

                if empresa:
                    payload["custom_attributes"] = {"empresa": empresa}
                
                # Removemos os campos nulos ou vazios para não gerar erro na API
                payload = {k: v for k, v in payload.items() if v}

                print(f"Importando: {name}...")
                
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    print(f"✅ Sucesso: {name}")
                    sucesso += 1
                else:
                    print(f"❌ Erro ao importar {name}: {response.text}")
                    falhas += 1
                
                # Pequena pausa para evitar bloqueios de Rate Limit da API
                time.sleep(0.2)
                
        print("\n--- RESUMO DA IMPORTAÇÃO ---")
        print(f"Contatos importados com sucesso: {sucesso}")
        print(f"Falhas: {falhas}")

    except Exception as e:
        print(f"Ocorreu um erro ao processar o arquivo: {e}")

if __name__ == "__main__":
    # Crie o arquivo 'contatos_escritorio.csv' no mesmo diretório com as colunas Nome, Email e Telefone
    import_contacts(CSV_FILE_PATH)
