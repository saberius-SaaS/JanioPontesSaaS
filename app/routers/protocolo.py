from fastapi import APIRouter, Depends, Request, Form, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.storage_service import storage_service
from app.core.email_service import email_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 25


@router.get("/protocolos", response_class=HTMLResponse)
async def list_protocolos_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    offset = (page - 1) * PAGE_SIZE
    total = db.query(models.Protocolo).count()
    protocolos = db.query(models.Protocolo).order_by(models.Protocolo.data.desc()).offset(offset).limit(PAGE_SIZE).all()
    clientes = db.query(models.Cliente).filter(models.Cliente.status == "ATIVO").order_by(models.Cliente.cliente).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    protocolos_nao_lidos = db.query(models.Protocolo).filter(
        models.Protocolo.conf_recto == None
    ).order_by(models.Protocolo.data.desc()).all()

    return templates.TemplateResponse(request, "protocolos.html", {
        "protocolos": protocolos,
        "protocolos_nao_lidos": protocolos_nao_lidos,
        "clientes": clientes,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "user": current_user
    })


@router.get("/protocolos/search", response_class=HTMLResponse)
async def search_protocolos(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    query = db.query(models.Protocolo).order_by(models.Protocolo.data.desc())
    if q:
        query = query.filter(
            models.Protocolo.protocolo.ilike(f"%{q}%")
            | models.Protocolo.cliente.ilike(f"%{q}%")
        )
    protocolos = query.limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/protocolos_table.html", {"protocolos": protocolos})


@router.post("/protocolos", response_class=HTMLResponse)
async def create_protocolo(
    request: Request,
    background_tasks: BackgroundTasks,
    cliente: str = Form(...),
    obrigacao: str = Form(...),
    email: str = Form(None),
    arquivo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    prt_code = f"PRT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    link = "Não anexado"
    if arquivo and arquivo.filename:
        link = await storage_service.upload_file(arquivo)

    novo_protocolo = models.Protocolo(
        tenant_id=current_user.tenant_id,
        data=datetime.now(),
        protocolo=prt_code,
        cliente=cliente,
        obrigacao=obrigacao,
        email=email,
        link_arquivo=link,
        status_envio="ENVIADO",
        responsavel=current_user.nome
    )
    db.add(novo_protocolo)

    historico = models.HistoricoTarefa(
        tenant_id=current_user.tenant_id,
        mes_ano=datetime.now().strftime("%m/%Y"),
        cliente=cliente,
        obrigacao=obrigacao,
        status="ENTREGUE",
        protocolo=prt_code,
        acao="ENVIAR",
        responsavel=current_user.nome,
        id_controle=str(uuid.uuid4())
    )
    db.add(historico)
    db.commit()

    if email:
        corpo_html = f"""
        <div style="font-family: 'Inter', 'Roboto', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
            <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
                <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">ENVIO DE DOCUMENTOS</p>
            </div>
            <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a),</p>
                <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Informamos que o documento abaixo foi gerado e está disponível:</p>
                <table style="width: 100%; border-collapse: collapse; margin: 0 0 20px;">
                    <tr>
                        <td style="padding: 10px; background: #f1f5f9; border-radius: 8px 0 0 0; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Obrigação / Referência</td>
                        <td style="padding: 10px; background: #f1f5f9; border-radius: 0 8px 0 0; font-size: 14px; font-weight: bold; color: #1C3051;">{obrigacao}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Protocolo</td>
                        <td style="padding: 10px; font-size: 14px; font-weight: bold; color: #6366f1;">{prt_code}</td>
                    </tr>
                </table>
                <p style="text-align: center; margin: 30px 0;"><a href='https://app.janiopontes.com.br/acesso/{prt_code}' style="display: inline-block; background-color: #6366f1; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">Acessar no Portal do Cliente</a></p>
                <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                    <p style="color: #64748b; font-size: 12px; margin: 0; font-weight: bold;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</p>
                    <p style="color: #94a3b8; font-size: 10px; margin: 5px 0 0;">O link acima concede acesso seguro aos arquivos desta entrega.</p>
                </div>
            </div>
        </div>
        """
        background_tasks.add_task(email_service.enviar_email, email, f"Novo Documento: {obrigacao}", corpo_html)

    protocolos = db.query(models.Protocolo).order_by(models.Protocolo.data.desc()).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/protocolos_table.html", {"protocolos": protocolos})


@router.post("/protocolos/{protocolo_id}/baixa")
async def baixa_manual_protocolo(
    protocolo_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.id == protocolo_id,
        models.Protocolo.tenant_id == current_user.tenant_id
    ).first()
    
    if protocolo:
        protocolo.conf_recto = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        db.commit()
    
    # Retorna uma div vazia para remover o card da lista usando htmx (hx-swap="outerHTML")
    return HTMLResponse(content="")
