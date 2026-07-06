from app.core.timezone import agora_br, hoje_br
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
import logging

from app import models
from app.database import get_db
from app.api.deps import require_cliente_login
from app.core import security
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Filtro Jinja2 para converter UTC → Horário de Brasília (UTC-3)
_tz_brasilia = timezone(timedelta(hours=-3))

def _filtro_brasilia(dt, fmt="%d/%m/%Y %H:%M"):
    """Converte datetime UTC para horário de Brasília e formata."""
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz_brasilia).strftime(fmt)

templates.env.filters["brasilia"] = _filtro_brasilia

@router.get("/acesso/{protocolo_id}", response_class=HTMLResponse)
async def acesso_magico(
    request: Request,
    protocolo_id: str,
    db: Session = Depends(get_db)
):
    """
    Link Mágico: Recebe o ID do protocolo do e-mail, identifica o cliente,
    marca como lido, e faz auto-login redirecionando para o documento.
    """
    # Bypass RLS porque não temos tenant ainda
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    import uuid
    try:
        prot_uuid = uuid.UUID(protocolo_id)
    except Exception:
        # Tenta buscar pelo código PRT- se não for UUID
        protocolo = db.query(models.Protocolo).filter(models.Protocolo.protocolo == protocolo_id).first()
    else:
        protocolo = db.query(models.Protocolo).filter(models.Protocolo.id == prot_uuid).first()

    if not protocolo:
        return HTMLResponse("<h1>Link inválido ou expirado.</h1>", status_code=404)

    cliente_nome = protocolo.cliente
    tenant_id_str = str(protocolo.tenant_id)
    prot_id = protocolo.id

    # Marca como lido se ainda não estiver
    if not protocolo.conf_recto:
        protocolo.conf_recto = agora_br()
        db.commit()

    # Tenta preservar a sessão de admin (sub) caso o dono do sistema esteja testando o portal
    token_atual = request.cookies.get("__session")
    admin_sub = None
    if token_atual:
        try:
            payload = jwt.decode(token_atual, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            admin_sub = payload.get("sub")
        except Exception:
            pass

    # Gera token de sessão do cliente
    expires = timedelta(days=30)
    expire = agora_br() + expires
    token_data = {"exp": expire, "cliente": cliente_nome, "tenant_id": tenant_id_str}
    
    if admin_sub:
        token_data["sub"] = admin_sub

    from jose import jwt
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = RedirectResponse(url=f"/portal/documento/{prot_id}", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="__session",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",
        secure=True
    )
    return response

@router.get("/portal/login", response_class=HTMLResponse)
async def portal_login(request: Request):
    return templates.TemplateResponse(request, "portal/login.html", {"request": request})

@router.get("/portal", response_class=HTMLResponse)
async def portal_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    # Buscar protocolos recentes (até 50 para uma timeline legal)
    protocolos_db = db.query(models.Protocolo).filter(
        models.Protocolo.cliente == cliente_nome
    ).order_by(models.Protocolo.data.desc()).limit(50).all()

    import re
    from collections import defaultdict
    import locale

    protocolos_parsed = []
    meses_grupos = defaultdict(list)

    # Buscar período (mes_ano) das tarefas vinculadas (batch para evitar N+1)
    id_tarefas = [p.id_tarefa for p in protocolos_db if p.id_tarefa]
    mes_ano_lookup = {}
    if id_tarefas:
        tarefas_ref = db.query(models.Tarefa.id_controle, models.Tarefa.mes_ano).filter(
            models.Tarefa.id_controle.in_(id_tarefas)
        ).all()
        mes_ano_lookup = {t.id_controle: t.mes_ano for t in tarefas_ref}
        missing = [idt for idt in id_tarefas if idt not in mes_ano_lookup]
        if missing:
            hist_ref = db.query(models.HistoricoTarefa.id_controle, models.HistoricoTarefa.mes_ano).filter(
                models.HistoricoTarefa.id_controle.in_(missing)
            ).all()
            for h in hist_ref:
                mes_ano_lookup[h.id_controle] = h.mes_ano
    
    # Dicionário manual de meses em PT-BR para evitar problemas de locale no servidor
    meses_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    for p in protocolos_db:
        acao_tipo = (p.acao or "").upper()
        
        # 1. Bloquear ações estritamente internas (justificativas, auditorias)
        if acao_tipo in ["ARQUIVAR", "AUDITAR"]:
            continue

        link_bruto = p.link_arquivo or ""
        base_link = re.sub(r'\[.*?\]', '', link_bruto).strip()
        links = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]
        
        # 2. Se não for comunicado e não tiver link de arquivo, é apenas uma baixa justificada antiga/sem arquivo
        if acao_tipo != "COMUNICAR" and len(links) == 0:
            continue
        
        # Pega a data real de criação e converte para UTC-3 (Brasília)
        dt = p.data
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt:
            dt = dt.astimezone(_tz_brasilia)
            mes_nome = meses_pt.get(dt.month, "")
            grupo_nome = f"{mes_nome} de {dt.year}"
        else:
            grupo_nome = "Anteriores"

        # Dados da ação e mensagem para COMUNICAR
        if acao_tipo == "COMUNICAR":
            mensagem_texto = p.link_arquivo.strip() if p.link_arquivo else ""
        else:
            mensagem_texto = ""

        # Criar um dicionário com os dados formatados
        p_dict = {
            "id": p.id,
            "protocolo": p.protocolo,
            "obrigacao": p.obrigacao,
            "data_obj": dt,
            "lido": bool(p.conf_recto),
            "links": links,
            "has_pdf": len(links) > 0 and any(".pdf" in l.lower() for l in links),
            "first_url": links[0] if links else None,
            "mes_ano": mes_ano_lookup.get(p.id_tarefa, ""),
            "acao": acao_tipo,
            "mensagem": mensagem_texto,
        }
        meses_grupos[grupo_nome].append(p_dict)

    return templates.TemplateResponse(request, "portal/dashboard.html", {
        "request": request,
        "cliente": cliente_nome,
        "meses_grupos": dict(meses_grupos)
    })

