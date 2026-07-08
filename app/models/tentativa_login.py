from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, gerar_uuid
from app.core.timezone import agora_br

class TentativaLogin(Base):
    __tablename__ = "tentativas_login"
    __table_args__ = {"comment": "Registro de tentativas de login falhas por IP para rate limiting"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)
    ip_address = Column(String(45), nullable=False, index=True, comment="Endereco IP da tentativa (suporta IPv4 e IPv6)")
    attempt_time = Column(DateTime(timezone=True), nullable=False, default=agora_br, comment="Data/hora da tentativa falha")
    documento = Column(String(20), nullable=True, comment="CPF/CNPJ tentado")
