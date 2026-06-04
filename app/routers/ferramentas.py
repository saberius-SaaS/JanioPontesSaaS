from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.email_service import email_service
from app.core.task_engine import run_task_engine
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/ferramentas", response_class=HTMLResponse)
async def list_ferramentas(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)
        
    clientes = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == current_user.tenant_id,
        models.Cliente.status == 'ATIVO'
    ).order_by(models.Cliente.cliente).all()

    return templates.TemplateResponse(request=request, name="ferramentas.html", context={
        "request": request,
        "user": current_user,
        "clientes": clientes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.post("/ferramentas/gerador", response_class=HTMLResponse)
async def trigger_gerador(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)
        
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(current_user.tenant_id)}';"))
    except Exception:
        pass
        
    logger.info(f"Gerador de tarefas acionado manualmente por {current_user.nome}")
    resultado = run_task_engine(db, current_user.tenant_id)
    
    msg = f"Gerador concluído! Mês referência: {resultado.get('mes_referencia')}. Tarefas Novas: {resultado.get('novas')}, Atualizadas: {resultado.get('atualizadas')}."
    logger.info(msg)
    
    # Redireciona de volta
    return RedirectResponse(url="/ferramentas", status_code=303)


@router.post("/ferramentas/comunicado", response_class=HTMLResponse)
async def trigger_comunicado(
    request: Request,
    background_tasks: BackgroundTasks,
    assunto: str = Form(...),
    mensagem: str = Form(...),
    alvo: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    """
    Dispara comunicado oficial para os clientes.
    """
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)

    clientes_emails = []
    
    if alvo == "TODOS":
        clientes = db.query(models.Cliente).filter(
            models.Cliente.tenant_id == current_user.tenant_id,
            models.Cliente.status == 'ATIVO'
        ).all()
        clientes_emails = [c.email for c in clientes if c.email]
    else:
        cli = db.query(models.Cliente).filter(
            models.Cliente.tenant_id == current_user.tenant_id,
            models.Cliente.cliente == alvo
        ).first()
        if cli and cli.email:
            clientes_emails = [cli.email]
            
    if not clientes_emails:
        logger.warning("Comunicado não enviado: Nenhum e-mail de destino válido encontrado.")
        return RedirectResponse(url="/ferramentas", status_code=303)

    # Convert newlines to HTML <br>
    mensagem_html = mensagem.replace('\n', '<br>')

    corpo = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
        <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
            <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">Comunicado Oficial</p>
        </div>
        <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a) Cliente,</p>
            <div style="background: #f1f5f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; color: #1e293b; line-height: 1.6;">
                {mensagem_html}
            </div>
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                <p style="color: #64748b; font-size: 12px; margin: 0; font-weight: bold;">Enviado por: {current_user.nome}</p>
                <p style="color: #94a3b8; font-size: 10px; margin: 5px 0 0;">Este é um aviso automático.</p>
            </div>
        </div>
    </div>
    """
    
    # Enviar em background (se for "TODOS", envia um loop)
    for email in clientes_emails:
        background_tasks.add_task(email_service.enviar_email, email, assunto, corpo)
        
    logger.info(f"Comunicado '{assunto}' enviado para {len(clientes_emails)} emails.")
    
    return RedirectResponse(url="/ferramentas", status_code=303)
