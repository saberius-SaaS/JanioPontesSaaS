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
from app.models import Tenant, Tarefa, HistoricoTarefa, Protocolo

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

def migrar_tarefas(db: Session, tenant_id: str, tarefas_sheet: List[Dict]):
    logging.info(f"Migrando {len(tarefas_sheet)} tarefas...")
    count_inseridos = 0
    count_atualizados = 0
    
    for row in tarefas_sheet:
        id_controle = row.get('ID_CONTROLE', '').strip()
        if not id_controle: id_controle = str(uuid.uuid4())
        
        cliente_nome = row.get('CLIENTE', '').strip()
        obrigacao_nome = row.get('OBRIGACAO', '').strip()
        mes_ano = row.get('MES_ANO', '').strip()
        
        if not cliente_nome or not obrigacao_nome:
            continue
            
        # Tenta encontrar por id_controle primeiro, depois por chave composta
        existente = db.query(Tarefa).filter(Tarefa.id_controle == id_controle).first()
        if not existente:
            existente = db.query(Tarefa).filter(
                Tarefa.mes_ano == mes_ano,
                Tarefa.cliente == cliente_nome,
                Tarefa.obrigacao == obrigacao_nome
            ).first()

        status = row.get('STATUS', 'PENDENTE').upper()
        
        if existente:
            existente.status = status[:20]
            existente.vencimento = parse_date(row.get('VENCIMENTO', '')) or existente.vencimento
            existente.protocolo = str(row.get('PROTOCOLO', ''))[:50]
            existente.responsavel = str(row.get('RESPONSAVEL', existente.responsavel))[:255]
            if existente.id_controle != id_controle:
                existente.id_controle = id_controle[:50]
            count_atualizados += 1
        else:
            nova = Tarefa(
                tenant_id=tenant_id,
                mes_ano=mes_ano[:20],
                cliente=cliente_nome[:255],
                obrigacao=obrigacao_nome[:255],
                vencimento=parse_date(row.get('VENCIMENTO', '')),
                departamento=str(row.get('DEPARTAMENTO', ''))[:50],
                status=status[:20],
                protocolo=str(row.get('PROTOCOLO', ''))[:50],
                acao=str(row.get('ACAO', ''))[:50],
                responsavel=str(row.get('RESPONSAVEL', ''))[:255],
                id_controle=id_controle[:50],
                nivel=int(row.get('NIVEL', 1)) if str(row.get('NIVEL', '')).isdigit() else 1,
                vencimento_legal=parse_date(row.get('VENCIMENTO_LEGAL', ''))
            )
            db.add(nova)
            count_inseridos += 1
            
        if (count_inseridos + count_atualizados) % 50 == 0:
            db.commit()
            logging.info(f"  ... progresso: {count_inseridos + count_atualizados} tarefas processadas...")
    db.commit()
    logging.info(f"Tarefas: {count_inseridos} inseridas, {count_atualizados} atualizadas.")

def migrar_historico(db: Session, tenant_id: str, historico_sheet: List[Dict]):
    logging.info(f"Migrando {len(historico_sheet)} historicos...")
    count = 0
    count_skip = 0
    for row in historico_sheet:
        id_controle = row.get('ID_CONTROLE', '').strip()
        if not id_controle: id_controle = str(uuid.uuid4())
        
        cliente_nome = row.get('CLIENTE', '').strip()
        if not cliente_nome:
            continue
            
        exist = db.query(HistoricoTarefa).filter(HistoricoTarefa.id_controle == id_controle).first()
        if exist:
            count_skip += 1
            continue
        
        novo = HistoricoTarefa(
            tenant_id=tenant_id,
            mes_ano=str(row.get('MES_ANO', ''))[:20],
            cliente=cliente_nome[:255],
            obrigacao=str(row.get('OBRIGACAO', ''))[:255],
            vencimento=parse_date(row.get('VENCIMENTO', '')),
            departamento=str(row.get('DEPARTAMENTO', ''))[:50],
            status=str(row.get('STATUS', 'ENTREGUE')).upper()[:20],
            protocolo=str(row.get('PROTOCOLO', ''))[:50],
            acao=str(row.get('ACAO', ''))[:50],
            responsavel=str(row.get('RESPONSAVEL', ''))[:255],
            id_controle=id_controle[:50],
            nivel=int(row.get('NIVEL', 1)) if str(row.get('NIVEL', '')).isdigit() else 1,
            vencimento_legal=parse_date(row.get('VENCIMENTO_LEGAL', '')),
            status_envio=str(row.get('STATUS_ENVIO', ''))[:50],
            conf_recto=str(row.get('CONF_RECTO', ''))[:100]
        )
        db.add(novo)
        count += 1
        
        # Commit a cada 200 para evitar erros massivos
        if count % 200 == 0:
            db.commit()
            logging.info(f"  ... {count} historicos inseridos...")
            
    db.commit()
    logging.info(f"Historico: {count} registros inseridos, {count_skip} ja existiam.")

def iniciar_migracao():
    logging.info("Iniciando migracao de Tarefas e Historico (GAS -> Postgres)")
    db = SessionLocal()
    try:
        tenant_base = db.query(Tenant).first()
        if not tenant_base:
            logging.error("Tenant base nao encontrado.")
            return
            
        tenant_id = str(tenant_base.id)
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        
        service = get_sheets_service()
        
        tarefas_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_TAREFAS!A:Z")
        historico_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_HISTORICO!A:Z")
        
        if tarefas_dados:
            # Limpa tarefas existentes para sincronizar 1:1 com a planilha
            deleted = db.query(Tarefa).filter(Tarefa.tenant_id == tenant_id).delete()
            db.commit()
            logging.info(f"Limpeza: {deleted} tarefas antigas removidas para sync limpo.")
            migrar_tarefas(db, tenant_id, tarefas_dados)
        else:
            logging.warning("Nenhuma tarefa encontrada ou aba DB_TAREFAS nao existe.")
            
        if historico_dados:
            migrar_historico(db, tenant_id, historico_dados)
        else:
            logging.warning("Nenhum historico encontrado ou aba DB_HISTORICO nao existe.")
            
        logging.info("Migracao de Tarefas/Historico concluida!")
    except Exception as e:
        db.rollback()
        logging.error(f"Erro: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    iniciar_migracao()
