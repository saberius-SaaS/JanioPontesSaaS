"""
Modelo: Equipes e Relacionamento N:N com Usuários
"""
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TenantMixin, gerar_uuid


class Equipe(TenantMixin, Base):
    __tablename__ = "equipes"
    __table_args__ = {"comment": "Equipes de trabalho (Squads) por departamento"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    nome = Column(String(255), nullable=False, comment="Nome da equipe (ex: Equipe Fiscal A)")
    departamento = Column(String(50), nullable=False, comment="Departamento (FISCAL, CONTABIL, PESSOAL, SOCIETARIO)")

    # Relacionamento com a tabela associativa
    membros = relationship("UsuarioEquipe", back_populates="equipe", cascade="all, delete-orphan")


class UsuarioEquipe(TenantMixin, Base):
    __tablename__ = "usuarios_equipes"
    __table_args__ = {"comment": "Relacionamento N:N entre Usuários e Equipes"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    equipe_id = Column(UUID(as_uuid=True), ForeignKey("equipes.id"), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)

    equipe = relationship("Equipe", back_populates="membros")
    usuario = relationship("Usuario", back_populates="equipes")
