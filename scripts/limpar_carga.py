import os
import sys
import logging

# Garante que as importações do app funcionem se executado da raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.models import Cliente, RegraObrigacao, Protocolo, HistoricoTarefa, Tarefa, Perfil, TipoTarefaAvulsa, Workflow, Usuario

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def limpar_banco():
    db: Session = SessionLocal()
    try:
        logging.info("🧹 Iniciando limpeza do banco para nova carga...")
        
        # Desliga RLS temporariamente para ter permissão de apagar
        db.execute(text("SET SESSION app.bypass_rls = 'on';"))
        
        # Apagar tarefas, históricos e protocolos primeiro (devido às foreign keys para clientes)
        tarefas_deletadas = db.query(Tarefa).delete()
        historico_deletado = db.query(HistoricoTarefa).delete()
        protocolos_deletados = db.query(Protocolo).delete()
        logging.info(f"Apagado: {tarefas_deletadas} tarefas, {historico_deletado} históricos, {protocolos_deletados} protocolos.")
        
        # Apagar tabelas de domínio principal (na ordem segura)
        clientes_deletados = db.query(Cliente).delete()
        regras_deletadas = db.query(RegraObrigacao).delete()
        perfis_deletados = db.query(Perfil).delete()
        tipos_deletados = db.query(TipoTarefaAvulsa).delete()
        workflows_deletados = db.query(Workflow).delete()
        
        # Para usuários, excluímos as associações de equipe primeiro para não dar erro de foreign key
        from app.models import UsuarioEquipe
        # Tentar apagar usuários e suas equipes (preservando quem for MASTER)
        usuarios_para_deletar = db.query(Usuario).filter(Usuario.nivel != 'MASTER').all()
        ids_usuarios = [u.id for u in usuarios_para_deletar]
        
        if ids_usuarios:
            equipes_deletadas = db.query(UsuarioEquipe).filter(UsuarioEquipe.usuario_id.in_(ids_usuarios)).delete(synchronize_session=False)
            usuarios_deletados = db.query(Usuario).filter(Usuario.id.in_(ids_usuarios)).delete(synchronize_session=False)
        else:
            equipes_deletadas = 0
            usuarios_deletados = 0
        
        db.commit()
        
        logging.info(f"Apagado: {clientes_deletados} Clientes.")
        logging.info(f"Apagado: {regras_deletadas} Regras/Obrigações.")
        logging.info(f"Apagado: {perfis_deletados} Perfis.")
        logging.info(f"Apagado: {tipos_deletados} Tipos de Tarefa Avulsa.")
        logging.info(f"Apagado: {workflows_deletados} Workflows.")
        logging.info(f"Apagado: {usuarios_deletados} Usuários (excluindo MASTER).")
        
        logging.info("✅ Limpeza concluída com sucesso! O banco está pronto para a nova migração.")
        
    except Exception as e:
        db.rollback()
        logging.error(f"❌ Erro ao limpar o banco: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    limpar_banco()
