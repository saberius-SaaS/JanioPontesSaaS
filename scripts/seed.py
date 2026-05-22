import os
import sys

# Garante que as importações do app funcionem
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models import Tenant, Usuario

def seed_database():
    db: Session = SessionLocal()
    try:
        print("🚀 Iniciando Seed do Banco de Dados...")
        
        # O SQLAlchemy gerencia as sessões, mas como ativamos o RLS obrigatório,
        # precisamos garantir que o bypass esteja ligado para inserir o admin e o tenant
        # caso a inserção não faça sentido no escopo de um tenant específico.
        # Mas como a tabela `tenants` não tem RLS, a inserção é direta.
        
        # 1. Cria ou Atualiza o Tenant Inicial
        tenant_existente = db.query(Tenant).filter(Tenant.cnpj == "00.000.000/0001-00").first()
        
        if not tenant_existente:
            tenant_base = Tenant(
                razao_social="Janio Pontes Contabilidade",
                nome_fantasia="JP NCE",
                cnpj="00.000.000/0001-00",
                cor_primaria="#1C3051",
                plano="ENTERPRISE",
                ativo=True
            )
            db.add(tenant_base)
            db.flush() # Gera o ID
            tenant_id = tenant_base.id
            print(f"🏢 Tenant Base criado: {tenant_base.razao_social} (ID: {tenant_id})")
        else:
            tenant_id = tenant_existente.id
            print(f"🏢 Tenant Base já existe: {tenant_existente.razao_social} (ID: {tenant_id})")
            
        # 2. Configura a sessão do PostgreSQL para o tenant_id antes de inserir na tabela com RLS
        # Desativamos o bypass só para testar se a inserção funciona no contexto do tenant
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_id)}';"))
        
        # 3. Cria ou Atualiza o Usuário Admin
        email_admin = "janiopontes@janiopontes.com.br"
        admin_existente = db.query(Usuario).filter(Usuario.email.in_(["admin@janiopontes.com.br", email_admin])).first()
        
        if not admin_existente:
            admin_user = Usuario(
                tenant_id=tenant_id,
                email=email_admin,
                nome="Jânio Pontes",
                nivel="MASTER",
                ativo=True
            )
            db.add(admin_user)
            print(f"👤 Usuário Admin criado: {email_admin}")
        else:
            if admin_existente.email != email_admin:
                admin_existente.email = email_admin
                admin_existente.nome = "Jânio Pontes"
                print(f"👤 Usuário Admin atualizado para: {email_admin}")
            else:
                print(f"👤 Usuário Admin já existe: {email_admin}")
            
        db.commit()
        print("✅ Seed finalizado com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao executar seed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
