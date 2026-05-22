"""
Modelos: Tarefas, Protocolos, Histórico, Solicitações
Mapeamento: DB_TAREFAS (12), DB_PROTOCOLOS (13), DB_HISTORICO (14), DB_SOLICITACOES (12)
"""
from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class Tarefa(TenantMixin, Base):
    """Fila ativa de trabalho — DB_TAREFAS (12 colunas)"""
    __tablename__ = "tarefas"
    __table_args__ = {"comment": "Fila ativa de tarefas pendentes e em andamento"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    mes_ano = Column(String(20), nullable=False, comment="Referência: MM/YYYY")
    cliente = Column(String(255), nullable=False, index=True, comment="Nome do cliente")
    obrigacao = Column(String(255), nullable=False, comment="Nome da obrigação")
    vencimento = Column(Date, nullable=True, comment="Data de vencimento operacional")
    departamento = Column(String(50), nullable=True, comment="Departamento responsável")
    status = Column(String(20), nullable=True, default="PENDENTE", index=True, comment="PENDENTE, ENTREGUE, REVISAO, REPROVADO")
    protocolo = Column(String(50), nullable=True, comment="Código do protocolo de entrega")
    acao = Column(String(50), nullable=True, comment="ENVIAR, ARQUIVAR, AUDITAR, COMUNICAR")
    responsavel = Column(String(255), nullable=True, comment="Email(s) do(s) responsável(is)")
    id_controle = Column(String(50), nullable=False, unique=True, index=True, comment="Identificador único da tarefa")
    nivel = Column(Integer, nullable=True, default=1, comment="Prioridade (1-5)")
    vencimento_legal = Column(Date, nullable=True, comment="Data legal original do vencimento")


class Protocolo(TenantMixin, Base):
    """Registro de entregas de documentos — DB_PROTOCOLOS (13 colunas)"""
    __tablename__ = "protocolos"
    __table_args__ = {"comment": "Registro de entregas e protocolos gerados"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    data = Column(DateTime(timezone=True), nullable=False, comment="Data/hora do registro")
    cliente = Column(String(255), nullable=False, index=True, comment="Nome do cliente")
    protocolo = Column(String(50), nullable=False, unique=True, index=True, comment="Código único (PRT...)")
    id_tarefa = Column(String(50), nullable=True, index=True, comment="Referência ao id_controle da tarefa")
    obrigacao = Column(String(255), nullable=True, comment="Nome da obrigação entregue")
    email = Column(String(255), nullable=True, comment="Email de destino")
    responsavel = Column(String(255), nullable=True, comment="Quem realizou a entrega")
    link_arquivo = Column(Text, nullable=True, comment="URL(s) dos arquivos ou justificativa")
    status_envio = Column(String(50), nullable=True, default="ENVIADO", comment="ENVIADO, MANUAL, ERRO")
    conf_recto = Column(DateTime(timezone=True), nullable=True, comment="Data de confirmação de recebimento")
    vcto_legal = Column(Date, nullable=True, comment="Vencimento legal da obrigação")
    acao = Column(String(50), nullable=True, comment="ENVIAR, ARQUIVAR, COMUNICAR, AUDITAR")
    wpp_notif = Column(DateTime(timezone=True), nullable=True, comment="Última notificação WhatsApp enviada")


class HistoricoTarefa(TenantMixin, Base):
    """Arquivo de tarefas concluídas — DB_HISTORICO (14 colunas = 12 tarefa + 2 extras)"""
    __tablename__ = "historico_tarefas"
    __table_args__ = {"comment": "Arquivo permanente de tarefas concluídas"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)

    # --- Colunas 1-12 (idênticas a DB_TAREFAS) ---
    mes_ano = Column(String(20), nullable=False)
    cliente = Column(String(255), nullable=False, index=True)
    obrigacao = Column(String(255), nullable=False)
    vencimento = Column(Date, nullable=True)
    departamento = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    protocolo = Column(String(50), nullable=True, index=True)
    acao = Column(String(50), nullable=True)
    responsavel = Column(String(255), nullable=True)
    id_controle = Column(String(50), nullable=True, index=True)
    nivel = Column(Integer, nullable=True)
    vencimento_legal = Column(Date, nullable=True)

    # --- Colunas 13-14 (extras do histórico) ---
    status_envio = Column(String(50), nullable=True, comment="Copiado de DB_PROTOCOLOS")
    conf_recto = Column(String(100), nullable=True, comment="Confirmação de recebimento")


class Solicitacao(TenantMixin, Base):
    """Pedidos de documentos enviados aos clientes — DB_SOLICITACOES (12 colunas)"""
    __tablename__ = "solicitacoes"
    __table_args__ = {"comment": "Solicitações de documentos pendentes dos clientes"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    id_legado = Column(String(50), nullable=True, unique=True, comment="ID original (SOL + timestamp)")
    data = Column(DateTime(timezone=True), nullable=False, comment="Data da solicitação")
    cliente = Column(String(255), nullable=False, index=True, comment="Nome do cliente")
    email = Column(String(255), nullable=True, comment="Email do cliente")
    pedido = Column(Text, nullable=True, comment="Descrição do documento solicitado")
    id_tarefa = Column(String(50), nullable=True, comment="Referência à tarefa (ou 'AVULSA')")
    status = Column(String(20), nullable=True, default="PENDENTE", comment="PENDENTE, ENTREGUE")
    data_envio = Column(DateTime(timezone=True), nullable=True, comment="Data do envio de resposta")
    ultima_cobranca = Column(DateTime(timezone=True), nullable=True, comment="Data da última cobrança")
    qtd_avisos = Column(Integer, nullable=True, default=0, comment="Contador de lembretes enviados")
    responsavel = Column(String(255), nullable=True, comment="Email de quem solicitou")
    meta_tarefa = Column(String(255), nullable=True, comment="Info da tarefa vinculada")
