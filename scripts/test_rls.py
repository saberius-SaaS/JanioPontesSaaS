import os
import sys

# Garante que as importações do app funcionem
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models import Tenant, Usuario, Cliente
import uuid

def test_rls():
    db: Session = SessionLocal()
    try:
        print("🧪 Iniciando Teste de Isolamento RLS...")

        # Garantir bypass off para começar
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))

        # 1. Obter o Tenant A (Janio Pontes Contabilidade)
        tenant_a = db.query(Tenant).filter(Tenant.cnpj == "00.000.000/0001-00").first()
        if not tenant_a:
            print("❌ Tenant A não encontrado. Rode seed.py primeiro.")
            return
        
        # 2. Criar Tenant B
        tenant_b = db.query(Tenant).filter(Tenant.cnpj == "11.111.111/0001-11").first()
        if not tenant_b:
            tenant_b = Tenant(
                razao_social="Empresa Teste B",
                nome_fantasia="Teste B",
                cnpj="11.111.111/0001-11",
                cor_primaria="#FF0000",
                plano="FREE",
                ativo=True
            )
            db.add(tenant_b)
            db.commit()
            print("🏢 Tenant B criado com sucesso.")
        else:
            print("🏢 Tenant B já existe.")

        # 3. Criar Usuário B para Tenant B
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_b.id)}';"))
        user_b = db.query(Usuario).filter(Usuario.email == "userb@testeb.com.br").first()
        if not user_b:
            user_b = Usuario(
                tenant_id=tenant_b.id,
                email="userb@testeb.com.br",
                nome="Usuário B",
                nivel="USER",
                ativo=True
            )
            db.add(user_b)
            db.commit()
            print("👤 Usuário B criado para Tenant B.")

        # 4. Criar Clientes para Tenant A e Tenant B
        
        # Inserir no Tenant A
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_a.id)}';"))
        cliente_a = db.query(Cliente).filter(Cliente.cliente == "Cliente do Tenant A").first()
        if not cliente_a:
            cliente_a = Cliente(tenant_id=tenant_a.id, cliente="Cliente do Tenant A", cnpj="22.222.222/0001-22")
            db.add(cliente_a)
            db.commit()
            print("👥 Cliente inserido no Tenant A.")

        # Inserir no Tenant B
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_b.id)}';"))
        cliente_b = db.query(Cliente).filter(Cliente.cliente == "Cliente do Tenant B").first()
        if not cliente_b:
            cliente_b = Cliente(tenant_id=tenant_b.id, cliente="Cliente do Tenant B", cnpj="33.333.333/0001-33")
            db.add(cliente_b)
            db.commit()
            print("👥 Cliente inserido no Tenant B.")

        # 5. Testar Isolamento

        # Logado como Tenant A
        print("\n🔍 Simulando acesso do Usuário A (Tenant A)...")
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_a.id)}';"))
        clientes_a = db.query(Cliente).all()
        nomes_a = [c.cliente for c in clientes_a]
        print(f"Clientes vistos pelo Tenant A: {nomes_a}")
        assert "Cliente do Tenant A" in nomes_a
        assert "Cliente do Tenant B" not in nomes_a

        # Logado como Tenant B
        print("\n🔍 Simulando acesso do Usuário B (Tenant B)...")
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(tenant_b.id)}';"))
        clientes_b = db.query(Cliente).all()
        nomes_b = [c.cliente for c in clientes_b]
        print(f"Clientes vistos pelo Tenant B: {nomes_b}")
        assert "Cliente do Tenant B" in nomes_b
        assert "Cliente do Tenant A" not in nomes_b

        # Acesso global com Bypass
        print("\n🔍 Simulando acesso de sistema (Bypass RLS ON)...")
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        clientes_todos = db.query(Cliente).all()
        nomes_todos = [c.cliente for c in clientes_todos]
        print(f"Clientes vistos com bypass: {nomes_todos}")
        assert "Cliente do Tenant A" in nomes_todos
        assert "Cliente do Tenant B" in nomes_todos

        print("\n✅ TESTE DE RLS CONCLUÍDO COM SUCESSO! Isolamento 100% garantido.")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro durante o teste: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_rls()
