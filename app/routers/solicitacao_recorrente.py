from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import require_login
from app.models import Usuario, SolicitacaoRecorrente, Cliente, Equipe
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gestao/solicitacoes-recorrentes")
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def list_recorrentes(request: Request, db: Session = Depends(get_db), current_user: Usuario = Depends(require_login)):
    regras = db.query(SolicitacaoRecorrente).filter(
        SolicitacaoRecorrente.tenant_id == current_user.tenant_id
    ).order_by(SolicitacaoRecorrente.cliente_nome).all()
    
    clientes = db.query(Cliente).filter(
        Cliente.tenant_id == current_user.tenant_id,
        Cliente.status == "ATIVO"
    ).order_by(Cliente.cliente).all()
    
    departamentos_db = db.query(Equipe.departamento).filter(
        Equipe.tenant_id == current_user.tenant_id
    ).distinct().order_by(Equipe.departamento).all()
    departamentos = [d[0] for d in departamentos_db if d[0]]
    
    return templates.TemplateResponse(request, "solicitacao_recorrente/lista.html", {
        "regras": regras,
        "clientes": clientes,
        "departamentos": departamentos,
        "user": current_user
    })

@router.post("/salvar")
async def save_recorrente(
    id: str = Form(None),
    cliente_id: str = Form(...),
    departamento: str = Form(...),
    responsavel: str = Form(...),
    email_override: str = Form(""),
    titulo_template: str = Form(...),
    descricao_template: str = Form(...),
    dia_geracao: int = Form(...),
    ativo: str = Form("true"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_login)
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id, Cliente.tenant_id == current_user.tenant_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
    is_ativo = ativo.lower() == "true" or ativo == "on"
    
    if id:
        regra = db.query(SolicitacaoRecorrente).filter(SolicitacaoRecorrente.id == id, SolicitacaoRecorrente.tenant_id == current_user.tenant_id).first()
        if regra:
            regra.cliente_id = cliente.id
            regra.cliente_nome = cliente.cliente
            regra.departamento = departamento
            regra.responsavel = responsavel
            regra.email_override = email_override if email_override.strip() else None
            regra.titulo_template = titulo_template
            regra.descricao_template = descricao_template
            regra.dia_geracao = dia_geracao
            regra.ativo = is_ativo
    else:
        nova_regra = SolicitacaoRecorrente(
            tenant_id=current_user.tenant_id,
            cliente_id=cliente.id,
            cliente_nome=cliente.cliente,
            departamento=departamento,
            responsavel=responsavel,
            email_override=email_override if email_override.strip() else None,
            titulo_template=titulo_template,
            descricao_template=descricao_template,
            dia_geracao=dia_geracao,
            ativo=is_ativo
        )
        db.add(nova_regra)
        
    db.commit()
    return RedirectResponse(url="/gestao/solicitacoes-recorrentes", status_code=303)

@router.post("/deletar/{id}")
async def delete_recorrente(id: str, db: Session = Depends(get_db), current_user: Usuario = Depends(require_login)):
    regra = db.query(SolicitacaoRecorrente).filter(SolicitacaoRecorrente.id == id, SolicitacaoRecorrente.tenant_id == current_user.tenant_id).first()
    if regra:
        db.delete(regra)
        db.commit()
    return RedirectResponse(url="/gestao/solicitacoes-recorrentes", status_code=303)
