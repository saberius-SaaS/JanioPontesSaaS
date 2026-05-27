from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/tipos-tarefa", response_class=HTMLResponse)
async def list_tipos_tarefa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    tipos = db.query(models.TipoTarefaAvulsa).filter(
        models.TipoTarefaAvulsa.tenant_id == current_user.tenant_id
    ).order_by(models.TipoTarefaAvulsa.nome).all()

    return templates.TemplateResponse(request=request, name="tipos_tarefa.html", context={
        "request": request,
        "user": current_user,
        "tipos": tipos,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })


@router.post("/tipos-tarefa", response_class=HTMLResponse)
async def create_tipo_tarefa(
    request: Request,
    nome: str = Form(...),
    departamento: str = Form(""),
    descricao: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    novo = models.TipoTarefaAvulsa(
        tenant_id=current_user.tenant_id,
        nome=nome.upper().strip(),
        departamento=departamento or None,
        descricao=descricao or None,
        status="ATIVO"
    )
    db.add(novo)
    db.commit()
    return RedirectResponse(url="/tipos-tarefa", status_code=303)


@router.post("/tipos-tarefa/{id}/editar", response_class=HTMLResponse)
async def editar_tipo_tarefa(
    request: Request,
    id: str,
    nome: str = Form(...),
    departamento: str = Form(""),
    descricao: str = Form(""),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    tipo = db.query(models.TipoTarefaAvulsa).filter(
        models.TipoTarefaAvulsa.id == id,
        models.TipoTarefaAvulsa.tenant_id == current_user.tenant_id
    ).first()

    if tipo:
        tipo.nome = nome.upper().strip()
        tipo.departamento = departamento or None
        tipo.descricao = descricao or None
        tipo.status = status
        db.commit()

    return RedirectResponse(url="/tipos-tarefa", status_code=303)


@router.post("/tipos-tarefa/{id}/excluir", response_class=HTMLResponse)
async def excluir_tipo_tarefa(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    tipo = db.query(models.TipoTarefaAvulsa).filter(
        models.TipoTarefaAvulsa.id == id,
        models.TipoTarefaAvulsa.tenant_id == current_user.tenant_id
    ).first()

    if tipo:
        db.delete(tipo)
        db.commit()

    return RedirectResponse(url="/tipos-tarefa", status_code=303)
