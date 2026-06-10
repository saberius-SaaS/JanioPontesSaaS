import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Usuario, Equipe, UsuarioEquipe, Cliente

def run():
    db: Session = SessionLocal()
    
    # Descobre o tenant_id (usando o primeiro admin disponível ou pegando do primeiro cliente)
    primeiro_cliente = db.query(Cliente).first()
    if not primeiro_cliente:
        print("Nenhum cliente encontrado. Abortando.")
        return
        
    tenant_id = primeiro_cliente.tenant_id
    
    # 1. Cria as Equipes Iniciais
    departamentos = {
        "CONTABIL": "Contábil A",
        "FISCAL": "Fiscal A",
        "PESSOAL": "Pessoal A",
        "SOCIETARIO": "Societário A"
    }
    
    equipes_criadas = {}
    
    for depto_id, nome_equipe in departamentos.items():
        eq = db.query(Equipe).filter(Equipe.nome == nome_equipe, Equipe.tenant_id == tenant_id).first()
        if not eq:
            eq = Equipe(tenant_id=tenant_id, nome=nome_equipe, departamento=depto_id)
            db.add(eq)
            db.commit()
            db.refresh(eq)
            print(f"Equipe {nome_equipe} criada.")
        equipes_criadas[depto_id] = eq

    # 2. Varre os clientes para descobrir quem trabalha em qual departamento
    clientes = db.query(Cliente).filter(Cliente.tenant_id == tenant_id).all()
    
    usuarios_por_depto = {
        "CONTABIL": set(),
        "FISCAL": set(),
        "PESSOAL": set(),
        "SOCIETARIO": set()
    }
    
    for c in clientes:
        if c.contabil and c.contabil.strip(): usuarios_por_depto["CONTABIL"].add(c.contabil.strip())
        if c.fiscal and c.fiscal.strip(): usuarios_por_depto["FISCAL"].add(c.fiscal.strip())
        if c.pessoal and c.pessoal.strip(): usuarios_por_depto["PESSOAL"].add(c.pessoal.strip())
        if c.societario and c.societario.strip(): usuarios_por_depto["SOCIETARIO"].add(c.societario.strip())
        
    # 3. Associa os usuários às equipes
    for depto_id, nomes_usuarios in usuarios_por_depto.items():
        equipe_id = equipes_criadas[depto_id].id
        
        for nome_usuario in nomes_usuarios:
            # Tenta encontrar o usuário pelo nome (aproximado)
            usr = db.query(Usuario).filter(
                Usuario.tenant_id == tenant_id, 
                Usuario.nome.ilike(f"%{nome_usuario}%")
            ).first()
            
            if usr:
                # Verifica se já está na equipe
                assoc_existe = db.query(UsuarioEquipe).filter(
                    UsuarioEquipe.equipe_id == equipe_id,
                    UsuarioEquipe.usuario_id == usr.id
                ).first()
                
                if not assoc_existe:
                    db.add(UsuarioEquipe(tenant_id=tenant_id, equipe_id=equipe_id, usuario_id=usr.id))
                    print(f"Usuário {usr.nome} adicionado à equipe {equipes_criadas[depto_id].nome}.")
            
    # 4. Atualiza os clientes para apontarem para as Equipes em vez dos nomes!
    for c in clientes:
        if c.contabil and c.contabil.strip(): c.contabil = "Contábil A"
        if c.fiscal and c.fiscal.strip(): c.fiscal = "Fiscal A"
        if c.pessoal and c.pessoal.strip(): c.pessoal = "Pessoal A"
        if c.societario and c.societario.strip(): c.societario = "Societário A"
        
    db.commit()
    print("Migração de clientes para as novas equipes concluída!")
    
if __name__ == "__main__":
    run()
