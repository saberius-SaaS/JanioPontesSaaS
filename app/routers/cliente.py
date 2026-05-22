from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 25


@router.get("/clientes", response_class=HTMLResponse)
async def list_clientes_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    offset = (page - 1) * PAGE_SIZE
    total = db.query(models.Cliente).count()
    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).offset(offset).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return templates.TemplateResponse("clientes.html", {
        "request": request,
        "clientes": clientes,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "user": current_user
    })


@router.get("/clientes/search", response_class=HTMLResponse)
async def search_clientes(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    query = db.query(models.Cliente)
    if q:
        query = query.filter(
            models.Cliente.cliente.ilike(f"%{q}%")
            | models.Cliente.cnpj.ilike(f"%{q}%")
            | models.Cliente.email.ilike(f"%{q}%")
        )
    clientes = query.order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/clientes_table.html", {"request": request, "clientes": clientes})


@router.post("/clientes", response_class=HTMLResponse)
async def create_cliente(
    request: Request,
    cliente: str = Form(...),
    cnpj: str = Form(None),
    responsavel: str = Form(None),
    email: str = Form(None),
    telefone: str = Form(None),
    regime: str = Form(None),
    nome_fantasia: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    # Validação: CNPJ duplicado
    if cnpj:
        existente = db.query(models.Cliente).filter(models.Cliente.cnpj == cnpj).first()
        if existente:
            clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
            return templates.TemplateResponse("partials/clientes_table.html", {
                "request": request, "clientes": clientes,
                "erro": f"CNPJ {cnpj} já cadastrado para {existente.cliente}"
            })

    novo_cliente = models.Cliente(
        tenant_id=current_user.tenant_id,
        cliente=cliente,
        cnpj=cnpj,
        responsavel=responsavel,
        email=email,
        telefone=telefone,
        regime=regime,
        nome_fantasia=nome_fantasia
    )
    db.add(novo_cliente)
    db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/clientes_table.html", {"request": request, "clientes": clientes})


@router.put("/clientes/{cliente_id}", response_class=HTMLResponse)
async def update_cliente(
    request: Request,
    cliente_id: UUID,
    cliente: str = Form(...),
    cnpj: str = Form(None),
    responsavel: str = Form(None),
    email: str = Form(None),
    telefone: str = Form(None),
    regime: str = Form(None),
    nome_fantasia: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    obj = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not obj:
        return HTMLResponse("<p class='text-red-500'>Cliente não encontrado.</p>", status_code=404)

    obj.cliente = cliente
    obj.cnpj = cnpj
    obj.responsavel = responsavel
    obj.email = email
    obj.telefone = telefone
    obj.regime = regime
    obj.nome_fantasia = nome_fantasia
    obj.status = status
    db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/clientes_table.html", {"request": request, "clientes": clientes})


@router.delete("/clientes/{cliente_id}", response_class=HTMLResponse)
async def delete_cliente(
    request: Request,
    cliente_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    obj = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if obj:
        obj.status = "INATIVO"  # Soft-delete: inativa ao invés de excluir
        db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/clientes_table.html", {"request": request, "clientes": clientes})
