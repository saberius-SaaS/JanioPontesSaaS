"""
Modelos: Workflows, Logs, Frequência, Configurações
Mapeamento: DB_WORKFLOWS (6), DB_LOGS (4), DB_FREQUENCIA (5), DB_CONFIG_IA (2)
"""
from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class Workflow(TenantMixin, Base):
    """Encadeamento de fases de trabalho — DB_WORKFLOWS (6 colunas)"""
    __tablename__ = "workflows"
    __table_args__ = {"comment": "Regras de encadeamento de fases (workflow)"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    fase_atual = Column(String(100), nullable=False, comment="Nome da fase de origem")
    proxima_fase = Column(String(100), nullable=False, comment="Nome da fase seguinte")
    dias = Column(Integer, nullable=True, comment="Prazo em dias para a próxima fase")
    departamento = Column(String(50), nullable=True, comment="Departamento da próxima fase")
    acao = Column(String(50), nullable=True, comment="Ação da próxima fase")
    responsavel_padrao = Column(String(255), nullable=True, comment="Email do responsável padrão")


class LogSistema(TenantMixin, Base):
    """Logs de auditoria e operação — DB_LOGS (4 colunas)"""
    __tablename__ = "logs_sistema"
    __table_args__ = {"comment": "Logs de auditoria, erros e operações do sistema"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    data = Column(DateTime(timezone=True), nullable=False, comment="Data/hora do evento")
    email = Column(String(255), nullable=True, index=True, comment="Quem executou a ação")
    acao = Column(String(100), nullable=False, index=True, comment="Tipo do evento (ex: UPLOAD_START)")
    detalhes = Column(Text, nullable=True, comment="Informação adicional")


class FrequenciaAcesso(TenantMixin, Base):
    """Consolidação diária de tempo de acesso — DB_FREQUENCIA (5 colunas)"""
    __tablename__ = "frequencia_acessos"
    __table_args__ = {"comment": "Registro consolidado de tempo de uso diário por usuário"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    data = Column(Date, nullable=False, comment="Data consolidada")
    email = Column(String(255), nullable=False, index=True, comment="Email do usuário")
    nome = Column(String(255), nullable=True, comment="Nome do usuário")
    tempo_minutos = Column(Integer, nullable=True, default=0, comment="Minutos de atividade no dia")
    pings = Column(Integer, nullable=True, default=0, comment="Quantidade de heartbeats no dia")


class Configuracao(Base):
    """Configurações do sistema (chave/valor) — DB_CONFIG_IA (2 colunas)
    Nota: NÃO usa TenantMixin pois configurações são globais ou por tenant via chave.
    """
    __tablename__ = "configuracoes"
    __table_args__ = {"comment": "Configurações do sistema em formato chave/valor"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    chave = Column(String(100), nullable=False, unique=True, index=True, comment="Nome da configuração")
    valor = Column(Text, nullable=True, comment="Valor da configuração")
