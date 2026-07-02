from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.email_service import email_service
from fastapi import BackgroundTasks

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/historico", response_class=HTMLResponse)
async def list_historico(
    request: Request,
    mes: str = Query(default="", description="Filtro por mes_ano"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    query = db.query(models.HistoricoTarefa, models.Protocolo.link_arquivo, models.Protocolo.conf_recto).outerjoin(
        models.Protocolo,
        (models.Protocolo.tenant_id == models.HistoricoTarefa.tenant_id) &
        (models.Protocolo.protocolo == models.HistoricoTarefa.protocolo)
    ).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    )

    if current_user.nivel not in ['ADMIN', 'MASTER']:
        from sqlalchemy import or_
        nomes_equipes = [eq.equipe.nome for eq in current_user.equipes]
        filtros_resp = [current_user.nome, current_user.email] + nomes_equipes
        filtros_resp = [f for f in filtros_resp if f]
        if filtros_resp:
            query = query.filter(or_(*[models.HistoricoTarefa.responsavel.ilike(f"%{f}%") for f in filtros_resp]))
        else:
            query = query.filter(models.HistoricoTarefa.responsavel == None)
    
    if mes:
        query = query.filter(models.HistoricoTarefa.mes_ano == mes)
    
    historicos_raw = query.order_by(models.HistoricoTarefa.criado_em.desc()).limit(300).all()
    
    import re
    historicos = []
    for h, link, conf_recto in historicos_raw:
        link = link or ""
        
        # Extrai links de URL puros
        urls = []
        base_link = re.sub(r'\[(.*?)\]', '', link).strip()
        if base_link:
            urls = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]
            
        # Extrai mensagens ou justificativas (ex: [COMUNICADO: texto], [ARQUIVADO: justificativa])
        obs_match = re.search(r'\[(.*?)\]', link)
        mensagem = obs_match.group(1) if obs_match else ""
        
        h.anexos = urls
        h.mensagem_enviada = mensagem
        h.conf_recto_proto = conf_recto
        historicos.append(h)
    
    # Busca meses disponíveis para o filtro
    meses_raw = db.query(models.HistoricoTarefa.mes_ano).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    ).distinct().all()
    meses = sorted(set(m[0] for m in meses_raw if m[0]), reverse=True)

    return templates.TemplateResponse(request=request, name="historico.html", context={
        "request": request,
        "user": current_user,
        "historicos": historicos,
        "meses": meses,
        "mes_selecionado": mes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.post("/historico/{id}/reenviar")
async def reenviar_historico(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    historico = db.query(models.HistoricoTarefa).filter(
        models.HistoricoTarefa.id == id,
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    ).first()
    
    if not historico or not historico.protocolo:
        return JSONResponse(status_code=400, content={"detail": "Histórico não possui protocolo vinculado."})
        
    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.protocolo == historico.protocolo,
        models.Protocolo.tenant_id == current_user.tenant_id
    ).first()
    
    if not protocolo or not protocolo.email:
        return JSONResponse(status_code=400, content={"detail": "E-mail ou dados do protocolo não encontrados."})
        
    link = protocolo.link_arquivo or "Não anexado"
    
    corpo_html = f"""
    <div style="font-family: 'Inter', 'Roboto', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
        <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
            <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">REENVIO DE DOCUMENTOS</p>
        </div>
        <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a),</p>
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Estamos reenviando o documento abaixo, que já se encontra disponível:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 0 0 20px;">
                <tr>
                    <td style="padding: 10px; background: #f1f5f9; border-radius: 8px 0 0 0; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Obrigação / Referência</td>
                    <td style="padding: 10px; background: #f1f5f9; border-radius: 0 8px 0 0; font-size: 14px; font-weight: bold; color: #1C3051;">{protocolo.obrigacao}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Protocolo Original</td>
                    <td style="padding: 10px; font-size: 14px; font-weight: bold; color: #6366f1;">{protocolo.protocolo}</td>
                </tr>
            </table>
            <p style="text-align: center; margin: 30px 0;"><a href='https://app.janiopontes.com.br/acesso/{protocolo.protocolo}' style="display: inline-block; background-color: #6366f1; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">Acessar no Portal do Cliente</a></p>
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                <p style="color: #64748b; font-size: 12px; margin: 0; font-weight: bold;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</p>
                <p style="color: #94a3b8; font-size: 10px; margin: 5px 0 0;">O link acima concede acesso seguro aos arquivos desta entrega.</p>
            </div>
        </div>
    </div>
    """
    
    background_tasks.add_task(email_service.enviar_email, protocolo.email, f"[REENVIO] Documento: {protocolo.obrigacao}", corpo_html)
    
    return HTMLResponse(content='<span class="text-xs font-bold text-emerald-600"><i class="fa-solid fa-check mr-1"></i>Reenviado</span>')

@router.post("/historico/{id}/reverter")
async def reverter_historico(
    id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    import datetime
    
    historico = db.query(models.HistoricoTarefa).filter(
        models.HistoricoTarefa.id == id,
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    ).first()
    
    if not historico:
        return JSONResponse(status_code=404, content={"detail": "Histórico não encontrado."})
        
    if historico.protocolo:
        tarefa = db.query(models.Tarefa).filter(
            models.Tarefa.protocolo == historico.protocolo,
            models.Tarefa.tenant_id == current_user.tenant_id
        ).first()
        
        if tarefa:
            if tarefa.vencimento and tarefa.vencimento < datetime.date.today():
                tarefa.status = 'ATRASADO'
            else:
                tarefa.status = 'PENDENTE'
            
            tarefa.protocolo = None

        prot = db.query(models.Protocolo).filter(
            models.Protocolo.protocolo == historico.protocolo,
            models.Protocolo.tenant_id == current_user.tenant_id
        ).first()
        if prot:
            db.delete(prot)
            
    db.delete(historico)
    db.commit()
    
    return HTMLResponse(content='<span class="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200"><i class="fa-solid fa-rotate-left mr-1"></i>Revertida</span>')

@router.get("/historico/fix-tarefas")
async def fix_stuck_tarefas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    import datetime
    
    tarefas_stuck = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['ENTREGUE', 'REVISAO'])
    ).all()
    
    fixed = 0
    for t in tarefas_stuck:
        h = None
        if t.protocolo:
            h = db.query(models.HistoricoTarefa).filter(
                models.HistoricoTarefa.protocolo == t.protocolo,
                models.HistoricoTarefa.tenant_id == current_user.tenant_id
            ).first()
        
        if not h:
            if t.vencimento and t.vencimento < datetime.date.today():
                t.status = 'ATRASADO'
            else:
                t.status = 'PENDENTE'
            t.protocolo = None
            fixed += 1
            
    db.commit()
    return JSONResponse(content={"message": f"Corrigidas {fixed} tarefas presas!"})

@router.get("/historico/busca-debug")
async def debug_buscar_tarefa(
    q: str = Query(default="", description="Termo para buscar na obrigacao ou cliente"),
    prot: str = Query(default="", description="Busca por protocolo"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    from sqlalchemy import or_
    
    # Busca em TAREFAS (todos os status)
    query_t = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id
    )
    if prot:
        query_t = query_t.filter(models.Tarefa.protocolo == prot)
    elif q:
        query_t = query_t.filter(or_(
            models.Tarefa.obrigacao.ilike(f"%{q}%"),
            models.Tarefa.cliente.ilike(f"%{q}%")
        ))
    tarefas = query_t.order_by(models.Tarefa.id.desc()).limit(30).all()
    
    # Busca em HISTORICO
    query_h = db.query(models.HistoricoTarefa).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id
    )
    if prot:
        query_h = query_h.filter(models.HistoricoTarefa.protocolo == prot)
    elif q:
        query_h = query_h.filter(or_(
            models.HistoricoTarefa.obrigacao.ilike(f"%{q}%"),
            models.HistoricoTarefa.cliente.ilike(f"%{q}%")
        ))
    historicos = query_h.order_by(models.HistoricoTarefa.id.desc()).limit(30).all()
    
    # Busca em PROTOCOLOS
    query_p = db.query(models.Protocolo).filter(
        models.Protocolo.tenant_id == current_user.tenant_id
    )
    if prot:
        query_p = query_p.filter(models.Protocolo.protocolo == prot)
    elif q:
        query_p = query_p.filter(or_(
            models.Protocolo.obrigacao.ilike(f"%{q}%"),
            models.Protocolo.cliente.ilike(f"%{q}%")
        ))
    protocolos = query_p.order_by(models.Protocolo.id.desc()).limit(30).all()

    resultado_t = []
    for t in tarefas:
        resultado_t.append({
            "id": str(t.id), "cliente": t.cliente, "obrigacao": t.obrigacao,
            "status": t.status, "protocolo": t.protocolo, "mes_ano": t.mes_ano,
            "vencimento": str(t.vencimento) if t.vencimento else None,
            "id_controle": t.id_controle, "responsavel": t.responsavel
        })
    
    resultado_h = []
    for h in historicos:
        resultado_h.append({
            "id": str(h.id), "cliente": h.cliente, "obrigacao": h.obrigacao,
            "status": h.status, "protocolo": h.protocolo, "mes_ano": h.mes_ano,
            "id_controle": h.id_controle
        })

    resultado_p = []
    for p in protocolos:
        resultado_p.append({
            "protocolo": p.protocolo, "cliente": p.cliente,
            "obrigacao": p.obrigacao, "status_envio": p.status_envio
        })
        
    return JSONResponse(content={
        "tarefas": {"total": len(resultado_t), "registros": resultado_t},
        "historico": {"total": len(resultado_h), "registros": resultado_h},
        "protocolos": {"total": len(resultado_p), "registros": resultado_p}
    })

@router.get("/historico/diag-usuario")
async def diagnostico_usuario(
    email: str = Query(default="", description="Email do usuario para diagnosticar"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return JSONResponse(status_code=403, content={"detail": "Somente ADMIN"})
    
    if email:
        user = db.query(models.Usuario).filter(
            models.Usuario.email == email,
            models.Usuario.tenant_id == current_user.tenant_id
        ).first()
    else:
        user = current_user
        
    if not user:
        return JSONResponse(content={"erro": f"Usuario {email} nao encontrado"})
    
    nomes_equipes = [eq.equipe.nome for eq in user.equipes]
    filtros = [user.nome, user.email] + nomes_equipes
    filtros = [f for f in filtros if f]
    
    # Amostrar responsaveis unicos das tarefas pendentes
    from sqlalchemy import distinct
    responsaveis = db.query(distinct(models.Tarefa.responsavel)).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['PENDENTE', 'ATRASADO'])
    ).limit(50).all()
    responsaveis_lista = [r[0] for r in responsaveis if r[0]]
    
    # Quantas tarefas ela veria com o filtro atual
    from sqlalchemy import or_
    if filtros:
        count = db.query(models.Tarefa).filter(
            models.Tarefa.tenant_id == current_user.tenant_id,
            models.Tarefa.status.in_(['PENDENTE', 'ATRASADO']),
            or_(*[models.Tarefa.responsavel.ilike(f"%{f}%") for f in filtros])
        ).count()
    else:
        count = 0
    
    return JSONResponse(content={
        "usuario": {"nome": user.nome, "email": user.email, "nivel": user.nivel},
        "equipes": nomes_equipes,
        "filtros_aplicados": filtros,
        "tarefas_visiveis": count,
        "responsaveis_existentes": responsaveis_lista
    })
