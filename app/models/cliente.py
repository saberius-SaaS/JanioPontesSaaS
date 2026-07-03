"""
Modelo: Clientes (Empresas atendidas pelo escritório)
Mapeamento: DB_CLIENTES (21 colunas)
"""
from sqlalchemy import Column, Integer, String, Text, Date
from sqlalchemy.dialects.postgresql import UUID
import datetime

from app.models.base import Base, TenantMixin, gerar_uuid


class Cliente(TenantMixin, Base):
    __tablename__ = "clientes"
    __table_args__ = {"comment": "Clientes (empresas atendidas pelo escritório)"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)

    # --- Dados Cadastrais (Colunas A-G) ---
    cliente = Column(String(255), nullable=False, index=True, comment="Razão social do cliente")
    cnpj = Column(String(20), nullable=True, comment="CNPJ (com ou sem máscara)")
    responsavel = Column(String(255), nullable=True, comment="Nome do responsável no cliente")
    email = Column(String(255), nullable=True, comment="Email principal de contato")
    telefone = Column(String(255), nullable=True, comment="Telefones (separados por ,;/)")
    regime = Column(String(50), nullable=True, comment="Regime tributário: SIMPLES, LUCRO PRESUMIDO, etc.")

    # --- Referências Departamentais (Colunas H-K) ---
    fiscal = Column(String(255), nullable=True, comment="Referência do setor Fiscal")
    contabil = Column(String(255), nullable=True, comment="Referência do setor Contábil")
    pessoal = Column(String(255), nullable=True, comment="Referência do setor Pessoal")
    societario = Column(String(255), nullable=True, comment="Referência do setor Societário")

    # --- Configurações (Colunas L-P) ---
    excecoes = Column(Text, nullable=True, comment="IDs de regras excluídas para este cliente")
    pasta_drive = Column(Text, nullable=True, comment="URL da pasta no Google Drive")
    nivel = Column(Integer, nullable=True, default=1, comment="Nível de prioridade do cliente")
    perfis_ativos = Column(Text, nullable=True, comment="Tags/Perfis de regras aplicáveis")
    status = Column(String(20), nullable=True, default="ATIVO", comment="ATIVO / INATIVO")

    # --- Emails Departamentais de Roteamento (Colunas Q-T) ---
    email_fiscal = Column(String(255), nullable=True, comment="Email de roteamento — Fiscal")
    email_contabil = Column(String(255), nullable=True, comment="Email de roteamento — Contábil")
    email_pessoal = Column(String(255), nullable=True, comment="Email de roteamento — Pessoal")
    email_societario = Column(String(255), nullable=True, comment="Email de roteamento — Societário")
    regras_roteamento = Column(Text, nullable=True, comment="JSON mapping: {'Obrigacao': 'email@destino'}")

    # --- Coluna U ---
    nome_fantasia = Column(String(255), nullable=True, comment="Nome fantasia da empresa")

    # --- Controle de Entrada ---
    data_entrada = Column(Date, nullable=True, default=datetime.date.today, comment="Data de entrada do cliente na carteira. Tarefas não serão geradas para competências anteriores a este mês.")
