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

@router.get("/perfis", response_class=HTMLResponse)
async def list_perfis_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    perfis = db.query(models.Perfil).order_by(models.Perfil.nome).all()
    return templates.TemplateResponse(request, "perfis.html", {
        "perfis": perfis,
        "user": current_user
    })

@router.post("/perfis", response_class=HTMLResponse)
async def create_perfil(
    request: Request,
    nome: str = Form(...),
    descricao: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    novo_perfil = models.Perfil(
        tenant_id=current_user.tenant_id,
        nome=nome,
        descricao=descricao,
        status=status
    )
    db.add(novo_perfil)
    db.commit()

    perfis = db.query(models.Perfil).order_by(models.Perfil.nome).all()
    return templates.TemplateResponse(request, "partials/perfis_table.html", {"perfis": perfis})

@router.put("/perfis/{perfil_id}", response_class=HTMLResponse)
async def update_perfil(
    request: Request,
    perfil_id: UUID,
    nome: str = Form(...),
    descricao: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.Perfil).filter(models.Perfil.id == perfil_id).first()
    if not obj:
        return HTMLResponse("<p class='text-red-500'>Perfil não encontrado.</p>", status_code=404)

    obj.nome = nome
    obj.descricao = descricao
    obj.status = status
    db.commit()

    perfis = db.query(models.Perfil).order_by(models.Perfil.nome).all()
    return templates.TemplateResponse(request, "partials/perfis_table.html", {"perfis": perfis})

@router.delete("/perfis/{perfil_id}", response_class=HTMLResponse)
async def delete_perfil(
    request: Request,
    perfil_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.Perfil).filter(models.Perfil.id == perfil_id).first()
    if obj:
        obj.status = "INATIVO"
        db.commit()

    perfis = db.query(models.Perfil).order_by(models.Perfil.nome).all()
    return templates.TemplateResponse(request, "partials/perfis_table.html", {"perfis": perfis})
