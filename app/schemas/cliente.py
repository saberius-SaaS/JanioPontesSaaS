import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from uuid import UUID


def validar_cnpj(cnpj: str) -> str:
    """Valida formato básico de CNPJ (com ou sem máscara)."""
    limpo = re.sub(r'[^0-9]', '', cnpj)
    if len(limpo) != 14:
        raise ValueError(f"CNPJ deve ter 14 dígitos, recebido {len(limpo)}")
    return cnpj


def validar_email(email: str) -> str:
    """Valida formato básico de e-mail."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError(f"E-mail inválido: {email}")
    return email


class ClienteBase(BaseModel):
    cliente: str = Field(..., min_length=2, max_length=255, description="Razão social do cliente")
    cnpj: Optional[str] = None
    responsavel: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    regime: Optional[str] = None
    fiscal: Optional[str] = None
    contabil: Optional[str] = None
    pessoal: Optional[str] = None
    societario: Optional[str] = None
    nivel: Optional[int] = 1
    status: Optional[str] = "ATIVO"
    nome_fantasia: Optional[str] = None
    email_fiscal: Optional[str] = None
    email_contabil: Optional[str] = None
    email_pessoal: Optional[str] = None
    email_societario: Optional[str] = None
    pasta_drive: Optional[str] = None
    perfis_ativos: Optional[str] = None
    excecoes: Optional[str] = None

    @field_validator('cnpj')
    @classmethod
    def check_cnpj(cls, v):
        if v:
            return validar_cnpj(v)
        return v

    @field_validator('email')
    @classmethod
    def check_email(cls, v):
        if v:
            return validar_email(v)
        return v


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    cliente: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)
