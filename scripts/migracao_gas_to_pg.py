"""
Script de Carga Inicial (Migração Etapa 9)
Lê as abas DB_CLIENTES, DB_REGRAS e DB_HISTORICO do Google Sheets atual do Janio Pontes,
transforma os dados e faz o upload para o banco de dados PostgreSQL.

Operação READ-ONLY no Google Sheets. NENHUM DADO DA PLANILHA É ALTERADO.
"""
import os
import sys
import logging
from typing import List, Dict

# Garante que as importações do app funcionem se executado da raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Tenant, Cliente, RegraObrigacao, Protocolo, HistoricoTarefa

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- CONFIGURAÇÕES DO GOOGLE SHEETS ---
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "ID_DA_SUA_PLANILHA_AQUI")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    """Autentica na API do Google Sheets e retorna o serviço."""
    if not os.path.exists(CREDENTIALS_FILE):
        logging.error(f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
        sys.exit(1)
        
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    return service

def ler_aba_planilha(service, spreadsheet_id: str, range_name: str) -> List[Dict]:
    """
    Lê os dados de uma aba específica e retorna uma lista de dicionários
    baseada no cabeçalho (primeira linha).
    """
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])

        if not values:
            logging.warning(f"Nenhum dado encontrado na aba {range_name}.")
            return []

        # A primeira linha é o cabeçalho
        headers = values[0]
        dados = []
        
        # Ignora a primeira linha (cabeçalho)
        for row in values[1:]:
            # Preenche colunas vazias para ter o mesmo tamanho do cabeçalho
            row_padded = row + [''] * (len(headers) - len(row))
            # Cria dicionário: {'Nome do Cabeçalho': 'Valor'}
            item = dict(zip(headers, row_padded))
            dados.append(item)
            
        return dados
    except Exception as e:
        logging.error(f"Erro ao ler aba {range_name}: {str(e)}")
        return []

def migrar_clientes(db: Session, tenant_id: str, clientes_sheet: List[Dict]):
    """Migra os dados da aba DB_CLIENTES."""
    logging.info(f"Migrando {len(clientes_sheet)} clientes...")
    
    count_inseridos = 0
    count_pulados = 0
    
    for row in clientes_sheet:
        nome_cliente = row.get('CLIENTE', '').strip()
        if not nome_cliente:
            continue
            
        cnpj = row.get('CNPJ', '').strip()
        
        # Verifica se já existe para não duplicar na homologação
        existente = db.query(Cliente).filter(Cliente.cliente == nome_cliente).first()
        if existente:
            count_pulados += 1
            continue
            
        novo_cliente = Cliente(
            tenant_id=tenant_id,
            cliente=nome_cliente,
            cnpj=cnpj,
            responsavel=row.get('RESPONSAVEL', ''),
            email=row.get('EMAIL', ''),
            telefone=row.get('TELEFONE', ''),
            regime=row.get('REGIME', ''),
            nome_fantasia=row.get('FANTASIA', ''),
            status="ATIVO"
        )
        db.add(novo_cliente)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Clientes: {count_inseridos} inseridos, {count_pulados} ignorados (já existiam).")

def migrar_regras(db: Session, tenant_id: str, regras_sheet: List[Dict]):
    """Migra os dados da aba DB_REGRAS."""
    logging.info(f"Migrando {len(regras_sheet)} regras/obrigações...")
    
    count_inseridos = 0
    
    for row in regras_sheet:
        nome_regra = row.get('OBRIGACAO', '').strip()
        if not nome_regra:
            continue
            
        existente = db.query(RegraObrigacao).filter(RegraObrigacao.obrigacao == nome_regra).first()
        if existente:
            continue
            
        nova_regra = RegraObrigacao(
            tenant_id=tenant_id,
            obrigacao=nome_regra,
            dia=row.get('DIA', ''),
            departamento=row.get('DEPARTAMENTO', ''),
            regime=row.get('REGIME', ''),
            acao=row.get('ACAO', '')
        )
        db.add(nova_regra)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Regras: {count_inseridos} novas regras inseridas.")

def iniciar_migracao():
    logging.info("🚀 Iniciando script de migração (Google Sheets -> PostgreSQL)")
    
    # 1. Recupera o Tenant Base
    db: Session = SessionLocal()
    try:
        tenant_base = db.query(Tenant).first()
        if not tenant_base:
            logging.error("Tenant base não encontrado. Rode o `scripts/seed.py` primeiro.")
            return
            
        tenant_id = str(tenant_base.id)
        logging.info(f"Usando Tenant: {tenant_base.razao_social} (ID: {tenant_id})")
        
        # Desliga RLS e define o tenant ativo para a sessão (sobrevive aos commits do SQLAlchemy)
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        db.execute(text(f"SET SESSION app.current_tenant = '{tenant_id}';"))
        
        # 2. Conecta no Google Sheets
        if SPREADSHEET_ID == "ID_DA_SUA_PLANILHA_AQUI":
            logging.error("ATENÇÃO: Você precisa colocar o SPREADSHEET_ID real da sua planilha no arquivo .env!")
            return
            
        service = get_sheets_service()
        
        # 3. Lê os dados
        logging.info("Fazendo download dos dados do Google Sheets...")
        # NOTA: Os nomes das abas precisam ser exatos! 
        # Altere se a sua planilha usar nomes diferentes (ex: 'Clientes!A:Z')
        clientes_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_CLIENTES!A:Z")
        regras_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_REGRAS!A:Z")
        
        # 4. Migra para o banco de dados
        migrar_clientes(db, tenant_id, clientes_dados)
        migrar_regras(db, tenant_id, regras_dados)
        
        logging.info("✅ Migração Carga Inicial concluída com sucesso!")
        
    except Exception as e:
        db.rollback()
        logging.error(f"❌ Erro crítico durante a migração: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    iniciar_migracao()
