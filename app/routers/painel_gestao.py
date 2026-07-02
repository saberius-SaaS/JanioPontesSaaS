from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/painel-gestao", response_class=HTMLResponse)
async def painel_gestao_view(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Buscar periodos disponíveis
    periodos_db = db.query(models.Tarefa.mes_ano).filter(
        models.Tarefa.tenant_id == current_user.tenant_id
    ).distinct().all()
    periodos = sorted([p[0] for p in periodos_db if p[0]], reverse=True)
    
    return templates.TemplateResponse(request, "painel_gestao.html", {
        "request": request,
        "user": current_user,
        "periodos": periodos,
        "page_title": "Painel de Acompanhamento de Trabalhos"
    })

@router.get("/painel-gestao/dados")
async def obter_dados_painel(
    visao: str = Query("cliente", description="cliente | tarefa | periodo | responsavel"),
    mes_ano: Optional[str] = Query(None, description="Filtro de competencia"),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        raise HTTPException(status_code=403, detail="Acesso negado")

    hoje = date.today()
    
    # Montar base query (Tarefas)
    base_query = db.query(models.Tarefa).filter(models.Tarefa.tenant_id == current_user.tenant_id)
    if mes_ano and mes_ano != "todos":
        base_query = base_query.filter(models.Tarefa.mes_ano == mes_ano)

    tarefas = base_query.all()

    # Pre-fetch protocolos para otimizar a query (evitar N+1)
    protocolos_ids = [t.protocolo for t in tarefas if t.protocolo]
    protocolos_db = {}
    if protocolos_ids:
        prots = db.query(models.Protocolo).filter(
            models.Protocolo.protocolo.in_(protocolos_ids),
            models.Protocolo.tenant_id == current_user.tenant_id
        ).all()
        for p in prots:
            protocolos_db[p.protocolo] = p

    resultados = []
    
    for t in tarefas:
        status_visual = "NO_PRAZO" # Verde
        if t.status != "ENTREGUE":
            if t.vencimento_legal and t.vencimento_legal < hoje:
                status_visual = "ATRASADA_LEGAL" # Vermelho
            elif t.vencimento and t.vencimento < hoje:
                status_visual = "ATRASADA_INTERNO" # Amarelo/Laranja
        else:
            status_visual = "ENTREGUE" # Verde/Cinza

        data_entrega = None
        data_leitura = None
        if t.protocolo and t.protocolo in protocolos_db:
            prot = protocolos_db[t.protocolo]
            data_entrega = prot.data.strftime('%d/%m/%Y %H:%M') if prot.data else None
            data_leitura = prot.conf_recto.strftime('%d/%m/%Y %H:%M') if prot.conf_recto else None

        resultados.append({
            "id": str(t.id),
            "cliente": t.cliente,
            "obrigacao": t.obrigacao,
            "mes_ano": t.mes_ano,
            "responsavel": t.responsavel or "Não atribuído",
            "vencimento_interno": t.vencimento.strftime('%d/%m/%Y') if t.vencimento else "-",
            "vencimento_legal": t.vencimento_legal.strftime('%d/%m/%Y') if t.vencimento_legal else "-",
            "data_entrega": data_entrega or "-",
            "data_leitura": data_leitura or "-",
            "status_visual": status_visual,
            "status_real": t.status,
            "protocolo": t.protocolo or "-"
        })
        
    agrupado = {}
    for r in resultados:
        chave = "Outros"
        if visao == "cliente":
            chave = r["cliente"]
        elif visao == "tarefa":
            chave = r["obrigacao"]
        elif visao == "periodo":
            chave = r["mes_ano"]
        elif visao == "responsavel":
            chave = r["responsavel"]
            
        if chave not in agrupado:
            agrupado[chave] = []
        agrupado[chave].append(r)
        
    # Order chaves
    agrupado_ordenado = {k: agrupado[k] for k in sorted(agrupado.keys())}
    
    return {"dados": agrupado_ordenado, "visao": visao}
