from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID

class RegraObrigacaoBase(BaseModel):
    obrigacao: str
    dia: Optional[str] = None
    departamento: Optional[str] = None
    regime: Optional[str] = None
    acao: Optional[str] = None
    meses: Optional[str] = None
    tipos: Optional[str] = None
    desloca: Optional[int] = 0
    vencimento_legal: Optional[str] = None
    antecipa_fds: Optional[str] = None
    grupo_regra: Optional[str] = None
    revisao: Optional[str] = None
    status: Optional[str] = "ATIVO"

class RegraObrigacaoCreate(RegraObrigacaoBase):
    pass

class RegraObrigacaoUpdate(RegraObrigacaoBase):
    obrigacao: Optional[str] = None

class RegraObrigacaoResponse(RegraObrigacaoBase):
    id: UUID
    tenant_id: UUID

    model_config = ConfigDict(from_attributes=True)
