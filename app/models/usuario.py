"""
Modelo: Usuarios (Controle de Acesso)
Mapeamento: DB_USUARIOS (3 colunas originais + tenant + audit)
"""
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class Usuario(TenantMixin, Base):
    __tablename__ = "usuarios"
    __table_args__ = {"comment": "Usuários do sistema (operadores do escritório)"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    email = Column(String(255), nullable=False, index=True, comment="Email de login (Google OAuth)")
    nome = Column(String(255), nullable=False, comment="Nome de exibição")
    nivel = Column(String(20), nullable=False, default="USER", comment="USER, ADMIN, MASTER, CONSULTOR")
    ativo = Column(Boolean, nullable=False, default=True, comment="Usuário ativo/inativo")
