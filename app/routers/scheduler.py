from app.core.timezone import agora_br, hoje_br
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app import models
from app.database import get_db
from app.core.email_service import email_service
from app.api.deps import verify_scheduler_key
from app.core.task_engine import run_task_engine
from app.core.cron_solicitacoes import run_cron_solicitacoes_recorrentes

router = APIRouter()


@router.post("/check-overdue")
async def check_overdue_tasks(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Varre os protocolos/tarefas e marca como ATRASADO os vencidos.
    Protegida por X-Scheduler-Key header. Chamada pelo Cloud Scheduler.
    """
    # Rotinas de sistema operam em todos os tenants
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    today = hoje_br()

    tarefas_atrasadas = db.query(models.Tarefa).filter(
        models.Tarefa.vencimento < today,
        models.Tarefa.status != 'ENTREGUE',
        models.Tarefa.status != 'ATRASADO'
    ).all()

    contador = 0
    for tarefa in tarefas_atrasadas:
        tarefa.status = 'ATRASADO'
        contador += 1

    db.commit()
    return {"status": "success", "updated_count": contador}


@router.post("/daily-report")
async def daily_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Gera relatório diário e envia para a gerência.
    Protegida por X-Scheduler-Key header. Chamada pelo Cloud Scheduler.
    """
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    today = hoje_br()
    entregas_hoje = db.query(models.Protocolo).filter(
        models.Protocolo.data >= datetime.combine(today, datetime.min.time())
    ).count()

    corpo_html = f"""
    <div style="font-family: 'Inter', 'Roboto', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
        <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
            <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">RELATÓRIO DIÁRIO DE OPERAÇÃO</p>
        </div>
        <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Foram realizados <strong>{entregas_hoje}</strong> protocolos na plataforma hoje.</p>
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                <p style="color: #64748b; font-size: 12px; margin: 0; font-weight: bold;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</p>
                <p style="color: #94a3b8; font-size: 10px; margin: 5px 0 0;">Monitoramento legal de abertura de mensagem.</p>
            </div>
        </div>
    </div>
    """

    admin_email = "gerencia@janiopontes.com.br"
    background_tasks.add_task(email_service.enviar_email, admin_email, f"Relatório Diário — {today.strftime('%d/%m/%Y')}", corpo_html)

    return {"status": "success", "report_sent_to": admin_email, "entregas_hoje": entregas_hoje}


@router.post("/run-engine")
async def trigger_task_engine(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Gatilho para rodar o motor de tarefas (Restrito e sem ações de disparo externo).
    """
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass
        
    cliente = db.query(models.Cliente).first()
    if not cliente:
        return {"status": "error", "message": "Sem dados base"}
        
    resultado = run_task_engine(db, cliente.tenant_id)
    return resultado

@router.post("/run-cron-solicitacoes")
async def trigger_cron_solicitacoes(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Roda a rotina diária de criação automática de solicitações recorrentes.
    """
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass
        
    cliente = db.query(models.Cliente).first()
    if not cliente:
        return {"status": "error", "message": "Sem dados base"}
        
    resultado = await run_cron_solicitacoes_recorrentes(db, cliente.tenant_id)
    return resultado

@router.post("/whatsapp-reminders")
async def send_whatsapp_reminders(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Envia lembrete via Chatwoot (WhatsApp) para clientes com protocolos não lidos.
    Protegida por X-Scheduler-Key header. Chamada pelo Cloud Scheduler.
    """
    from sqlalchemy import not_, or_, text
    from datetime import timedelta
    from app.core.chatwoot_service import chatwoot_service
    from collections import defaultdict
    import re
    
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass
        
    agora = agora_br()
    limite_notificacao = agora - timedelta(hours=24)

    # Buscar protocolos não lidos que não foram notificados nas últimas 24h
    protocolos = db.query(models.Protocolo).filter(
        models.Protocolo.conf_recto == None,
        models.Protocolo.status_envio == 'ENVIADO',
        models.Protocolo.acao.ilike('%ENVIAR%'),
        or_(
            models.Protocolo.link_arquivo == None,
            not_(models.Protocolo.link_arquivo.startswith('SEM_ENVIO:'))
        ),
        or_(
            models.Protocolo.wpp_notif == None,
            models.Protocolo.wpp_notif < limite_notificacao
        )
    ).all()
    
    # 1. Agrupar protocolos pelo número de WhatsApp (garante 1 msg por número)
    protocolos_por_wpp = defaultdict(list)
    nome_por_wpp = {}
    email_por_wpp = {}
    wpp_original_por_wpp = {}
    
    for p in protocolos:
        cliente_db = db.query(models.Cliente).filter(
            models.Cliente.tenant_id == p.tenant_id,
            models.Cliente.cliente == p.cliente
        ).first()
        
        if not cliente_db:
            continue
            
        telefone_raw = getattr(cliente_db, 'telefone', None)
        if not telefone_raw:
            continue
            
        telefones = re.split(r'[,;/]', telefone_raw)
        wpp = telefones[0].strip() if telefones else None
        if not wpp:
            continue
            
        # Extrair apenas números para garantir o agrupamento correto
        wpp_clean = re.sub(r'[^0-9]', '', wpp)
        if not wpp_clean:
            continue
            
        chave = (p.tenant_id, wpp_clean)
        protocolos_por_wpp[chave].append(p)
        
        # Salva os dados do primeiro cliente encontrado para este número
        if chave not in nome_por_wpp:
            nome_por_wpp[chave] = cliente_db.cliente
            email_por_wpp[chave] = f"wpp_{wpp_clean}@cliente.local"
            wpp_original_por_wpp[chave] = wpp
            
    contador_mensagens = 0
    
    # 2. Enviar 1 mensagem por número de WhatsApp com o total de protocolos
    for chave, lista_p in protocolos_por_wpp.items():
        tenant_id, wpp_clean = chave
        nome_cliente = nome_por_wpp[chave]
        email = email_por_wpp[chave]
        wpp = wpp_original_por_wpp[chave]
        
        total = len(lista_p)
        
        logger.info(f"[WPP] Enviando para '{nome_cliente}' → tel: {wpp} | {total} protocolo(s)")
        
        sucesso = await chatwoot_service.send_template_notification(
            name=nome_cliente,
            email=email,
            template_name="automatico_protocolos",
            phone_number=wpp,
            template_params=[nome_cliente, str(total)]
        )
        
        if sucesso:
            for p in lista_p:
                p.wpp_notif = agora
            db.commit()  # Commitar a cada sucesso evita reenvios por timeout do Cloud Scheduler
            contador_mensagens += 1
            logger.info(f"[WPP] ✅ Enviado com sucesso para '{nome_cliente}' ({wpp})")
        else:
            logger.warning(f"[WPP] ❌ Falha ao enviar para '{nome_cliente}' ({wpp})")
            
    return {"status": "success", "clientes_notificados": contador_mensagens}


@router.post("/backup-database")
async def backup_database(
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Exporta o banco PostgreSQL como CSVs compactados em ZIP
    e faz upload na pasta BACKUPS_SISTEMA do Google Drive.
    Remove backups com mais de 30 dias automaticamente.
    Protegida por X-Scheduler-Key. Chamada pelo Cloud Scheduler (semanal).
    """
    from app.core.backup_service import gerar_backup_zip, upload_backup_drive, limpar_backups_antigos

    try:
        zip_bytes, nome_arquivo = gerar_backup_zip(db)
        link = upload_backup_drive(zip_bytes, nome_arquivo)
        removidos = limpar_backups_antigos(dias_retencao=30)

        return {
            "status": "success",
            "arquivo": nome_arquivo,
            "link": link,
            "tamanho_kb": round(len(zip_bytes) / 1024, 1),
            "backups_antigos_removidos": removidos
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/societario-alerts")
async def send_societario_alerts(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _auth: bool = Depends(verify_scheduler_key)
):
    """
    Verifica vencimentos do controle societário e envia alertas
    com 30, 15, 10 e 5 dias de antecedência.
    """
    from sqlalchemy import text
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    hoje = hoje_br()
    dias_alerta = [30, 15, 10, 5]

    # Busca e-mails do societário
    usuarios_societario = db.query(models.Usuario).join(models.UsuarioEquipe).join(models.Equipe).filter(
        models.Equipe.nome.ilike("%societ%"),
        models.Usuario.ativo == True
    ).all()
    emails_alvo = [u.email for u in usuarios_societario if u.email]
    
    if not emails_alvo:
        emails_alvo = ["gerencia@janiopontes.com.br"]

    # Verifica os 5 modelos
    from app.models.documentos_societarios import LicencaLocalizacao, AlvaraSanitario, AVCB, InscricaoMunicipal
    modelos_servicos = [
        (models.CertificadoDigital, "Certificado Digital"),
        (LicencaLocalizacao, "Licença/Localização"),
        (AlvaraSanitario, "Alvará Sanitário"),
        (AVCB, "AVCB"),
        (InscricaoMunicipal, "Inscrição Municipal")
    ]

    alertas_enviados = 0

    for Model, nome_servico in modelos_servicos:
        docs = db.query(Model).filter(Model.status != "VENCIDO").all()
        for doc in docs:
            dias_restantes = (doc.vencimento - hoje).days
            
            # Se for dia de alerta
            if dias_restantes in dias_alerta:
                cliente_nome = doc.cliente.cliente if doc.cliente else "Desconhecido"
                assunto = f"ALERTA DE VENCIMENTO: {nome_servico} - {cliente_nome} ({dias_restantes} dias)"
                
                corpo_html = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                    <h2 style="color: #d97706;">Aviso de Vencimento Próximo</h2>
                    <p>O documento abaixo irá vencer em <strong>{dias_restantes} dias</strong>.</p>
                    <ul style="line-height: 1.6;">
                        <li><strong>Cliente:</strong> {cliente_nome}</li>
                        <li><strong>Documento:</strong> {nome_servico}</li>
                        <li><strong>Data de Vencimento:</strong> {doc.vencimento.strftime('%d/%m/%Y')}</li>
                    </ul>
                    <p>Por favor, providencie a renovação e atualize o sistema.</p>
                </div>
                """
                
                for email in emails_alvo:
                    background_tasks.add_task(email_service.enviar_email, email, assunto, corpo_html)
                    alertas_enviados += 1

    return {"status": "success", "alertas_enviados": alertas_enviados, "emails_alvo": emails_alvo}

