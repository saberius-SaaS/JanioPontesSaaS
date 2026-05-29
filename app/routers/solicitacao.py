from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.email_service import email_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/solicitacoes", response_class=HTMLResponse)
async def list_solicitacoes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    solicitacoes = db.query(models.Solicitacao).filter(
        models.Solicitacao.tenant_id == current_user.tenant_id
    ).order_by(models.Solicitacao.data.desc()).all()
    
    clientes = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == current_user.tenant_id,
        models.Cliente.status == 'ATIVO'
    ).order_by(models.Cliente.cliente).all()

    return templates.TemplateResponse(request=request, name="solicitacoes.html", context={
        "request": request,
        "user": current_user,
        "solicitacoes": solicitacoes,
        "clientes": clientes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.post("/solicitacoes", response_class=HTMLResponse)
async def create_solicitacao(
    request: Request,
    cliente: str = Form(...),
    pedido: str = Form(...),
    email: str = Form(None),
    id_tarefa: str = Form("AVULSA"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    nova = models.Solicitacao(
        tenant_id=current_user.tenant_id,
        id_legado=f"SOL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
        data=datetime.now(),
        cliente=cliente,
        email=email,
        pedido=pedido,
        id_tarefa=id_tarefa,
        status="PENDENTE",
        qtd_avisos=0,
        responsavel=current_user.nome
    )
    db.add(nova)
    db.commit()
    
    if email:
        assunto = f"Nova Solicitação: Janio Pontes Contabilidade"
        corpo = f"""
        <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
            <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
                <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">Nova Solicitação / Mensagem</p>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a),</p>
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Uma nova solicitação foi registrada para <strong>{cliente}</strong>:</p>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 14px; color: #1e293b; white-space: pre-wrap;">{pedido}</p>
                </div>
                <p style="color: #64748b; font-size: 12px;">Responsável: {current_user.nome}</p>
            </div>
        </div>
        """
        await email_service.enviar_email(para=email, assunto=assunto, corpo_html=corpo)
        
    return RedirectResponse(url="/solicitacoes", status_code=303)

@router.post("/solicitacoes/{id}/cobrar", response_class=HTMLResponse)
async def cobrar_solicitacao(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    solic = db.query(models.Solicitacao).filter(
        models.Solicitacao.id == id,
        models.Solicitacao.tenant_id == current_user.tenant_id
    ).first()
    
    if solic:
        solic.qtd_avisos = (solic.qtd_avisos or 0) + 1
        solic.ultima_cobranca = datetime.now()
        db.commit()
        
        if solic.email:
            assunto = f"Lembrete: Solicitação Janio Pontes Contabilidade"
            corpo = f"""
            <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
                <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
                    <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">Aviso / Lembrete</p>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
                    <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a),</p>
                    <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Gostaríamos de relembrar a seguinte solicitação pendente para <strong>{solic.cliente}</strong>:</p>
                    <div style="background: #fffbeb; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #fde68a;">
                        <p style="margin: 0; font-size: 14px; color: #92400e; white-space: pre-wrap;">{solic.pedido}</p>
                    </div>
                    <p style="color: #64748b; font-size: 12px;">Responsável: {current_user.nome}</p>
                </div>
            </div>
            """
            await email_service.enviar_email(para=solic.email, assunto=assunto, corpo_html=corpo)
        
    return RedirectResponse(url="/solicitacoes", status_code=303)

@router.post("/solicitacoes/{id}/concluir", response_class=HTMLResponse)
async def concluir_solicitacao(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    solic = db.query(models.Solicitacao).filter(
        models.Solicitacao.id == id,
        models.Solicitacao.tenant_id == current_user.tenant_id
    ).first()
    
    if solic:
        solic.status = "ENTREGUE"
        solic.data_envio = datetime.now()
        db.commit()
        
    return RedirectResponse(url="/solicitacoes", status_code=303)
