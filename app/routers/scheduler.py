from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app import models
from app.database import get_db
from app.core.email_service import email_service
from app.api.deps import verify_scheduler_key
from app.core.task_engine import run_task_engine

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

    today = datetime.now().date()

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

    today = datetime.now().date()
    entregas_hoje = db.query(models.Protocolo).filter(
        models.Protocolo.data >= datetime.combine(today, datetime.min.time())
    ).count()

    corpo_html = f"<h2>Relatório Diário — {today.strftime('%d/%m/%Y')}</h2><p>Foram realizados <strong>{entregas_hoje}</strong> protocolos na plataforma hoje.</p>"

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

