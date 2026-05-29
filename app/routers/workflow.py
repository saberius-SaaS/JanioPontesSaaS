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

    # Passamos os departamentos também para o dropdown
    deptos_raw = db.query(models.RegraObrigacao.departamento).filter(
        models.RegraObrigacao.tenant_id == current_user.tenant_id,
        models.RegraObrigacao.departamento != None
    ).distinct().all()
    departamentos = sorted(set(d[0] for d in deptos_raw if d[0]))

    return templates.TemplateResponse(request=request, name="workflows.html", context={
        "request": request,
        "user": current_user,
        "workflows": workflows,
        "departamentos": departamentos,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.post("/workflows", response_class=HTMLResponse)
async def create_workflow(
    request: Request,
    fase_atual: str = Form(...),
    proxima_fase: str = Form(...),
    dias: int = Form(0),
    departamento: str = Form(None),
    acao: str = Form(None),
    responsavel_padrao: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    novo = models.Workflow(
        tenant_id=current_user.tenant_id,
        fase_atual=fase_atual.strip(),
        proxima_fase=proxima_fase.strip(),
        dias=dias,
        departamento=departamento,
        acao=acao,
        responsavel_padrao=responsavel_padrao
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
    departamento: str = Form(None),
    acao: str = Form(None),
    responsavel_padrao: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    wf = db.query(models.Workflow).filter(
        models.Workflow.id == id,
        models.Workflow.tenant_id == current_user.tenant_id
    ).first()

    if wf:
        wf.fase_atual = fase_atual.strip()
        wf.proxima_fase = proxima_fase.strip()
        wf.dias = dias
        wf.departamento = departamento
        wf.acao = acao
        wf.responsavel_padrao = responsavel_padrao
        db.commit()

    return RedirectResponse(url="/workflows", status_code=303)

@router.post("/workflows/{id}/excluir", response_class=HTMLResponse)
async def excluir_workflow(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    wf = db.query(models.Workflow).filter(
        models.Workflow.id == id,
        models.Workflow.tenant_id == current_user.tenant_id
    ).first()

    if wf:
        db.delete(wf)
        db.commit()

    return RedirectResponse(url="/workflows", status_code=303)
