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


@router.get("/obrigacoes", response_class=HTMLResponse)
async def list_obrigacoes_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    offset = (page - 1) * PAGE_SIZE
    total = db.query(models.RegraObrigacao).count()
    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).offset(offset).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return templates.TemplateResponse("regras.html", {
        "request": request,
        "obrigacoes": obrigacoes,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "user": current_user
    })


@router.get("/obrigacoes/search", response_class=HTMLResponse)
async def search_obrigacoes(
    request: Request,
    q: str = "",
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    query = db.query(models.RegraObrigacao)
    if q:
        query = query.filter(models.RegraObrigacao.obrigacao.ilike(f"%{q}%"))
    obrigacoes = query.order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/regras_table.html", {"request": request, "obrigacoes": obrigacoes})


@router.post("/obrigacoes", response_class=HTMLResponse)
async def create_obrigacao(
    request: Request,
    obrigacao: str = Form(...),
    dia: str = Form(None),
    departamento: str = Form(None),
    regime: str = Form(None),
    acao: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    # Validação: nome duplicado
    existente = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.obrigacao == obrigacao).first()
    if existente:
        obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
        return templates.TemplateResponse("partials/regras_table.html", {
            "request": request, "obrigacoes": obrigacoes,
            "erro": f"Obrigação '{obrigacao}' já cadastrada"
        })

    nova_obrigacao = models.RegraObrigacao(
        tenant_id=current_user.tenant_id,
        obrigacao=obrigacao,
        dia=dia,
        departamento=departamento,
        regime=regime,
        acao=acao
    )
    db.add(nova_obrigacao)
    db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/regras_table.html", {"request": request, "obrigacoes": obrigacoes})


@router.put("/obrigacoes/{obrigacao_id}", response_class=HTMLResponse)
async def update_obrigacao(
    request: Request,
    obrigacao_id: UUID,
    obrigacao: str = Form(...),
    dia: str = Form(None),
    departamento: str = Form(None),
    regime: str = Form(None),
    acao: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    obj = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.id == obrigacao_id).first()
    if not obj:
        return HTMLResponse("<p class='text-red-500'>Obrigação não encontrada.</p>", status_code=404)

    obj.obrigacao = obrigacao
    obj.dia = dia
    obj.departamento = departamento
    obj.regime = regime
    obj.acao = acao
    db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/regras_table.html", {"request": request, "obrigacoes": obrigacoes})


@router.delete("/obrigacoes/{obrigacao_id}", response_class=HTMLResponse)
async def delete_obrigacao(
    request: Request,
    obrigacao_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    obj = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.id == obrigacao_id).first()
    if obj:
        db.delete(obj)
        db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse("partials/regras_table.html", {"request": request, "obrigacoes": obrigacoes})
