from fastapi import APIRouter, Depends, Request, Form, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.drive_service import drive_service
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

    return templates.TemplateResponse("protocolos.html", {
        "request": request,
        "protocolos": protocolos,
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
    return templates.TemplateResponse("partials/protocolos_table.html", {"request": request, "protocolos": protocolos})


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

    # Upload para o Google Drive (real ou mock, depende de DRIVE_MODE)
    link = "Não anexado"
    if arquivo and arquivo.filename:
        link = await drive_service.upload_file(arquivo)

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

    # Log de Histórico (transacional)
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

    # Disparar E-mail em background (real ou mock, depende de EMAIL_MODE)
    if email:
        corpo_html = f"<h2>Novo Documento Disponível</h2><p>Olá, o protocolo {prt_code} referente a {obrigacao} foi gerado e está disponível.</p><p><a href='{link}'>Acessar Documento</a></p>"
        background_tasks.add_task(email_service.enviar_email, email, f"Novo Documento: {obrigacao}", corpo_html)

    protocolos = db.query(models.Protocolo).order_by(models.Protocolo.data.desc()).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/protocolos_table.html", {"request": request, "protocolos": protocolos})
