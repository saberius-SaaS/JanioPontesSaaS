import datetime
import calendar
import logging
from sqlalchemy.orm import Session
from app.models import SolicitacaoRecorrente, Solicitacao, Cliente
from app.core.task_engine import is_dia_util
from app.core.email_service import email_service
from app.models.base import gerar_uuid

logger = logging.getLogger(__name__)

def get_next_business_day(date_obj: datetime.date) -> datetime.date:
    """Avança a data até encontrar o próximo dia útil."""
    current_date = date_obj
    while not is_dia_util(current_date):
        current_date += datetime.timedelta(days=1)
    return current_date

def build_template_text(template: str, hoje: datetime.date) -> str:
    """Substitui as variáveis de template {mes_anterior} e {ano_anterior}."""
    if not template: return ""
    
    # Calcula mês e ano anterior
    mes_anterior = hoje.month - 1
    ano_anterior = hoje.year
    if mes_anterior == 0:
        mes_anterior = 12
        ano_anterior -= 1
        
    mes_str = f"{mes_anterior:02d}"
    ano_str = str(ano_anterior)
    
    return template.replace("{mes_anterior}", mes_str).replace("{ano_anterior}", ano_str)

async def run_cron_solicitacoes_recorrentes(db: Session, tenant_id: str, force_date: datetime.date = None):
    """
    Roda diariamente. Verifica regras ativas e gera solicitações.
    Se o dia da geração cair em final de semana/feriado, empurra para o próximo dia útil.
    """
    hoje = force_date or datetime.date.today()
    
    # Se hoje não é dia útil, a rotina não precisa fazer nada
    if not is_dia_util(hoje):
        logger.info(f"Cron Solicitações: {hoje} não é dia útil. Ignorando.")
        return {"status": "skipped", "reason": "not_business_day"}
        
    regras = db.query(SolicitacaoRecorrente).filter(
        SolicitacaoRecorrente.tenant_id == tenant_id,
        SolicitacaoRecorrente.ativo == True
    ).all()
    
    geradas = 0
    erros = 0
    
    for regra in regras:
        try:
            # Garante que o dia da geração não ultrapasse o último dia do mês atual
            last_day = calendar.monthrange(hoje.year, hoje.month)[1]
            dia_alvo = min(regra.dia_geracao, last_day)
            
            data_alvo_bruta = datetime.date(hoje.year, hoje.month, dia_alvo)
            data_alvo_ajustada = get_next_business_day(data_alvo_bruta)
            
            # Só executa se o dia ajustado for EXATAMENTE hoje
            if data_alvo_ajustada != hoje:
                continue
                
            cliente = db.query(Cliente).filter(Cliente.id == regra.cliente_id).first()
            if not cliente:
                continue
                
            titulo_resolvido = build_template_text(regra.titulo_template, hoje)
            descricao_resolvida = build_template_text(regra.descricao_template, hoje)
            
            # Hierarquia de E-mail
            email_destino = regra.email_override
            if not email_destino:
                dep_norm = str(regra.departamento).upper()
                if "FISCAL" in dep_norm: email_destino = cliente.email_fiscal
                elif "CONTABIL" in dep_norm: email_destino = cliente.email_contabil
                elif "PESSOAL" in dep_norm: email_destino = cliente.email_pessoal
                elif "SOCIETARIO" in dep_norm: email_destino = cliente.email_societario
                
            if not email_destino:
                email_destino = cliente.email
                
            # Verifica se já gerou hoje para evitar duplo disparo caso o cron rode duas vezes no mesmo dia
            hoje_inicio = datetime.datetime.combine(hoje, datetime.time.min)
            hoje_fim = datetime.datetime.combine(hoje, datetime.time.max)
            
            # O uuid da solicitação é gerado na criação ou instanciamento
            ja_existe = db.query(Solicitacao).filter(
                Solicitacao.tenant_id == tenant_id,
                Solicitacao.cliente == cliente.cliente,
                Solicitacao.data >= hoje_inicio,
                Solicitacao.data <= hoje_fim,
                Solicitacao.id_tarefa == "AVULSA",
                Solicitacao.pedido.like(f"%{titulo_resolvido}%")
            ).first()
            
            if ja_existe:
                continue
                
            pedido_completo = f"Assunto: {titulo_resolvido}\n\n{descricao_resolvida}"
            
            nova_solicitacao = Solicitacao(
                id_legado=f"SOL-REC-{hoje.strftime('%Y%m%d%H%M%S')}-{geradas}",
                tenant_id=tenant_id,
                data=datetime.datetime.now(),
                cliente=cliente.cliente,
                email=email_destino,
                pedido=pedido_completo,
                id_tarefa="AVULSA",
                responsavel=regra.responsavel,
                status="PENDENTE"
            )
            db.add(nova_solicitacao)
            db.commit()
            
            # Disparo do e-mail
            if email_destino:
                html_body = f"<p>Prezado Cliente,</p><p>{descricao_resolvida}</p>"
                await email_service.enviar_email(
                    para=email_destino,
                    assunto=titulo_resolvido,
                    corpo_html=html_body
                )
                
            geradas += 1
            
        except Exception as e:
            logger.error(f"Erro ao processar regra recorrente {regra.id}: {e}")
            db.rollback()
            erros += 1
            
    return {"status": "success", "geradas": geradas, "erros": erros}
