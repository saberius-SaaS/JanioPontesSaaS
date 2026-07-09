from sqlalchemy import Column, String, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TenantMixin, gerar_uuid

class LicencaLocalizacao(Base, TenantMixin):
    __tablename__ = "licencas_localizacao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    vencimento = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO, ALERTA, VENCIDO, INDETERMINADO
    arquivo_url = Column(Text, nullable=True)
    anotacao = Column(Text, nullable=True)

    cliente = relationship("Cliente", backref="licencas_localizacao")

class AlvaraSanitario(Base, TenantMixin):
    __tablename__ = "alvaras_sanitarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    vencimento = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO, ALERTA, VENCIDO, INDETERMINADO
    arquivo_url = Column(Text, nullable=True)
    anotacao = Column(Text, nullable=True)

    cliente = relationship("Cliente", backref="alvaras_sanitarios")

class AVCB(Base, TenantMixin):
    __tablename__ = "avcbs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    vencimento = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO, ALERTA, VENCIDO, INDETERMINADO
    arquivo_url = Column(Text, nullable=True)
    anotacao = Column(Text, nullable=True)

    cliente = relationship("Cliente", backref="avcbs")

class InscricaoMunicipal(Base, TenantMixin):
    __tablename__ = "inscricoes_municipais"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    vencimento = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO, ALERTA, VENCIDO, INDETERMINADO
    arquivo_url = Column(Text, nullable=True)
    anotacao = Column(Text, nullable=True)

    cliente = relationship("Cliente", backref="inscricoes_municipais")
