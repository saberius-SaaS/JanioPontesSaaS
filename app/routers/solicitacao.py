from app.core.timezone import agora_br, hoje_br
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.email_service import email_service
from app.core.storage_service import storage_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/solicitacoes", response_class=HTMLResponse)
async def list_solicitacoes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    from sqlalchemy import case
    
    solicitacoes = db.query(models.Solicitacao).filter(
        models.Solicitacao.tenant_id == current_user.tenant_id
    ).order_by(
        case(
            (models.Solicitacao.status != 'ENTREGUE', 0),
            else_=1
        ),
        models.Solicitacao.data.desc()
    ).all()
    
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
    # Se o email não veio no form, busca no cadastro do cliente ANTES de instanciar a Solicitação
    if not email:
        cli = db.query(models.Cliente).filter(
            models.Cliente.tenant_id == current_user.tenant_id,
            models.Cliente.cliente == cliente
        ).first()
        if cli and cli.email:
            email = cli.email

    id_legado_gerado = f"SOL-{agora_br().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    
    nova = models.Solicitacao(
        tenant_id=current_user.tenant_id,
        id_legado=id_legado_gerado,
        data=agora_br(),
        cliente=cliente,
        email=email,
        pedido=pedido,
        id_tarefa=id_tarefa,
        status="PENDENTE",
        qtd_avisos=0,
        responsavel=current_user.nome
    )
    db.add(nova)
    
    # Store variable before commit to avoid lazy-load RLS issues
    resp_nome = current_user.nome 
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
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a) {cliente},</p>
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Uma nova solicitação foi registrada para <strong>{cliente}</strong>:</p>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 14px; color: #1e293b; white-space: pre-wrap;">{pedido}</p>
                </div>
                <p style="text-align: center; margin: 30px 0;">
                    <a href='{request.base_url}s/{id_legado_gerado}' style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 12px;">Responder Solicitação</a>
                </p>
                <p style="color: #64748b; font-size: 12px;">Responsável: {resp_nome}</p>
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
        # Extrair variáveis antes do commit
        resp_nome = current_user.nome
        cli_nome = solic.cliente
        ped = solic.pedido
        idl = solic.id_legado
        eml = solic.email

        solic.qtd_avisos = (solic.qtd_avisos or 0) + 1
        solic.ultima_cobranca = agora_br()
        db.commit()
        
        if eml:
            assunto = f"Lembrete: Solicitação Janio Pontes Contabilidade"
            corpo = f"""
            <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
                <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
                    <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">Aviso / Lembrete</p>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
                    <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a) {cli_nome},</p>
                    <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Gostaríamos de relembrar a seguinte solicitação pendente para <strong>{cli_nome}</strong>:</p>
                    <div style="background: #fffbeb; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #fde68a;">
                        <p style="margin: 0; font-size: 14px; color: #92400e; white-space: pre-wrap;">{ped}</p>
                    </div>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href='{request.base_url}s/{idl}' style="display: inline-block; background-color: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 12px;">Responder Solicitação</a>
                    </p>
                    <p style="color: #64748b; font-size: 12px;">Responsável: {resp_nome}</p>
                </div>
            </div>
            """
            await email_service.enviar_email(para=eml, assunto=assunto, corpo_html=corpo)
        
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
        solic.data_envio = agora_br()
        db.commit()
        
    return RedirectResponse(url="/solicitacoes", status_code=303)


@router.get("/s/{id_legado}", response_class=HTMLResponse)
async def ver_solicitacao_publica(
    request: Request,
    id_legado: str,
    db: Session = Depends(get_db)
):
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass
    
    solic = db.query(models.Solicitacao).filter(models.Solicitacao.id_legado == id_legado).first()
    if not solic:
        return HTMLResponse("<h1>Solicitação não encontrada ou já expirada.</h1>", status_code=404)
        
    return templates.TemplateResponse(request=request, name="portal_solicitacao.html", context={
        "request": request,
        "solicitacao": solic,
        "sucesso": False
    })


@router.post("/s/{id_legado}", response_class=HTMLResponse)
async def responder_solicitacao_publica(
    request: Request,
    id_legado: str,
    background_tasks: BackgroundTasks,
    mensagem: str = Form(None),
    arquivo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass
        
    solic = db.query(models.Solicitacao).filter(models.Solicitacao.id_legado == id_legado).first()
    if not solic:
        return HTMLResponse("<h1>Solicitação não encontrada.</h1>", status_code=404)
        
    link = None
    if arquivo and arquivo.filename:
        link = await storage_service.upload_file(arquivo)
        
    solic.status = "ENTREGUE"
    solic.data_envio = agora_br()
    resposta_texto = ""
    if mensagem:
        resposta_texto += f"\n\n[RESPOSTA DO CLIENTE]: {mensagem}"
    if link:
        resposta_texto += f"\n[ARQUIVO ANEXADO]: {link}"
        
    solic.pedido = solic.pedido + resposta_texto
    
    # Extrai dados antes do commit para evitar ObjectDeletedError no lazy-load pós-commit
    s_responsavel = solic.responsavel
    s_tenant_id = solic.tenant_id
    s_cliente = solic.cliente
    db.commit()
    
    if s_responsavel:
        # Precisamos reativar o bypass para buscar o usuário responsável (pois o commit encerrou a transação)
        try:
            db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        except Exception:
            pass
            
        user_responsavel = db.query(models.Usuario).filter(
            models.Usuario.nome == s_responsavel,
            models.Usuario.tenant_id == s_tenant_id
        ).first()
        if user_responsavel and user_responsavel.email:
            assunto = f"Solicitação Respondida: {s_cliente}"
            corpo = f"""
            <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
                <div style="background: #10b981; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">CLIENTE RESPONDEU</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
                    <p>O cliente <strong>{s_cliente}</strong> respondeu a sua solicitação.</p>
                    <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px; white-space: pre-wrap;">{mensagem or "Nenhuma mensagem enviada."}</div>
                    <p><a href="{link or '#'}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px;">Acessar Anexo (se houver)</a></p>
                </div>
            </div>
            """
            background_tasks.add_task(email_service.enviar_email, user_responsavel.email, assunto, corpo)
            
    return templates.TemplateResponse(request=request, name="portal_solicitacao.html", context={
        "request": request,
        "solicitacao": solic,
        "sucesso": True
    })
