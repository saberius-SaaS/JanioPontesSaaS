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
    
    # Todas as tarefas ativas que não estão entregues ou arquivadas
    tarefas_ativas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.notin_(['ENTREGUE', 'ARQUIVADO', 'IGNORADO']),
        models.Tarefa.vencimento != None
    ).all()
    
    atrasadas = []
    em_risco = []
    
    for t in tarefas_ativas:
        # Usa vencimento_legal se disponível, senão usa vencimento (prazo operacional)
        data_ref = t.vencimento_legal or t.vencimento
        if data_ref:
            dias_restantes = (data_ref - hoje).days
            t.dias_restantes = dias_restantes
            
            if dias_restantes < 0 or t.status == 'ATRASADO':
                atrasadas.append(t)
            elif dias_restantes <= 5:
                em_risco.append(t)
                
    atrasadas.sort(key=lambda x: x.vencimento_legal or x.vencimento)
    em_risco.sort(key=lambda x: x.vencimento_legal or x.vencimento)
    
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
