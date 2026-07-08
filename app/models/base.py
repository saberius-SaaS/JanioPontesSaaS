"""
Modelo Base SQLAlchemy para o JP SaaS.
Define a classe base, mixins de auditoria e o tenant_id para RLS.
"""
from app.core.timezone import agora_br
import uuid

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Classe base para todos os modelos do sistema."""
    pass


class TenantMixin:
    """
    Mixin que injeta tenant_id + timestamps em todas as tabelas multi-tenant.
    Cada registro pertence a um único tenant (escritório).
    """

    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="ID do escritório proprietário (RLS)"
        )

    criado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=agora_br,
        comment="Data de criação do registro"
    )

    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        default=agora_br,
        onupdate=agora_br,
        comment="Data da última atualização"
    )


def gerar_uuid():
    """Gera um UUID v4 para uso como PK."""
    return uuid.uuid4()
