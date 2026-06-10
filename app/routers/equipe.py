from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID

from app import models
from app.database import get_db
from app.api.deps import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/equipes", response_class=HTMLResponse)
async def list_equipes_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()
    
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.tenant_id == current_user.tenant_id,
        models.Usuario.ativo == True
    ).order_by(models.Usuario.nome).all()

    return templates.TemplateResponse(request, "equipes.html", {
        "equipes": equipes,
        "usuarios": usuarios,
        "user": current_user
    })

@router.post("/equipes", response_class=HTMLResponse)
async def create_equipe(
    request: Request,
    nome: str = Form(...),
    departamento: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    nova_equipe = models.Equipe(
        tenant_id=current_user.tenant_id,
        nome=nome,
        departamento=departamento
    )
    db.add(nova_equipe)
    db.commit()

    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()
    
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.tenant_id == current_user.tenant_id,
        models.Usuario.ativo == True
    ).order_by(models.Usuario.nome).all()

    return templates.TemplateResponse(request, "partials/equipes_table.html", {"equipes": equipes, "usuarios": usuarios})

@router.post("/equipes/{equipe_id}/membros", response_class=HTMLResponse)
async def add_membro(
    request: Request,
    equipe_id: str,
    usuario_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    existente = db.query(models.UsuarioEquipe).filter(
        models.UsuarioEquipe.equipe_id == equipe_id,
        models.UsuarioEquipe.usuario_id == usuario_id
    ).first()
    
    if not existente:
        novo_membro = models.UsuarioEquipe(
            tenant_id=current_user.tenant_id,
            equipe_id=equipe_id,
            usuario_id=usuario_id
        )
        db.add(novo_membro)
        db.commit()

    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()
    
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.tenant_id == current_user.tenant_id,
        models.Usuario.ativo == True
    ).order_by(models.Usuario.nome).all()

    return templates.TemplateResponse(request, "partials/equipes_table.html", {"equipes": equipes, "usuarios": usuarios})

@router.delete("/equipes/{equipe_id}/membros/{usuario_id}", response_class=HTMLResponse)
async def remove_membro(
    request: Request,
    equipe_id: str,
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    membro = db.query(models.UsuarioEquipe).filter(
        models.UsuarioEquipe.equipe_id == equipe_id,
        models.UsuarioEquipe.usuario_id == usuario_id,
        models.UsuarioEquipe.tenant_id == current_user.tenant_id
    ).first()
    
    if membro:
        db.delete(membro)
        db.commit()

    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()
    
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.tenant_id == current_user.tenant_id,
        models.Usuario.ativo == True
    ).order_by(models.Usuario.nome).all()

    return templates.TemplateResponse(request, "partials/equipes_table.html", {"equipes": equipes, "usuarios": usuarios})

@router.delete("/equipes/{equipe_id}", response_class=HTMLResponse)
async def delete_equipe(
    request: Request,
    equipe_id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    equipe = db.query(models.Equipe).filter(
        models.Equipe.id == equipe_id,
        models.Equipe.tenant_id == current_user.tenant_id
    ).first()
    
    if equipe:
        db.delete(equipe)
        db.commit()

    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()
    
    usuarios = db.query(models.Usuario).filter(
        models.Usuario.tenant_id == current_user.tenant_id,
        models.Usuario.ativo == True
    ).order_by(models.Usuario.nome).all()

    return templates.TemplateResponse(request, "partials/equipes_table.html", {"equipes": equipes, "usuarios": usuarios})
