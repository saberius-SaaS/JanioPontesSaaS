"""
Script para migrar os tipos da coluna H (TIPOS) da DB_REGRAS
para a nova tabela tipos_tarefa_avulsa.
Executa uma vez e pode ser descartado depois.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import RegraObrigacao, TipoTarefaAvulsa

db = SessionLocal()

try:
    # Busca todos os valores distintos de tipos
    regras = db.query(RegraObrigacao.tipos, RegraObrigacao.departamento, RegraObrigacao.tenant_id).filter(
        RegraObrigacao.tipos != None,
        RegraObrigacao.tipos != ''
    ).all()
    
    tipos_existentes = set()
    count = 0
    
    for row in regras:
        if not row.tipos:
            continue
        for tipo in row.tipos.split(','):
            tipo = tipo.strip().upper()
            if not tipo:
                continue
            chave = (tipo, row.tenant_id)
            if chave in tipos_existentes:
                continue
            tipos_existentes.add(chave)
            
            # Verifica se já existe
            existente = db.query(TipoTarefaAvulsa).filter(
                TipoTarefaAvulsa.nome == tipo,
                TipoTarefaAvulsa.tenant_id == row.tenant_id
            ).first()
            
            if not existente:
                novo = TipoTarefaAvulsa(
                    tenant_id=row.tenant_id,
                    nome=tipo,
                    departamento=row.departamento,
                    status="ATIVO"
                )
                db.add(novo)
                count += 1
    
    db.commit()
    print(f"Migração concluída: {count} tipos inseridos na tabela tipos_tarefa_avulsa.")
    
except Exception as e:
    db.rollback()
    print(f"Erro: {e}")
finally:
    db.close()
