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
from app.models import Tenant, Cliente, RegraObrigacao, Protocolo, HistoricoTarefa, Perfil, Usuario, TipoTarefaAvulsa, Workflow

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
        
        # Verifica se já existe
        existente = db.query(Cliente).filter(Cliente.cliente == nome_cliente).first()
        if existente:
            existente.cnpj = cnpj
            existente.responsavel = row.get('RESPONSAVEL', '')
            existente.email = row.get('EMAIL', '')
            existente.telefone = row.get('TELEFONE', '')
            existente.regime = row.get('REGIME', '')
            existente.fiscal = row.get('FISCAL', '')
            existente.contabil = row.get('CONTABIL', '')
            existente.pessoal = row.get('PESSOAL', '')
            existente.societario = row.get('SOCIETARIO', '')
            existente.excecoes = row.get('EXCECOES', '')
            existente.pasta_drive = row.get('PASTA_DRIVE', '')
            existente.nivel = int(row.get('NIVEL', 1)) if str(row.get('NIVEL', '')).strip().isdigit() else 1
            existente.perfis_ativos = row.get('PERFIS_ATIVOS', '')
            existente.status = row.get('STATUS', 'ATIVO')
            existente.email_fiscal = row.get('EMAIL_FISCAL', '')
            existente.email_contabil = row.get('EMAIL_CONTABIL', '')
            existente.email_pessoal = row.get('EMAIL_PESSOAL', '')
            existente.email_societario = row.get('EMAIL_SOCIETARIO', '')
            existente.nome_fantasia = row.get('FANTASIA', '')
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
            fiscal=row.get('FISCAL', ''),
            contabil=row.get('CONTABIL', ''),
            pessoal=row.get('PESSOAL', ''),
            societario=row.get('SOCIETARIO', ''),
            excecoes=row.get('EXCECOES', ''),
            pasta_drive=row.get('PASTA_DRIVE', ''),
            nivel=int(row.get('NIVEL', 1)) if str(row.get('NIVEL', '')).strip().isdigit() else 1,
            perfis_ativos=row.get('PERFIS_ATIVOS', ''),
            status=row.get('STATUS', 'ATIVO'),
            email_fiscal=row.get('EMAIL_FISCAL', ''),
            email_contabil=row.get('EMAIL_CONTABIL', ''),
            email_pessoal=row.get('EMAIL_PESSOAL', ''),
            email_societario=row.get('EMAIL_SOCIETARIO', ''),
            nome_fantasia=row.get('FANTASIA', '')
        )
        db.add(novo_cliente)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Clientes: {count_inseridos} novos inseridos, {count_pulados} atualizados (já existiam).")

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
            existente.dia = row.get('DIA', '')
            existente.departamento = row.get('DEPARTAMENTO', '')
            existente.regime = row.get('REGIME', '')
            existente.acao = row.get('ACAO', '')
            existente.meses = row.get('MESES', '')
            existente.tipos = row.get('TIPOS', '')
            existente.desloca = int(row.get('DESLOCA', 0)) if str(row.get('DESLOCA', '')).strip().lstrip('-').isdigit() else 0
            existente.vencimento_legal = row.get('VENCIMENTO_LEGAL', '')
            existente.antecipa_fds = row.get('ANTECIPA_FDS', '')
            existente.grupo_regra = row.get('GRUPO_REGRA', '')
            existente.revisao = row.get('REVISAO?', row.get('REVISAO', ''))
            count_inseridos += 1 # usando como contador de processados
            continue
            
        nova_regra = RegraObrigacao(
            tenant_id=tenant_id,
            obrigacao=nome_regra,
            dia=row.get('DIA', ''),
            departamento=row.get('DEPARTAMENTO', ''),
            regime=row.get('REGIME', ''),
            acao=row.get('ACAO', ''),
            meses=row.get('MESES', ''),
            tipos=row.get('TIPOS', ''),
            desloca=int(row.get('DESLOCA', 0)) if str(row.get('DESLOCA', '')).strip().lstrip('-').isdigit() else 0,
            vencimento_legal=row.get('VENCIMENTO_LEGAL', ''),
            antecipa_fds=row.get('ANTECIPA_FDS', ''),
            grupo_regra=row.get('GRUPO_REGRA', ''),
            revisao=row.get('REVISAO?', row.get('REVISAO', ''))
        )
        db.add(nova_regra)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Regras: {count_inseridos} regras processadas (novas ou atualizadas).")

