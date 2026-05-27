from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/tarefas", response_class=HTMLResponse)
async def list_tarefas(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    tarefas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['PENDENTE', 'ATRASADO'])
    ).order_by(models.Tarefa.vencimento.asc()).limit(200).all()
    
    return templates.TemplateResponse(request=request, name="tarefas.html", context={
        "request": request,
        "user": current_user,
        "tarefas": tarefas,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })
