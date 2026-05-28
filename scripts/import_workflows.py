import os
import sys
import logging
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Tenant
from app.models.operacional import Workflow

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)

def ler_aba_planilha(service, spreadsheet_id: str, range_name: str) -> List[Dict]:
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    if not values:
        return []
    headers = values[0]
    dados = []
    for row in values[1:]:
        row_padded = row + [''] * (len(headers) - len(row))
        item = dict(zip(headers, row_padded))
        dados.append(item)
    return dados

def migrar_workflows(db: Session, tenant_id: str, workflow_sheet: List[Dict]):
    count_inseridos = 0
    count_pulados = 0
    
    for row in workflow_sheet:
        keys = {k.upper(): k for k in row.keys()}
        
        def get_val(*possibilidades):
            for p in possibilidades:
                if p in keys:
                    return row[keys[p]].strip()
            return ""
            
        fase_atual = get_val('FASE ATUAL', 'FASE_ATUAL', 'ORIGEM', 'FASE')
        proxima_fase = get_val('PROXIMA FASE', 'PROXIMA_FASE', 'DESTINO', 'PROXIMA')
        dias_str = get_val('DIAS', 'PRAZO', 'TEMPO')
        departamento = get_val('DEPARTAMENTO', 'DEPTO')
        acao = get_val('ACAO', 'AÇÃO', 'TAREFA')
        responsavel = get_val('RESPONSAVEL PADRAO', 'RESPONSAVEL_PADRAO', 'RESPONSAVEL')
        
        if not fase_atual or not proxima_fase:
            continue
            
        dias = 0
        if dias_str.isdigit():
            dias = int(dias_str)
            
        existente = db.query(Workflow).filter(
            Workflow.tenant_id == tenant_id,
            Workflow.fase_atual == fase_atual,
            Workflow.proxima_fase == proxima_fase
        ).first()
        
        if existente:
            existente.dias = dias
            existente.departamento = departamento or None
            existente.acao = acao or None
            existente.responsavel_padrao = responsavel or None
            count_pulados += 1
            continue
            
        novo = Workflow(
            tenant_id=tenant_id,
            fase_atual=fase_atual,
            proxima_fase=proxima_fase,
            dias=dias,
            departamento=departamento or None,
            acao=acao or None,
            responsavel_padrao=responsavel or None
        )
        db.add(novo)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Workflows: {count_inseridos} novos inseridos, {count_pulados} atualizados.")

def run():
    logging.info("Iniciando migração de DB_WORKFLOWS...")
    if not SPREADSHEET_ID:
        logging.error("SPREADSHEET_ID não encontrado no .env")
        return
        
    db: Session = SessionLocal()
    try:
        tenant_base = db.query(Tenant).first()
        if not tenant_base:
            logging.error("Tenant não encontrado")
            return
        tenant_id = str(tenant_base.id)
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        db.execute(text(f"SET SESSION app.current_tenant = '{tenant_id}';"))
        
        service = get_sheets_service()
        dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_WORKFLOWS!A:Z")
        if dados:
            migrar_workflows(db, tenant_id, dados)
        else:
            logging.error("Nenhum dado encontrado em DB_WORKFLOWS!A:Z")
    finally:
        db.close()

if __name__ == '__main__':
    run()
