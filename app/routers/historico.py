from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/historico", response_class=HTMLResponse)
async def list_historico(
    request: Request,
    mes: str = Query(default="", description="Filtro por mes_ano"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    query = db.query(models.HistoricoTarefa).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    )
    if mes:
        query = query.filter(models.HistoricoTarefa.mes_ano == mes)
    
    historicos = query.order_by(models.HistoricoTarefa.vencimento.desc()).limit(300).all()
    
    # Busca meses disponíveis para o filtro
    meses_raw = db.query(models.HistoricoTarefa.mes_ano).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    ).distinct().all()
    meses = sorted(set(m[0] for m in meses_raw if m[0]), reverse=True)

    return templates.TemplateResponse(request=request, name="historico.html", context={
        "request": request,
        "user": current_user,
        "historicos": historicos,
        "meses": meses,
        "mes_selecionado": mes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })
