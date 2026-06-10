"""
Pacote de Modelos SQLAlchemy — JP SaaS
Importa todos os modelos para facilitar o uso e garantir que o Alembic os detecte.
"""
from app.models.base import Base, TenantMixin, gerar_uuid
from app.models.tenant import Tenant
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.regra import RegraObrigacao
from app.models.tarefa import Tarefa, Protocolo, HistoricoTarefa, Solicitacao
from app.models.operacional import Workflow, LogSistema, FrequenciaAcesso, Configuracao
from app.models.perfil import Perfil
from app.models.tipo_tarefa import TipoTarefaAvulsa
from app.models.equipe import Equipe, UsuarioEquipe

__all__ = [
    "Base",
    "TenantMixin",
    "gerar_uuid",
    "Tenant",
    "Usuario",
    "Cliente",
    "RegraObrigacao",
    "Tarefa",
    "Protocolo",
    "HistoricoTarefa",
    "Solicitacao",
    "Workflow",
    "LogSistema",
    "FrequenciaAcesso",
    "Configuracao",
    "Perfil",
    "TipoTarefaAvulsa",
    "Equipe",
    "UsuarioEquipe"
]