def migrar_perfis(db: Session, tenant_id: str, regras_sheet: List[Dict], clientes_sheet: List[Dict]):
    """
    Migra os perfis de DUAS fontes:
    1. GRUPO_REGRA da aba DB_REGRAS (ex: SIMPLES, PRESUMIDO)
    2. PERFIS_ATIVOS da aba DB_CLIENTES (ex: CERTIDAO_NEGATIVA, CLINICA_MEDICA)
    Isso garante que todo perfil referenciado por qualquer cliente exista na tabela perfis.
    """
    logging.info("Extraindo perfis de DB_REGRAS (GRUPO_REGRA) + DB_CLIENTES (PERFIS_ATIVOS)...")
    
    count_inseridos = 0
    count_atualizados = 0
    
    # Fonte 1: Extrair perfis dos grupos de regras
    perfis_unicos = set()
    for row in regras_sheet:
        grupo = row.get('GRUPO_REGRA', '').strip()
        if grupo:
            perfis_unicos.add(grupo)
    
    # Fonte 2: Extrair perfis usados pelos clientes (campo PERFIS_ATIVOS é uma lista separada por vírgula)
    for row in clientes_sheet:
        perfis_str = row.get('PERFIS_ATIVOS', '').strip()
        if perfis_str:
            for perfil in perfis_str.split(','):
                perfil = perfil.strip()
                if perfil:
                    perfis_unicos.add(perfil)
    
    logging.info(f"  Total de perfis unicos encontrados: {len(perfis_unicos)}")
            
    for nome_perfil in sorted(perfis_unicos):
        existente = db.query(Perfil).filter(Perfil.nome == nome_perfil, Perfil.tenant_id == tenant_id).first()
        if existente:
            existente.status = 'ATIVO'
            count_atualizados += 1
            continue
            
        novo_perfil = Perfil(
            tenant_id=tenant_id,
            nome=nome_perfil,
            descricao=f"Perfil importado automaticamente: {nome_perfil}",
            status='ATIVO'
        )
        db.add(novo_perfil)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Perfis: {count_inseridos} novos inseridos, {count_atualizados} atualizados (de {len(perfis_unicos)} encontrados).")

def migrar_tipos_tarefa_avulsa(db: Session, tenant_id: str, regras_sheet: List[Dict]):
    """
    Migra os tipos de tarefas avulsas de DUAS fontes dentro de DB_REGRAS:
    1. Coluna TIPOS (tipos de empresa, ex: JUCEMG, MEI)
    2. Coluna OBRIGACAO (nome da obrigação, ex: DCTF, EFD) — cada obrigação é um tipo de tarefa válido
    """
    logging.info(f"Extraindo tipos de tarefas de {len(regras_sheet)} regras...")
    
    count_inseridos = 0
    tipos_unicos = {}
    
    for row in regras_sheet:
        departamento = row.get('DEPARTAMENTO', '').strip()
        
        # Fonte 1: coluna TIPOS (filtros de tipo de empresa)
        tipos_str = row.get('TIPOS', '').strip()
        if tipos_str:
            for tipo in tipos_str.split(','):
                tipo = tipo.strip().upper()
                if tipo and tipo not in tipos_unicos:
                    tipos_unicos[tipo] = departamento
        
        # Fonte 2: coluna OBRIGACAO (cada obrigação é um tipo de tarefa válido para criação avulsa)
        obrigacao = row.get('OBRIGACAO', '').strip().upper()
        if obrigacao and obrigacao not in tipos_unicos:
            tipos_unicos[obrigacao] = departamento
                
    for nome_tipo, depto in sorted(tipos_unicos.items()):
        existente = db.query(TipoTarefaAvulsa).filter(TipoTarefaAvulsa.nome == nome_tipo, TipoTarefaAvulsa.tenant_id == tenant_id).first()
        if existente:
            continue
            
        novo_tipo = TipoTarefaAvulsa(
            tenant_id=tenant_id,
            nome=nome_tipo,
            departamento=depto,
            descricao=f"Importado automaticamente",
            status='ATIVO'
        )
        db.add(novo_tipo)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Tipos Tarefa Avulsa: {count_inseridos} novos inseridos.")

