from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID

from app import models
from app.database import get_db
from app.api.deps import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/usuarios", response_class=HTMLResponse)
async def list_usuarios_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    usuarios = db.query(models.Usuario).order_by(models.Usuario.nome).all()
    return templates.TemplateResponse(request, "usuarios.html", {
        "usuarios": usuarios,
        "user": current_user
    })

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