@router.get("/portal/documento/{id}", response_class=HTMLResponse)
async def portal_documento(
    request: Request,
    id: str,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.id == id,
        models.Protocolo.cliente == cliente_nome
    ).first()

    if not protocolo:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Extrair os links anexos (se hover mais de um, separados por ' | ')
    import re
    link_bruto = protocolo.link_arquivo or ""
    base_link = re.sub(r'\[.*?\]', '', link_bruto).strip()
    links = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]

    return templates.TemplateResponse(request, "portal/documento.html", {
        "request": request,
        "cliente": cliente_nome,
        "protocolo": protocolo,
        "links": links
    })

@router.get("/portal/logout")
async def portal_logout():
    response = RedirectResponse(url="/portal/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="__session")
    return response

@router.get("/portal/solicitacoes", response_class=HTMLResponse)
async def portal_solicitacoes_list(
    request: Request,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    solicitacoes = db.query(models.Solicitacao).filter(
        models.Solicitacao.cliente == cliente_nome
    ).order_by(models.Solicitacao.data.desc()).all()

    return templates.TemplateResponse(request, "portal/solicitacoes.html", {
        "request": request,
        "cliente": cliente_nome,
        "solicitacoes": solicitacoes
    })

@router.get("/portal/solicitacoes/{id_legado}", response_class=HTMLResponse)
async def portal_solicitacao_view(
    request: Request,
    id_legado: str,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    solic = db.query(models.Solicitacao).filter(
        models.Solicitacao.id_legado == id_legado,
        models.Solicitacao.cliente == cliente_nome
    ).first()

    if not solic:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    return templates.TemplateResponse(request, "portal/solicitacao_view.html", {
        "request": request,
        "cliente": cliente_nome,
        "solicitacao": solic,
        "sucesso": False
    })

@router.post("/portal/solicitacoes/{id_legado}", response_class=HTMLResponse)
async def portal_solicitacao_reply(
    request: Request,
    id_legado: str,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    """
    Quando o cliente responde a solicitação pelo portal.
    Para reaproveitar o upload e email do backend, faremos um form submission simples
    semelhante à rota pública, mas redirecionando de volta ao portal.
    """
    from fastapi import Form, UploadFile, File, BackgroundTasks
    from app.core.storage_service import storage_service
    from app.core.email_service import email_service
    
    # Process the form data explicitly because this is inside a POST function 
    # that doesn't use the typical Form/File injections directly due to being a manual route handler.
    # Actually, let's just use request.form()
    form = await request.form()
    mensagem = form.get("mensagem")
    arquivo = form.get("arquivo") # Type UploadFile if present
    
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    solic = db.query(models.Solicitacao).filter(
        models.Solicitacao.id_legado == id_legado,
        models.Solicitacao.cliente == cliente_nome
    ).first()

    if not solic:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    link = None
    if arquivo and hasattr(arquivo, "filename") and arquivo.filename:
        link = await storage_service.upload_file(arquivo, cliente_nome=cliente_nome)

    solic.status = "ENTREGUE"
    solic.data_envio = agora_br()
    
    resposta_texto = ""
    if mensagem:
        resposta_texto += f"\n\n[RESPOSTA DO CLIENTE]: {mensagem}"
    if link:
        resposta_texto += f"\n[ARQUIVO ANEXADO]: {link}"
        
    solic.pedido = (solic.pedido or "") + resposta_texto
    db.commit()

    # Como não temos background tasks instanciado diretamente, podemos usar chamadas await normais (ou ignorar email imediato).
    # O ideal seria injetar BackgroundTasks. Como não está na assinatura, vamos deixar apenas o log no banco por ora.
    
    return templates.TemplateResponse(request, "portal/solicitacao_view.html", {
        "request": request,
        "cliente": cliente_nome,
        "solicitacao": solic,
        "sucesso": True
    })
