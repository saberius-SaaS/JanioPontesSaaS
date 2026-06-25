import os
import sys
import logging
from typing import List, Dict
import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Tenant, Protocolo

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "ID_DA_SUA_PLANILHA_AQUI")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    if not os.path.exists(CREDENTIALS_FILE):
        logging.error(f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

def ler_aba_planilha(service, spreadsheet_id: str, range_name: str) -> List[Dict]:
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            return []
        headers = [h.strip().upper() for h in values[0]]
        dados = []
        for row in values[1:]:
            row_padded = row + [''] * (len(headers) - len(row))
            item = dict(zip(headers, row_padded))
            dados.append(item)
        return dados
    except Exception as e:
        logging.error(f"Erro ao ler aba {range_name}: {str(e)}")
        return []

def parse_datetime(date_str):
    if not date_str: return None
    try:
        # DD/MM/YYYY HH:MM:SS
        if "/" in date_str and ":" in date_str:
            date_part, time_part = date_str.split(" ")
            d_parts = date_part.split("/")
            t_parts = time_part.split(":")
            if len(d_parts) == 3 and len(t_parts) >= 2:
                sec = int(t_parts[2]) if len(t_parts) == 3 else 0
                return datetime.datetime(int(d_parts[2][:4]), int(d_parts[1]), int(d_parts[0]), int(t_parts[0]), int(t_parts[1]), sec)
    except:
        pass
    return None

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

def migrar_protocolos(db: Session, tenant_id: str, protocolos_sheet: List[Dict]):
    logging.info(f"Migrando {len(protocolos_sheet)} protocolos...")
    count = 0
    count_skip = 0
    for row in protocolos_sheet:
        protocolo_code = row.get('PROTOCOLO', '').strip()
        if not protocolo_code: continue
        
        exist = db.query(Protocolo).filter(Protocolo.protocolo == protocolo_code).first()
        if exist:
            count_skip += 1
            continue
            
        novo = Protocolo(
            tenant_id=tenant_id,
            data=parse_datetime(row.get('DATA', '')) or datetime.datetime.now(),
            cliente=row.get('CLIENTE', '').strip()[:255],
            protocolo=protocolo_code[:50],
            id_tarefa=row.get('ID_TAREFA', '')[:50],
            obrigacao=row.get('OBRIGACAO', '')[:255],
            email=row.get('EMAIL', '')[:255],
            responsavel=row.get('RESPONSAVEL', '')[:255],
            link_arquivo=row.get('LINK_ARQUIVO', ''),
            status_envio=row.get('STATUS_ENVIO', 'ENVIADO')[:50],
            conf_recto=parse_datetime(row.get('CONF_RECTO', '')),
            vcto_legal=parse_date(row.get('VCTO_LEGAL', '')),
            acao=row.get('ACAO', '')[:50],
            wpp_notif=parse_datetime(row.get('WPP_NOTIF', ''))
        )
        db.add(novo)
        count += 1
        
        if count % 200 == 0:
            db.commit()
            
    db.commit()
    logging.info(f"Protocolos: {count} inseridos, {count_skip} ja existiam.")

def main():
    db = SessionLocal()
    try:
        tenant_base = db.query(Tenant).first()
        tenant_id = str(tenant_base.id)
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        
        service = get_sheets_service()
        protocolos_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_PROTOCOLOS!A:Z")
        
        if protocolos_dados:
            db.query(Protocolo).filter(Protocolo.tenant_id == tenant_id).delete()
            db.commit()
            migrar_protocolos(db, tenant_id, protocolos_dados)
        else:
            logging.warning("Nenhum protocolo encontrado.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