def migrar_usuarios(db: Session, tenant_id: str, usuarios_sheet: List[Dict]):
    """Migra os dados da aba DB_USUARIOS."""
    logging.info(f"Migrando {len(usuarios_sheet)} usuários...")
    
    count_inseridos = 0
    count_atualizados = 0
    
    for row in usuarios_sheet:
        email = row.get('EMAIL', '').strip()
        if not email:
            continue
            
        ativo_str = str(row.get('ATIVO', row.get('STATUS', 'SIM'))).strip().upper()
        is_ativo = ativo_str in ['SIM', 'TRUE', '1', 'ATIVO', 'YES']
            
        existente = db.query(Usuario).filter(Usuario.email == email).first()
        if existente:
            existente.nome = row.get('NOME', '')
            existente.nivel = row.get('NIVEL', 'USER')
            existente.ativo = is_ativo
            count_atualizados += 1
            continue
            
        novo_usuario = Usuario(
            tenant_id=tenant_id,
            email=email,
            nome=row.get('NOME', ''),
            nivel=row.get('NIVEL', 'USER'),
            ativo=is_ativo
        )
        db.add(novo_usuario)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Usuários: {count_inseridos} novos inseridos, {count_atualizados} atualizados.")

def migrar_workflows(db: Session, tenant_id: str, workflows_sheet: List[Dict]):
    """Migra os dados da aba DB_WORKFLOWS."""
    logging.info(f"Migrando {len(workflows_sheet)} fluxos de workflow...")
    
    count_inseridos = 0
    
    # Limpa a tabela de workflows antes de migrar (pois os fluxos podem ter sido remodelados)
    db.query(Workflow).filter(Workflow.tenant_id == tenant_id).delete()
    db.flush()
    
    for row in workflows_sheet:
        fase_atual = row.get('FASE_ATUAL', '').strip()
        proxima_fase = row.get('PROXIMA_FASE', '').strip()
        if not fase_atual or not proxima_fase:
            continue
            
        novo_workflow = Workflow(
            tenant_id=tenant_id,
            fase_atual=fase_atual,
            proxima_fase=proxima_fase,
            dias=int(row.get('DIAS', 0)) if str(row.get('DIAS', '')).strip().isdigit() else 0,
            departamento=row.get('DEPARTAMENTO', ''),
            acao=row.get('ACAO', ''),
            responsavel_padrao=row.get('RESPONSAVEL_PADRAO', row.get('RESPONSAVEL', ''))
        )
        db.add(novo_workflow)
        count_inseridos += 1
        
    db.commit()
    logging.info(f"Workflows: {count_inseridos} inseridos.")

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
        usuarios_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_USUARIOS!A:Z")
        workflows_dados = ler_aba_planilha(service, SPREADSHEET_ID, "DB_WORKFLOWS!A:Z")
        
        # 4. Migra para o banco de dados
        migrar_clientes(db, tenant_id, clientes_dados)
        migrar_regras(db, tenant_id, regras_dados)
        migrar_perfis(db, tenant_id, regras_dados, clientes_dados)
        migrar_tipos_tarefa_avulsa(db, tenant_id, regras_dados)
        if usuarios_dados:
            migrar_usuarios(db, tenant_id, usuarios_dados)
        if workflows_dados:
            migrar_workflows(db, tenant_id, workflows_dados)
        
        logging.info("✅ Migração Carga Inicial concluída com sucesso!")
        
    except Exception as e:
        db.rollback()
        logging.error(f"❌ Erro crítico durante a migração: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    iniciar_migracao()
