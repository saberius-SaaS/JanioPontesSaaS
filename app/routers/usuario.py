from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID

from app import models
from app.database import get_db
from app.api.deps import require_admin, require_login
from datetime import date, datetime, timedelta
from sqlalchemy import func

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/usuarios", response_class=HTMLResponse)
async def list_usuarios_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    usuarios = db.query(models.Usuario).order_by(models.Usuario.nome).all()
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)

    telemetria_hoje = db.query(models.FrequenciaAcesso).filter(
        models.FrequenciaAcesso.tenant_id == current_user.tenant_id,
        models.FrequenciaAcesso.data == hoje
    ).all()
    map_hoje = {t.email: t.tempo_minutos for t in telemetria_hoje}

    telemetria_mes = db.query(
        models.FrequenciaAcesso.email,
        func.sum(models.FrequenciaAcesso.tempo_minutos).label('total_minutos')
    ).filter(
        models.FrequenciaAcesso.tenant_id == current_user.tenant_id,
        models.FrequenciaAcesso.data >= inicio_mes
    ).group_by(models.FrequenciaAcesso.email).all()
    map_mes = {t.email: t.total_minutos for t in telemetria_mes}

    from datetime import timezone
    agora = datetime.now(timezone.utc)
    limite_online = agora - timedelta(seconds=90)
    online_freqs = db.query(models.FrequenciaAcesso.email).filter(
        models.FrequenciaAcesso.tenant_id == current_user.tenant_id,
        models.FrequenciaAcesso.data == hoje,
        models.FrequenciaAcesso.atualizado_em >= limite_online
    ).all()
    online_set = {f.email for f in online_freqs}

    return templates.TemplateResponse(request, "usuarios.html", {
        "usuarios": usuarios,
        "map_hoje": map_hoje,
        "map_mes": map_mes,
        "online_set": online_set,
        "user": current_user
    })

@router.post("/telemetria/ping")
async def register_ping(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    from datetime import date as d_date
    hoje = d_date.today()
    freq = db.query(models.FrequenciaAcesso).filter(
        models.FrequenciaAcesso.tenant_id == current_user.tenant_id,
        models.FrequenciaAcesso.email == current_user.email,
        models.FrequenciaAcesso.data == hoje
    ).first()
    
    if not freq:
        freq = models.FrequenciaAcesso(
            tenant_id=current_user.tenant_id,
            data=hoje,
            email=current_user.email,
            nome=current_user.nome,
            tempo_minutos=1,
            pings=1
        )
        db.add(freq)
    else:
        freq.tempo_minutos += 1
        freq.pings += 1
    
    db.commit()
    return {"status": "ok"}

@router.post("/usuarios", response_class=HTMLResponse)
async def create_usuario(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    nivel: str = Form("USER"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    existente = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if existente:
        usuarios = db.query(models.Usuario).order_by(models.Usuario.nome).all()
        return templates.TemplateResponse(request, "partials/usuarios_table.html", {
            "usuarios": usuarios,
            "erro": f"E-mail {email} já cadastrado"
        })

    novo_usuario = models.Usuario(
        tenant_id=current_user.tenant_id,
        nome=nome,
        email=email,
        nivel=nivel,
        ativo=True
    )
    db.add(novo_usuario)
    db.commit()

    usuarios = db.query(models.Usuario).order_by(models.Usuario.nome).all()
    return templates.TemplateResponse(request, "partials/usuarios_table.html", {"usuarios": usuarios})

@router.put("/usuarios/{usuario_id}", response_class=HTMLResponse)
async def update_usuario(
    request: Request,
    usuario_id: UUID,
    nome: str = Form(...),
    email: str = Form(...),
    nivel: str = Form("USER"),
    ativo: str = Form("True"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not obj:
        return HTMLResponse("<p class='text-red-500'>Usuário não encontrado.</p>", status_code=404)

    obj.nome = nome
    obj.email = email
    obj.nivel = nivel
    obj.ativo = ativo.lower() == "true"
    db.commit()

    usuarios = db.query(models.Usuario).order_by(models.Usuario.nome).all()
    return templates.TemplateResponse(request, "partials/usuarios_table.html", {"usuarios": usuarios})
