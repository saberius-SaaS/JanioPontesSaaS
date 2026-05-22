"""
Modelo: Tenants (Escritórios Contábeis)
Tabela raiz da arquitetura multi-tenant.
"""
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, gerar_uuid


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"comment": "Escritórios contábeis (raiz multi-tenant)"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    razao_social = Column(String(255), nullable=False, comment="Razão social do escritório")
    cnpj = Column(String(20), nullable=True, unique=True, comment="CNPJ do escritório")
    nome_fantasia = Column(String(255), nullable=True, comment="Nome fantasia")
    logo_url = Column(Text, nullable=True, comment="URL do logotipo (White-label)")
    cor_primaria = Column(String(10), nullable=True, default="#1C3051", comment="Cor primária da interface")
    plano = Column(String(20), nullable=False, default="FREE", comment="FREE, PRO, ENTERPRISE")
    ativo = Column(Boolean, nullable=False, default=True, comment="Escritório ativo/inativo")
