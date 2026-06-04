from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app import models
from app.database import get_db
from app.api.deps import require_cliente_login
from app.core import security
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/acesso/{protocolo_id}", response_class=HTMLResponse)
async def acesso_magico(
    request: Request,
    protocolo_id: str,
    db: Session = Depends(get_db)
):
    """
    Link Mágico: Recebe o ID do protocolo do e-mail, identifica o cliente,
    marca como lido, e faz auto-login redirecionando para o documento.
    """
    # Bypass RLS porque não temos tenant ainda
    try:
        db.execute("SET LOCAL app.bypass_rls = 'on';")
    except Exception:
        pass

    import uuid
    try:
        prot_uuid = uuid.UUID(protocolo_id)
    except Exception:
        # Tenta buscar pelo código PRT- se não for UUID
        protocolo = db.query(models.Protocolo).filter(models.Protocolo.protocolo == protocolo_id).first()
    else:
        protocolo = db.query(models.Protocolo).filter(models.Protocolo.id == prot_uuid).first()

    if not protocolo:
        return HTMLResponse("<h1>Link inválido ou expirado.</h1>", status_code=404)

    # Marca como lido se ainda não estiver
    if not protocolo.conf_recto:
        protocolo.conf_recto = datetime.now()
        db.commit()

    # Gera token de sessão do cliente
    expires = timedelta(days=30)
    # JWT precisa receber string ou dict no subject? security.create_access_token espera subject (que é o sub),
    # mas o nosso JWT recebe dict e extrai as coisas? Não, a nossa dependência pega payload.get("cliente").
    # Precisamos montar um dict para gerar o JWT, ou passar subject.
    # Vamos adaptar para a assinatura do create_access_token.
    token_data = {"sub": "cliente", "cliente": protocolo.cliente, "tenant_id": str(protocolo.tenant_id)}
    # O security.create_access_token aceita um subject (string) ou dicionário dependendo da implementação.
    # Como implementamos? O padrão fastapi template recebe subject: Union[str, Any].
    token = security.create_access_token(subject=token_data, expires_delta=expires)

    response = RedirectResponse(url=f"/portal/documento/{protocolo.id}", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="client_session",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",
        secure=True
    )
    return response

@router.get("/portal/login", response_class=HTMLResponse)
async def portal_login(request: Request):
    return templates.TemplateResponse(request, "portal/login.html", {"request": request})

@router.get("/portal", response_class=HTMLResponse)
async def portal_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}';")
        db.execute("SET LOCAL app.bypass_rls = 'off';")
    except Exception:
        pass

    # Buscar protocolos recentes
    protocolos = db.query(models.Protocolo).filter(
        models.Protocolo.cliente == cliente_nome
    ).order_by(models.Protocolo.data.desc()).limit(10).all()

    return templates.TemplateResponse(request, "portal/dashboard.html", {
        "request": request,
        "cliente": cliente_nome,
        "protocolos": protocolos
    })

@router.get("/portal/documento/{id}", response_class=HTMLResponse)
async def portal_documento(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(f"SET LOCAL app.current_tenant = '{tenant_id}';")
        db.execute("SET LOCAL app.bypass_rls = 'off';")
    except Exception:
        pass

    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.id == id,
        models.Protocolo.cliente == cliente_nome
    ).first()

    if not protocolo:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Extrair os links anexos (se hover mais de um, separados por ' | ')
    import re
    link_bruto = protocolo.link_arquivo or ""
    base_link = re.sub(r'\[.*?\]', '', link_bruto).strip()
    links = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]

    return templates.TemplateResponse(request, "portal/documento.html", {
        "request": request,
        "cliente": cliente_nome,
        "protocolo": protocolo,
        "links": links
    })

@router.get("/portal/logout")
async def portal_logout():
    response = RedirectResponse(url="/portal/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="client_session")
    return response
