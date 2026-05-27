from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login

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
