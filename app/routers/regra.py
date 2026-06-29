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

PAGE_SIZE = 1000


@router.get("/obrigacoes", response_class=HTMLResponse)
async def list_obrigacoes_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    offset = (page - 1) * PAGE_SIZE
    total = db.query(models.RegraObrigacao).count()
    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).offset(offset).limit(PAGE_SIZE).all()
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    return templates.TemplateResponse(request, "regras.html", {
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
    current_user: models.Usuario = Depends(require_admin)
):
    query = db.query(models.RegraObrigacao)
    if q:
        query = query.filter(models.RegraObrigacao.obrigacao.ilike(f"%{q}%"))
    obrigacoes = query.order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/regras_table.html", {"obrigacoes": obrigacoes})


@router.post("/obrigacoes", response_class=HTMLResponse)
async def create_obrigacao(
    request: Request,
    obrigacao: str = Form(...),
    dia: str = Form(None),
    departamento: str = Form(None),
    regime: str = Form(None),
    acao: str = Form(None),
    meses: str = Form(None),
    tipos: str = Form(None),
    desloca: int = Form(0),
    vencimento_legal: str = Form(None),
    antecipa_fds: str = Form(None),
    grupo_regra: str = Form(None),
    revisao: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    existente = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.obrigacao == obrigacao).first()
    if existente:
        obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
        return templates.TemplateResponse(request, "partials/regras_table.html", {
            "obrigacoes": obrigacoes,
            "erro": f"Obrigação '{obrigacao}' já cadastrada"
        })

    nova_obrigacao = models.RegraObrigacao(
        tenant_id=current_user.tenant_id,
        obrigacao=obrigacao,
        dia=dia,
        departamento=departamento,
        regime=regime,
        acao=acao,
        meses=meses,
        tipos=tipos,
        desloca=desloca,
        vencimento_legal=vencimento_legal,
        antecipa_fds=antecipa_fds,
        grupo_regra=grupo_regra,
        revisao=revisao,
        status=status
    )
    db.add(nova_obrigacao)
    db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/regras_table.html", {"obrigacoes": obrigacoes})


@router.put("/obrigacoes/{obrigacao_id}", response_class=HTMLResponse)
async def update_obrigacao(
    request: Request,
    obrigacao_id: UUID,
    obrigacao: str = Form(...),
    dia: str = Form(None),
    departamento: str = Form(None),
    regime: str = Form(None),
    acao: str = Form(None),
    meses: str = Form(None),
    tipos: str = Form(None),
    desloca: int = Form(0),
    vencimento_legal: str = Form(None),
    antecipa_fds: str = Form(None),
    grupo_regra: str = Form(None),
    revisao: str = Form(None),
    status: str = Form("ATIVO"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.id == obrigacao_id).first()
    if not obj:
        return HTMLResponse("<p class='text-red-500'>Obrigação não encontrada.</p>", status_code=404)

    obj.obrigacao = obrigacao
    obj.dia = dia
    obj.departamento = departamento
    obj.regime = regime
    obj.acao = acao
    obj.meses = meses
    obj.tipos = tipos
    obj.desloca = desloca
    obj.vencimento_legal = vencimento_legal
    obj.antecipa_fds = antecipa_fds
    obj.grupo_regra = grupo_regra
    obj.revisao = revisao
    obj.status = status
    db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/regras_table.html", {"obrigacoes": obrigacoes})


@router.delete("/obrigacoes/{obrigacao_id}", response_class=HTMLResponse)
async def delete_obrigacao(
    request: Request,
    obrigacao_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    obj = db.query(models.RegraObrigacao).filter(models.RegraObrigacao.id == obrigacao_id).first()
    if obj:
        db.delete(obj)
        db.commit()

    obrigacoes = db.query(models.RegraObrigacao).order_by(models.RegraObrigacao.obrigacao).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/regras_table.html", {"obrigacoes": obrigacoes})
