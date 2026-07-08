from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
import datetime
import secrets
import string
import json
import re

from app import models
from app.database import get_db
from app.api.deps import require_admin
from app.core.timezone import agora_br

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
    equipes = db.query(models.Equipe).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).order_by(models.Equipe.departamento, models.Equipe.nome).all()

    obrigacoes = db.query(models.RegraObrigacao.obrigacao).filter(
        models.RegraObrigacao.tenant_id == current_user.tenant_id,
        models.RegraObrigacao.status == 'ATIVO'
    ).distinct().order_by(models.RegraObrigacao.obrigacao).all()
    lista_obrigacoes = [o[0] for o in obrigacoes if o[0]]

    return templates.TemplateResponse(request, "clientes.html", {
        "clientes": clientes,
        "perfis": perfis,
        "equipes": equipes,
        "obrigacoes": lista_obrigacoes,
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
        termos = [t.strip() for t in q.split() if t.strip()]
        for termo in termos:
            search_term = f"%{termo}%"
            query = query.filter(
                models.Cliente.cliente.ilike(search_term)
                | models.Cliente.cnpj.ilike(search_term)
                | models.Cliente.email.ilike(search_term)
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
    regras_roteamento: str = Form(None),
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
        regras_roteamento=regras_roteamento,
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
    regras_roteamento: str = Form(None),
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
    obj.regras_roteamento = regras_roteamento
    obj.status = status
    if status == "INATIVO":
        db.query(models.Tarefa).filter(
            models.Tarefa.cliente == obj.cliente,
            models.Tarefa.tenant_id == current_user.tenant_id,
            models.Tarefa.status != 'ENTREGUE'
        ).delete(synchronize_session=False)

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
        db.query(models.Tarefa).filter(
            models.Tarefa.cliente == obj.cliente,
            models.Tarefa.tenant_id == current_user.tenant_id,
            models.Tarefa.status != 'ENTREGUE'
        ).delete(synchronize_session=False)
        db.commit()

    clientes = db.query(models.Cliente).order_by(models.Cliente.cliente).limit(PAGE_SIZE).all()
    return templates.TemplateResponse(request, "partials/clientes_table.html", {"clientes": clientes})

def gerar_chave_aleatoria() -> str:
    alphabet = string.ascii_uppercase + string.digits
    confusing = ['O', '0', 'I', '1']
    clean_alphabet = [c for c in alphabet if c not in confusing]
    key_chars = [secrets.choice(clean_alphabet) for _ in range(6)]
    return f"JP-{''.join(key_chars)}"

@router.post("/api/clientes/{cliente_id}/gerar-chave-portal")
async def gerar_chave_portal(
    cliente_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_admin)
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    chave_pura = gerar_chave_aleatoria()
    
    from app.core.security import get_password_hash
    hash_chave = get_password_hash(chave_pura)

    cliente.chave_portal_hash = hash_chave
    cliente.chave_portal_gerada_em = agora_br()
    db.commit()

    emails_dest = set()
    campos_email = ["email", "email_fiscal", "email_contabil", "email_pessoal", "email_societario"]
    for campo in campos_email:
        val = getattr(cliente, campo, None)
        if val:
            for part in re.split(r'[;,]', val):
                p_clean = part.strip().lower()
                if p_clean and "@" in p_clean:
                    emails_dest.add(p_clean)

    if cliente.regras_roteamento:
        try:
            regras = json.loads(cliente.regras_roteamento)
            if isinstance(regras, dict):
                for val in regras.values():
                    if isinstance(val, str) and val.strip():
                        for part in re.split(r'[;,]', val):
                            p_clean = part.strip().lower()
                            if p_clean and "@" in p_clean:
                                emails_dest.add(p_clean)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Erro ao parsear regras_roteamento no cliente {cliente.id}: {e}")

    from app.core.email_service import email_service
    enviados_com_sucesso = []
    
    assunto = f"Chave de Acesso ao Portal do Cliente - {cliente.cliente}"
    corpo_html = f"""
    <div style="font-family: 'Inter', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 24px; border-bottom: 1px solid #f1f5f9; padding-bottom: 16px;">
            <h2 style="color: #1C3051; margin: 0; font-size: 22px;">Janio Pontes Contabilidade</h2>
            <p style="color: #64748b; margin: 4px 0 0 0; font-size: 14px;">Portal do Cliente</p>
        </div>
        <div style="color: #334155; font-size: 15px; line-height: 1.6;">
            <p>Prezado(a) Cliente <strong>{cliente.cliente}</strong>,</p>
            <p>Essa é a sua chave de Acesso ao <strong>Portal do Cliente</strong>.</p>
            
            <div style="text-align: center; margin: 32px 0; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 6px; padding: 20px;">
                <span style="font-family: monospace; font-size: 28px; font-weight: bold; letter-spacing: 2px; color: #1C3051; display: block; margin-bottom: 8px;">{chave_pura}</span>
                <span style="font-size: 13px; color: #64748b;">(Respeite letras maiusculas e o traco)</span>
            </div>
            
            <p>Para acessar o portal e consultar seus documentos, guias, guias de impostos e solicitacoes, siga o link abaixo:</p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="https://app.janiopontes.com.br/portal/login" style="display: inline-block; background-color: #1C3051; color: #ffffff; text-decoration: none; padding: 12px 28px; font-weight: 600; border-radius: 6px; font-size: 15px;">Acessar Portal do Cliente</a>
            </div>
            
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin: 24px 0;">
            <p style="font-size: 13px; color: #64748b; margin-bottom: 0;">
                Este e-mail e automatico. Sempre que precisar gerar nova chave, por favor entre em contato com nosso whatsapp.
            </p>
        </div>
    </div>
    """
    
    for email in sorted(list(emails_dest)):
        ok = await email_service.enviar_email(para=email, assunto=assunto, corpo_html=corpo_html)
        if ok:
            enviados_com_sucesso.append(email)

    return {
        "ok": True,
        "chave": chave_pura,
        "destinatarios": enviados_com_sucesso,
        "total_destinatarios": len(emails_dest)
    }
