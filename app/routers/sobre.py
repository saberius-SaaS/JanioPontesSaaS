from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.api.deps import require_login
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/sobre", response_class=HTMLResponse)
async def pagina_sobre(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    # Restringe acesso apenas para ADMIN ou MASTER
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)
        
    return templates.TemplateResponse(request=request, name="sobre.html", context={
        "request": request,
        "user": current_user,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })
