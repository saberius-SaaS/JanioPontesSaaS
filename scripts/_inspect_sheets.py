"""Script temporário para inspecionar a estrutura das planilhas do GAS."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
load_dotenv()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
creds = service_account.Credentials.from_service_account_file(
    'credentials.json', scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Listar todas as abas
metadata = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
print('=== ABAS DA PLANILHA ===')
for s in metadata.get('sheets', []):
    print(f'  - {s["properties"]["title"]}')

# Cabecalho da DB_CLIENTES (primeiras 2 linhas)
result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='DB_CLIENTES!1:2').execute()
vals = result.get('values', [])
if vals:
    print(f'\n=== DB_CLIENTES Cabecalho ({len(vals[0])} colunas) ===')
    for i, h in enumerate(vals[0]):
        sample = vals[1][i] if len(vals) > 1 and i < len(vals[1]) else ''
        print(f'  Col {i}: {h} = "{sample}"')

# Cabecalho da DB_REGRAS
result2 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='DB_REGRAS!1:2').execute()
vals2 = result2.get('values', [])
if vals2:
    print(f'\n=== DB_REGRAS Cabecalho ({len(vals2[0])} colunas) ===')
    for i, h in enumerate(vals2[0]):
        sample = vals2[1][i] if len(vals2) > 1 and i < len(vals2[1]) else ''
        print(f'  Col {i}: {h} = "{sample}"')

# Cabecalho da DB_WORKFLOWS
result3 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='DB_WORKFLOWS!1:2').execute()
vals3 = result3.get('values', [])
if vals3:
    print(f'\n=== DB_WORKFLOWS Cabecalho ({len(vals3[0])} colunas) ===')
    for i, h in enumerate(vals3[0]):
        sample = vals3[1][i] if len(vals3) > 1 and i < len(vals3[1]) else ''
        print(f'  Col {i}: {h} = "{sample}"')

# Cabecalho da DB_USUARIOS
result4 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='DB_USUARIOS!1:2').execute()
vals4 = result4.get('values', [])
if vals4:
    print(f'\n=== DB_USUARIOS Cabecalho ({len(vals4[0])} colunas) ===')
    for i, h in enumerate(vals4[0]):
        sample = vals4[1][i] if len(vals4) > 1 and i < len(vals4[1]) else ''
        print(f'  Col {i}: {h} = "{sample}"')
