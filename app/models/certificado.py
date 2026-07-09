from sqlalchemy import Column, String, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TenantMixin, gerar_uuid

class CertificadoDigital(Base, TenantMixin):
    __tablename__ = "certificados_digitais"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    cliente_id = Column(UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(10), nullable=False)  # A1 ou A3
    vencimento = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO, ALERTA, VENCIDO, INDETERMINADO
    senha = Column(String(255), nullable=True) # Optional, can be masked
    anotacao = Column(Text, nullable=True)

    # Relacionamento com o cliente
    cliente = relationship("Cliente", backref="certificados")
