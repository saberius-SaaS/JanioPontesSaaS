from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date
from uuid import UUID

class ProtocoloBase(BaseModel):
    cliente: str
    protocolo: str
    id_tarefa: Optional[str] = None
    obrigacao: Optional[str] = None
    email: Optional[str] = None
    responsavel: Optional[str] = None
    link_arquivo: Optional[str] = None
    status_envio: Optional[str] = "ENVIADO"
    conf_recto: Optional[datetime] = None
    vcto_legal: Optional[date] = None
    acao: Optional[str] = None
    wpp_notif: Optional[datetime] = None

class ProtocoloCreate(BaseModel):
    cliente: str
    obrigacao: str
    id_tarefa: Optional[str] = None
    email: Optional[str] = None
    # Upload via FormData isn't natively handled by JSON schemas, but this represents the core fields

class ProtocoloUpdate(BaseModel):
    status_envio: Optional[str] = None

class ProtocoloResponse(ProtocoloBase):
    id: UUID
    tenant_id: UUID
    data: datetime

    model_config = ConfigDict(from_attributes=True)
