import os
import sys
import logging
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Tenant, Tarefa, HistoricoTarefa, Cliente, RegraObrigacao, Usuario, Workflow

load_dotenv()
# Desativando logs extensivos para o relatorio ficar limpo
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def parse_date(date_str):
    if not date_str: return None
    try:
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                return datetime.date(int(parts[2][:4]), int(parts[1]), int(parts[0]))
    except:
        pass
    return None

def fetch_sheet_rows(service, range_name):
    try:
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        return result.get('values', [])
    except Exception:
        return []

def main():
    print("\n[INICIANDO AUDITORIA COMPLETA DE MIGRACAO: GAS vs PostgreSQL]")
    print("="*75)
    
    service = get_sheets_service()
    hoje = datetime.date.today()
    
    # --- 1. COLETA DO GOOGLE SHEETS (GAS) ---
    print("Extraindo dados do Google Sheets...")
    gas_clientes = fetch_sheet_rows(service, "DB_CLIENTES!A:Z")[1:]
    gas_regras = fetch_sheet_rows(service, "DB_REGRAS!A:Z")[1:]
    gas_usuarios = fetch_sheet_rows(service, "DB_USUARIOS!A:Z")[1:]
    gas_workflows = fetch_sheet_rows(service, "DB_WORKFLOWS!A:Z")[1:]
    
    raw_tarefas = fetch_sheet_rows(service, "DB_TAREFAS!A:Z")
    headers_tarefas = raw_tarefas[0] if raw_tarefas else []
    gas_tarefas = raw_tarefas[1:] if len(raw_tarefas) > 1 else []
    
    raw_historico = fetch_sheet_rows(service, "DB_HISTORICO!A:Z")
    headers_hist = raw_historico[0] if raw_historico else []
    gas_historico = raw_historico[1:] if len(raw_historico) > 1 else []
    
    # Contadores GAS
    total_clientes_gas = len([r for r in gas_clientes if r and r[0].strip()])
    total_regras_gas = len([r for r in gas_regras if r and r[0].strip()])
    total_usuarios_gas = len([r for r in gas_usuarios if r and r[0].strip()])
    total_workflows_gas = len([r for r in gas_workflows if r and r[0].strip()])
    total_tarefas_gas = len([r for r in gas_tarefas if r and r[0].strip()])
    total_historico_gas = len([r for r in gas_historico if r and r[0].strip()])
    
    # Metricas Detalhadas (GAS)
    gas_pendentes = 0
    gas_concluidas = 0
    gas_atrasadas = 0
    gas_com_protocolo = 0
    
    idx_status_tar = headers_tarefas.index('STATUS') if 'STATUS' in headers_tarefas else -1
    idx_venc_tar = headers_tarefas.index('VENCIMENTO_LEGAL') if 'VENCIMENTO_LEGAL' in headers_tarefas else (headers_tarefas.index('VENCIMENTO') if 'VENCIMENTO' in headers_tarefas else -1)
    idx_prot_tar = headers_tarefas.index('PROTOCOLO') if 'PROTOCOLO' in headers_tarefas else -1
    
    for row in gas_tarefas:
        if not row or not row[0].strip(): continue
        status = row[idx_status_tar].upper() if len(row) > idx_status_tar else ''
        venc_str = row[idx_venc_tar] if len(row) > idx_venc_tar else ''
        venc_date = parse_date(venc_str)
        protocolo = row[idx_prot_tar].strip() if len(row) > idx_prot_tar else ''
        
        if protocolo: gas_com_protocolo += 1
            
        if status in ['PENDENTE', 'EM_ANDAMENTO', 'AGUARDANDO']:
            gas_pendentes += 1
            if venc_date and venc_date < hoje:
                gas_atrasadas += 1
        elif status in ['ENTREGUE', 'CONCLUIDO', 'CONCLUÍDO']:
            gas_concluidas += 1
            
    idx_status_hist = headers_hist.index('STATUS') if 'STATUS' in headers_hist else -1
    idx_prot_hist = headers_hist.index('PROTOCOLO') if 'PROTOCOLO' in headers_hist else -1
    
    for row in gas_historico:
        if not row or not row[0].strip(): continue
        status = row[idx_status_hist].upper() if len(row) > idx_status_hist else 'ENTREGUE'
        protocolo = row[idx_prot_hist].strip() if len(row) > idx_prot_hist else ''
        
        if protocolo: gas_com_protocolo += 1
            
        if status in ['ENTREGUE', 'CONCLUIDO', 'CONCLUÍDO']:
            gas_concluidas += 1
        elif status in ['PENDENTE', 'EM_ANDAMENTO', 'AGUARDANDO']:
            gas_pendentes += 1
            
    # --- 2. COLETA DO POSTGRESQL ---
    print("Contando registros no PostgreSQL...")
    db: Session = SessionLocal()
    try:
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        
        total_clientes_pg = db.query(Cliente).count()
        total_regras_pg = db.query(RegraObrigacao).count()
        # Ignora admin se não conta no gas, mas o GAS pode ter admin. Vamos contar apenas onde nivel != master se master não vier do gas? 
        # O script atualiza o master, então ele existe no db. No gas não sabemos se existe. Vamos contar todos do tenant.
        total_usuarios_pg = db.query(Usuario).count()
        total_workflows_pg = db.query(Workflow).count()
        
        total_tarefas_pg = db.query(Tarefa).count()
        total_historico_pg = db.query(HistoricoTarefa).count()
        
        pg_pendentes = db.query(Tarefa).filter(Tarefa.status.in_(['PENDENTE', 'EM ANDAMENTO', 'AGUARDANDO', 'EM_ANDAMENTO'])).count()
        pg_atrasadas = db.query(Tarefa).filter(
            Tarefa.status.in_(['PENDENTE', 'EM ANDAMENTO', 'AGUARDANDO', 'EM_ANDAMENTO']),
            Tarefa.vencimento_legal < hoje
        ).count()
        
        pg_concluidas = db.query(Tarefa).filter(Tarefa.status.in_(['ENTREGUE', 'CONCLUIDO', 'CONCLUÍDO'])).count() + db.query(HistoricoTarefa).count()
        
        pg_com_protocolo = db.query(Tarefa).filter(Tarefa.protocolo != '', Tarefa.protocolo != None).count() + \
                           db.query(HistoricoTarefa).filter(HistoricoTarefa.protocolo != '', HistoricoTarefa.protocolo != None).count()
        
    finally:
        db.close()
        
    # --- 3. RELATORIO VISUAL ---
    print(f"\n{'-'*75}")
    print(f"{'TIPO DE DADO':<28} | {'ORIGEM (GAS)':<15} | {'DESTINO (PG)':<15} | {'STATUS':<10}")
    print(f"{'-'*75}")
    
    def check(g, p): return "OK" if g == p else "DIFERENTE"
    
    print(f"{'Total Clientes':<28} | {total_clientes_gas:<15} | {total_clientes_pg:<15} | {check(total_clientes_gas, total_clientes_pg)}")
    print(f"{'Total Regras':<28} | {total_regras_gas:<15} | {total_regras_pg:<15} | {check(total_regras_gas, total_regras_pg)}")
    print(f"{'Total Workflows':<28} | {total_workflows_gas:<15} | {total_workflows_pg:<15} | {check(total_workflows_gas, total_workflows_pg)}")
    print(f"{'Total Usuarios':<28} | {total_usuarios_gas:<15} | {total_usuarios_pg:<15} | {'*Verificar' if total_usuarios_gas != total_usuarios_pg else 'OK'}")
    
    print(f"{'-'*75}")
    print(f"{'Total Tarefas (Fila Atual)':<28} | {total_tarefas_gas:<15} | {total_tarefas_pg:<15} | {check(total_tarefas_gas, total_tarefas_pg)}")
    print(f"{'Total Historico (Morto)':<28} | {total_historico_gas:<15} | {total_historico_pg:<15} | {check(total_historico_gas, total_historico_pg)}")
    print(f"{'-'*75}")
    
    print(f"{'METRICAS DE OPERACAO':<28} | {'':<15} | {'':<15} | ")
    print(f"{'Obrigacoes Pendentes':<28} | {gas_pendentes:<15} | {pg_pendentes:<15} | {check(gas_pendentes, pg_pendentes)}")
    print(f"{'Entregas Realizadas':<28} | {gas_concluidas:<15} | {pg_concluidas:<15} | {check(gas_concluidas, pg_concluidas)}")
    print(f"{'Risco Legal (Atrasos)':<28} | {gas_atrasadas:<15} | {pg_atrasadas:<15} | {check(gas_atrasadas, pg_atrasadas)}")
    print(f"{'Total de Protocolos':<28} | {gas_com_protocolo:<15} | {pg_com_protocolo:<15} | {check(gas_com_protocolo, pg_com_protocolo)}")
    print(f"{'-'*75}")

if __name__ == "__main__":
    main()
