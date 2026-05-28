from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/workflows", response_class=HTMLResponse)
async def list_workflows(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    workflows = db.query(models.Workflow).filter(
        models.Workflow.tenant_id == current_user.tenant_id
    ).order_by(models.Workflow.fase_atual).all()

    return templates.TemplateResponse(request=request, name="workflows.html", context={
        "request": request,
        "user": current_user,
        "workflows": workflows,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })


@router.post("/workflows", response_class=HTMLResponse)
async def create_workflow(
    request: Request,
    fase_atual: str = Form(...),
    proxima_fase: str = Form(...),
    dias: int = Form(0),
    departamento: str = Form(""),
    acao: str = Form(""),
    responsavel_padrao: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    novo = models.Workflow(
        tenant_id=current_user.tenant_id,
        fase_atual=fase_atual.upper().strip(),
        proxima_fase=proxima_fase.upper().strip(),
        dias=dias,
        departamento=departamento or None,
        acao=acao or None,
        responsavel_padrao=responsavel_padrao or None
    )
    db.add(novo)
    db.commit()
    return RedirectResponse(url="/workflows", status_code=303)


@router.post("/workflows/{id}/editar", response_class=HTMLResponse)
async def editar_workflow(
    request: Request,
    id: str,
    fase_atual: str = Form(...),
    proxima_fase: str = Form(...),
    dias: int = Form(0),
    departamento: str = Form(""),
    acao: str = Form(""),
    responsavel_padrao: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    workflow = db.query(models.Workflow).filter(
        models.Workflow.id == id,
        models.Workflow.tenant_id == current_user.tenant_id
    ).first()

    if workflow:
        workflow.fase_atual = fase_atual.upper().strip()
        workflow.proxima_fase = proxima_fase.upper().strip()
        workflow.dias = dias
        workflow.departamento = departamento or None
        workflow.acao = acao or None
        workflow.responsavel_padrao = responsavel_padrao or None
        db.commit()

    return RedirectResponse(url="/workflows", status_code=303)


@router.post("/workflows/{id}/excluir", response_class=HTMLResponse)
async def excluir_workflow(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    workflow = db.query(models.Workflow).filter(
        models.Workflow.id == id,
        models.Workflow.tenant_id == current_user.tenant_id
    ).first()

    if workflow:
        db.delete(workflow)
        db.commit()

    return RedirectResponse(url="/workflows", status_code=303)
