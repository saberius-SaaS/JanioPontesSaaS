from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid

class SolicitacaoRecorrente(TenantMixin, Base):
    """Regras para geração automática de solicitações recorrentes"""
    __tablename__ = "solicitacoes_recorrentes"
    __table_args__ = {"comment": "Configuração de solicitações mensais/semanais geradas automaticamente"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Referência ao ID do cliente")
    cliente_nome = Column(String(255), nullable=False, comment="Nome do cliente (desnormalizado para busca)")
    departamento = Column(String(50), nullable=False, comment="Departamento responsável (Fiscal, Contábil, etc)")
    responsavel = Column(String(255), nullable=False, comment="Email do responsável pela solicitação")
    email_override = Column(String(255), nullable=True, comment="Se preenchido, sobrepõe o email do cliente/departamento")
    
    titulo_template = Column(String(255), nullable=False, comment="Ex: Extratos Bancários do mês {mes_anterior}/{ano_anterior}")
    descricao_template = Column(Text, nullable=True, comment="Corpo da solicitação com suporte a variáveis de template")
    
    dia_geracao = Column(Integer, nullable=False, comment="Dia do mês para gerar (ex: 3)")
    ativo = Column(Boolean, nullable=False, default=True, comment="Se a regra está ativa")
