"""
Modelo: Regras de Obrigações (regras que geram tarefas automaticamente)
Mapeamento: DB_REGRAS (12+1 colunas)
"""
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TenantMixin, gerar_uuid


class RegraObrigacao(TenantMixin, Base):
    __tablename__ = "regras_obrigacoes"
    __table_args__ = {"comment": "Regras que definem obrigações e geram tarefas mensais"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=gerar_uuid)

    # --- Dados da Regra (Colunas A-L) ---
    obrigacao = Column(String(255), nullable=False, index=True, comment="Nome da obrigação (ex: DCTF, EFD)")
    dia = Column(String(20), nullable=True, comment="Dia do vencimento (pode ser '5U' para 5º dia útil)")
    departamento = Column(String(100), nullable=True, comment="CONTABIL, FISCAL, PESSOAL, SOCIETARIO")
    regime = Column(String(255), nullable=True, comment="Filtro de regime tributário")
    acao = Column(String(100), nullable=True, comment="ENVIAR, ARQUIVAR, AUDITAR, COMUNICAR")
    meses = Column(String(255), nullable=True, comment="Meses aplicáveis (ex: '1,2,3...12')")
    tipos = Column(Text, nullable=True, comment="Tipos de empresa aplicáveis")
    desloca = Column(Integer, nullable=True, default=0, comment="Deslocamento de mês-referência")
    vencimento_legal = Column(String(100), nullable=True, comment="Data legal de referência")
    antecipa_fds = Column(String(10), nullable=True, comment="S/N — antecipa se cair no fim de semana")
    grupo_regra = Column(Text, nullable=True, comment="Agrupamento/Tag de regras")

    # --- Coluna M (adicionada posteriormente) ---
    revisao = Column(String(10), nullable=True, comment="S/N — exige revisão do admin antes de finalizar")
