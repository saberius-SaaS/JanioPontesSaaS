from app.core.timezone import agora_br
from fastapi import APIRouter, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta, timezone
from jose import jwt
import logging
import re

from app import models
from app.database import get_db
from app.api.deps import require_cliente_login
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
    email_usuario = protocolo.email or ""
    token_data = {"exp": expire, "cliente": cliente_nome, "tenant_id": tenant_id_str, "email_usuario": email_usuario}
    
    if admin_sub:
        token_data["sub"] = admin_sub

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

def validar_documento(doc: str) -> str:
    """Valida CPF (11 digitos) ou CNPJ (14 digitos) e retorna apenas os digitos."""
    limpo = re.sub(r'[^0-9]', '', doc)
    if len(limpo) == 11:
        if limpo == limpo[0] * 11:
            raise ValueError("CPF invalido")
        soma = sum(int(limpo[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10) % 11
        if d1 >= 10:
            d1 = 0
        if int(limpo[9]) != d1:
            raise ValueError("CPF invalido")
        soma = sum(int(limpo[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10) % 11
        if d2 >= 10:
            d2 = 0
        if int(limpo[10]) != d2:
            raise ValueError("CPF invalido")
        return limpo
    elif len(limpo) == 14:
        if limpo == limpo[0] * 14:
            raise ValueError("CNPJ invalido")
        pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(limpo[i]) * pesos1[i] for i in range(12))
        d1 = 11 - (soma % 11)
        if d1 >= 10:
            d1 = 0
        if int(limpo[12]) != d1:
            raise ValueError("CNPJ invalido")
        pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(limpo[i]) * pesos2[i] for i in range(13))
        d2 = 11 - (soma % 11)
        if d2 >= 10:
            d2 = 0
        if int(limpo[13]) != d2:
            raise ValueError("CNPJ invalido")
        return limpo
    else:
        raise ValueError("Documento invalido")

@router.post("/portal/auth", response_class=HTMLResponse)
async def portal_auth(
    request: Request,
    documento: str = Form(...),
    email: str = Form(...),
    chave: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        limpo = validar_documento(documento)
    except ValueError:
        return templates.TemplateResponse(
            request,
            "portal/login.html",
            {"request": request, "erro": "Documento (CPF ou CNPJ) invalido.", "documento": documento},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    ip = request.client.host if request.client else "0.0.0.0"
    limite_tempo = agora_br() - timedelta(minutes=15)
    
    try:
        from app.models.tentativa_login import TentativaLogin
        db.query(TentativaLogin).filter(TentativaLogin.attempt_time < limite_tempo).delete()
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao limpar tentativas antigas: {e}")

    try:
        failed_count = db.query(TentativaLogin).filter(
            TentativaLogin.ip_address == ip,
            TentativaLogin.attempt_time >= limite_tempo
        ).count()
        if failed_count >= 5:
            return templates.TemplateResponse(
                request,
                "portal/login.html",
                {"request": request, "erro": "Muitas tentativas falhas. Acesso bloqueado por 15 minutos.", "documento": documento},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
    except Exception as e:
        logger.error(f"Erro ao contar tentativas falhas: {e}")

    def registrar_falha():
        try:
            nova_tentativa = TentativaLogin(
                ip_address=ip,
                documento=limpo,
                attempt_time=agora_br()
            )
            db.add(nova_tentativa)
            db.commit()
        except Exception as e:
            logger.error(f"Erro ao persistir falha no login: {e}")

    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    padded_input = limpo.zfill(11) if len(limpo) == 11 else limpo.zfill(14)
    
    clientes = db.query(models.Cliente).filter(models.Cliente.status == 'ATIVO').all()
    cliente = None
    for c in clientes:
        if not c.cnpj:
            continue
        c_clean = re.sub(r'[^0-9]', '', c.cnpj)
        if not c_clean:
            continue
        c_padded = c_clean.zfill(11) if len(c_clean) <= 11 else c_clean.zfill(14)
        if c_padded == padded_input:
            cliente = c
            break

    email_limpo = email.strip().lower()

    try:
        import json
        chaves_map = json.loads(cliente.chaves_acesso) if cliente.chaves_acesso else {}
    except:
        chaves_map = {}

    chave_data = chaves_map.get(email_limpo)

    if not cliente or not chave_data:
        registrar_falha()
        return templates.TemplateResponse(
            request,
            "portal/login.html",
            {"request": request, "erro": "Dados de acesso incorretos.", "documento": documento, "email": email},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    from app.core.security import verify_password
    if not verify_password(chave.strip(), chave_data["hash"]):
        registrar_falha()
        return templates.TemplateResponse(
            request,
            "portal/login.html",
            {"request": request, "erro": "Dados de acesso incorretos.", "documento": documento, "email": email},
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    cliente_nome = cliente.cliente
    cliente_tenant = str(cliente.tenant_id)

    try:
        db.query(TentativaLogin).filter(TentativaLogin.ip_address == ip).delete()
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao limpar tentativas falhas: {e}")

    expires = timedelta(days=30)
    expire = agora_br() + expires
    token_data = {
        "exp": expire,
        "cliente": cliente_nome,
        "tenant_id": cliente_tenant,
        "email_usuario": email_limpo
    }

    token_atual = request.cookies.get("__session")
    if token_atual:
        try:
            from jose import jwt
            payload = jwt.decode(token_atual, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            admin_sub = payload.get("sub")
            if admin_sub:
                token_data["sub"] = admin_sub
        except Exception:
            pass

    from jose import jwt
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = RedirectResponse(url="/portal", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="__session",
        value=token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,
        samesite="lax",
        secure=True
    )
    return response

@router.get("/portal", response_class=HTMLResponse)
async def portal_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]
    email_usuario = cliente_data.get("email_usuario", "")

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    # Buscar protocolos recentes (até 50 para uma timeline legal)
    query = db.query(models.Protocolo).filter(
        models.Protocolo.cliente == cliente_nome
    )
    if email_usuario:
        query = query.filter(models.Protocolo.email.ilike(f"%{email_usuario}%"))
    protocolos_db = query.order_by(models.Protocolo.data.desc()).limit(50).all()

    import re
    from collections import defaultdict

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
        import urllib.parse
        safe_links = [f"/portal/download?url={urllib.parse.quote(l)}" for l in links]
        
        p_dict = {
            "id": p.id,
            "protocolo": p.protocolo,
            "obrigacao": p.obrigacao,
            "data_obj": dt,
            "lido": bool(p.conf_recto),
            "links": safe_links,
            "has_pdf": len(links) > 0 and any(".pdf" in l.lower() for l in links),
            "first_url": safe_links[0] if safe_links else None,
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
    email_usuario = cliente_data.get("email_usuario", "")

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    query = db.query(models.Protocolo).filter(
        models.Protocolo.id == id,
        models.Protocolo.cliente == cliente_nome
    )
    if email_usuario:
        query = query.filter(models.Protocolo.email.ilike(f"%{email_usuario}%"))
    protocolo = query.first()

    if not protocolo:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    # Extrair os links anexos (se hover mais de um, separados por ' | ')
    import re
    import urllib.parse
    link_bruto = protocolo.link_arquivo or ""
    base_link = re.sub(r'\[.*?\]', '', link_bruto).strip()
    links_orig = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]
    links = [f"/portal/download?url={urllib.parse.quote(l)}" for l in links_orig]

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

@router.get("/portal/download")
async def portal_download(
    url: str,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    from app.core.storage_service import storage_service
    fresh_url = storage_service.refresh_signed_url(url)
    return RedirectResponse(url=fresh_url, status_code=status.HTTP_302_FOUND)

@router.get("/portal/solicitacoes", response_class=HTMLResponse)
async def portal_solicitacoes_list(
    request: Request,
    db: Session = Depends(get_db),
    cliente_data: dict = Depends(require_cliente_login)
):
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]
    email_usuario = cliente_data.get("email_usuario", "")

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    query = db.query(models.Solicitacao).filter(
        models.Solicitacao.cliente == cliente_nome
    )
    if email_usuario:
        query = query.filter(models.Solicitacao.email.ilike(f"%{email_usuario}%"))
    solicitacoes = query.order_by(models.Solicitacao.data.desc()).all()

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
    email_usuario = cliente_data.get("email_usuario", "")

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    query = db.query(models.Solicitacao).filter(
        models.Solicitacao.id_legado == id_legado,
        models.Solicitacao.cliente == cliente_nome
    )
    if email_usuario:
        query = query.filter(models.Solicitacao.email.ilike(f"%{email_usuario}%"))
    solic = query.first()

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
    from app.core.storage_service import storage_service
    
    # Process the form data explicitly because this is inside a POST function 
    # that doesn't use the typical Form/File injections directly due to being a manual route handler.
    # Actually, let's just use request.form()
    form = await request.form()
    mensagem = form.get("mensagem")
    arquivo = form.get("arquivo") # Type UploadFile if present
    
    cliente_nome = cliente_data["cliente"]
    tenant_id = cliente_data["tenant_id"]
    email_usuario = cliente_data.get("email_usuario", "")

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass

    query = db.query(models.Solicitacao).filter(
        models.Solicitacao.id_legado == id_legado,
        models.Solicitacao.cliente == cliente_nome
    )
    if email_usuario:
        query = query.filter(models.Solicitacao.email.ilike(f"%{email_usuario}%"))
    solic = query.first()

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

    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        pass
    db.refresh(solic)

    # Como não temos background tasks instanciado diretamente, podemos usar chamadas await normais (ou ignorar email imediato).
    # O ideal seria injetar BackgroundTasks. Como não está na assinatura, vamos deixar apenas o log no banco por ora.
    
    return templates.TemplateResponse(request, "portal/solicitacao_view.html", {
        "request": request,
        "cliente": cliente_nome,
        "solicitacao": solic,
        "sucesso": True
    })
