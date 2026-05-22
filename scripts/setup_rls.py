import os
import sys

# Garante que as importações do app funcionem
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database import SessionLocal, engine

# Tabelas que herdam TenantMixin e portanto necessitam de RLS
TENANT_TABLES = [
    "clientes",
    "frequencia_acessos",
    "historico_tarefas",
    "logs_sistema",
    "protocolos",
    "regras_obrigacoes",
    "solicitacoes",
    "tarefas",
    "usuarios",
    "workflows"
]

def setup_rls():
    db = SessionLocal()
    try:
        print("🚀 Iniciando configuração de Row-Level Security (RLS)...")
        
        # 1. Função auxiliar para ler o tenant_id da transação atual
        # O SQLAlchemy injetará 'app.current_tenant' a cada requisição
        db.execute(text("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.current_tenant', TRUE), '')::UUID;
        END;
        $$ LANGUAGE plpgsql;
        """))
        
        for table in TENANT_TABLES:
            print(f"🔒 Aplicando RLS na tabela: {table}")
            
            # Habilita o RLS e força a aplicação inclusive para o dono da tabela
            db.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
            db.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
            
            # Remove a política caso já exista (para permitir reexecução do script)
            db.execute(text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};"))
            
            # Cria a política que garante o isolamento
            # Permite bypass se 'app.bypass_rls' estiver ativado (útil para jobs de background que varrem o DB inteiro)
            db.execute(text(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                AS PERMISSIVE FOR ALL
                TO PUBLIC
                USING (tenant_id = current_tenant_id() OR current_setting('app.bypass_rls', TRUE) = 'on')
                WITH CHECK (tenant_id = current_tenant_id() OR current_setting('app.bypass_rls', TRUE) = 'on');
            """))
            
        db.commit()
        print("✅ RLS configurado com sucesso para todas as tabelas tenant-bound!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao configurar RLS: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_rls()
