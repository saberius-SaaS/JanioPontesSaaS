"""
Modelo: Perfil (Agrupamento de Regras)
"""
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class Perfil(TenantMixin, Base):
    __tablename__ = "perfis"
    __table_args__ = {"comment": "Perfis de obrigações vinculados aos clientes e regras"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    nome = Column(String(255), nullable=False, index=True, comment="Nome do Perfil")
    descricao = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="ATIVO", comment="ATIVO / INATIVO")
