from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/compliance", response_class=HTMLResponse)
async def compliance_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    hoje = date.today()
    
    # Tarefas atrasadas (risco imediato)
    atrasadas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'ATRASADO'
    ).order_by(models.Tarefa.vencimento_legal.asc()).all()
    
    # Tarefas pendentes com vencimento_legal próximo (próximos 5 dias)
    # ou já vencidas mas que o status não foi atualizado (por segurança)
    pendentes_risco = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'PENDENTE',
        models.Tarefa.vencimento_legal != None
    ).all()
    
    em_risco = []
    for t in pendentes_risco:
        if t.vencimento_legal:
            dias_restantes = (t.vencimento_legal - hoje).days
            if dias_restantes <= 5:
                # Adiciona campo virtual temporário para o template
                t.dias_restantes = dias_restantes
                em_risco.append(t)
                
    em_risco.sort(key=lambda x: x.vencimento_legal)
    
    return templates.TemplateResponse(request=request, name="compliance.html", context={
        "request": request,
        "user": current_user,
        "atrasadas": atrasadas,
        "em_risco": em_risco,
        "total_atrasadas": len(atrasadas),
        "total_risco": len(em_risco),
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })
