"""
Modelo: Tipos de Tarefas Avulsas
Catálogo de tipos disponíveis para criação manual de tarefas.
"""
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class TipoTarefaAvulsa(TenantMixin, Base):
    __tablename__ = "tipos_tarefa_avulsa"
    __table_args__ = {"comment": "Catálogo de tipos de tarefas avulsas disponíveis para criação manual"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    nome = Column(String(255), nullable=False, index=True, comment="Nome do tipo (ex: CERTIDÃO NEGATIVA)")
    departamento = Column(String(50), nullable=True, comment="Departamento padrão ao usar este tipo")
    descricao = Column(String(500), nullable=True, comment="Descrição ou instrução sobre este tipo de tarefa")
    status = Column(String(20), nullable=False, default="ATIVO", comment="ATIVO ou INATIVO")
