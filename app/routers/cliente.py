from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import datetime

from app import models
from app.database import get_db
from app.api.deps import require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

PAGE_SIZE = 1000


@router.get("/clientes", response_class=HTMLResponse)
async def list_clientes_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    offset = (page - 1) * PAGE_SIZE
    total = db.query(models.Cliente).count()
    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).offset(offset).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    perfis = db.query(models.Perfil).filter(models.Perfil.status == "ATIVO").order_by(models.Perfil.nome).all()

    return templates.TemplateResponse(request, "clientes.html", {
        "clientes": clientes,
        "perfis": perfis,
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
    current_user: models.Usuario = Depends(require_admin)
):
    query = db.query(models.Cliente)
    if q:
        query = query.filter(
            models.Cliente.cliente.ilike(f"%{q}%")
            | models.Cliente.cnpj.ilike(f"%{q}%")
            | models.Cliente.email.ilike(f"%{q}%")
        )
    clientes = query.order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/clientes_table.html", {"clientes": clientes})


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
    fiscal: str = Form(None),
    contabil: str = Form(None),
    pessoal: str = Form(None),
    societario: str = Form(None),
    excecoes: str = Form(None),
    pasta_drive: str = Form(None),
    nivel: int = Form(1),
    perfis_ativos: List[str] = Form(default=[]),
    email_fiscal: str = Form(None),
    email_contabil: str = Form(None),
    email_pessoal: str = Form(None),
    email_societario: str = Form(None),
    data_entrada: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    if cnpj:
        existente = db.query(models.Cliente).filter(models.Cliente.cnpj == cnpj).first()
        if existente:
            clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
            return templates.TemplateResponse(request, "partials/clientes_table.html", {
                "clientes": clientes,
                "erro": f"CNPJ {cnpj} já cadastrado para {existente.cliente}"
            })

    # Parse data_entrada: se não informada, usa a data de hoje
    dt_entrada = datetime.date.today()
    if data_entrada:
        try:
            dt_entrada = datetime.datetime.strptime(data_entrada, '%Y-%m-%d').date()
        except ValueError:
            pass

    novo_cliente = models.Cliente(
        tenant_id=current_user.tenant_id,
        cliente=cliente,
        cnpj=cnpj,
        responsavel=responsavel,
        email=email,
        telefone=telefone,
        regime=regime,
        nome_fantasia=nome_fantasia,
        fiscal=fiscal,
        contabil=contabil,
        pessoal=pessoal,
        societario=societario,
        excecoes=excecoes,
        pasta_drive=pasta_drive,
        nivel=nivel,
        perfis_ativos=", ".join(perfis_ativos) if perfis_ativos else "",
        email_fiscal=email_fiscal,
        email_contabil=email_contabil,
        email_pessoal=email_pessoal,
        email_societario=email_societario,
        data_entrada=dt_entrada
    )
    db.add(novo_cliente)
    db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/clientes_table.html", {"clientes": clientes})


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
    fiscal: str = Form(None),
    contabil: str = Form(None),
    pessoal: str = Form(None),
    societario: str = Form(None),
    excecoes: str = Form(None),
    pasta_drive: str = Form(None),
    nivel: int = Form(1),
    perfis_ativos: List[str] = Form(default=[]),
    email_fiscal: str = Form(None),
    email_contabil: str = Form(None),
    email_pessoal: str = Form(None),
    email_societario: str = Form(None),
    data_entrada: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
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
    obj.fiscal = fiscal
    obj.contabil = contabil
    obj.pessoal = pessoal
    obj.societario = societario
    obj.excecoes = excecoes
    obj.pasta_drive = pasta_drive
    obj.nivel = nivel
    obj.perfis_ativos = ", ".join(perfis_ativos) if perfis_ativos else ""
    obj.email_fiscal = email_fiscal
    obj.email_contabil = email_contabil
    obj.email_pessoal = email_pessoal
    obj.email_societario = email_societario
    obj.status = status
    if data_entrada:
        try:
            obj.data_entrada = datetime.datetime.strptime(data_entrada, '%Y-%m-%d').date()
        except ValueError:
            pass
    db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/clientes_table.html", {"clientes": clientes})


@router.delete("/clientes/{cliente_id}", response_class=HTMLResponse)
async def delete_cliente(
    request: Request,
    cliente_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if obj:
        obj.status = "INATIVO"
        db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/clientes_table.html", {"clientes": clientes})
