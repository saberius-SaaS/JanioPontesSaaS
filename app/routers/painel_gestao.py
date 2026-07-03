from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from collections import defaultdict

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
    
    # Query Tarefas
    q_tarefas = db.query(models.Tarefa).filter(models.Tarefa.tenant_id == current_user.tenant_id)
    if mes_ano and mes_ano != "todos":
        q_tarefas = q_tarefas.filter(models.Tarefa.mes_ano == mes_ano)
    tarefas_ativas = q_tarefas.all()

    # Query Historico
    q_hist = db.query(models.HistoricoTarefa).filter(models.HistoricoTarefa.tenant_id == current_user.tenant_id)
    if mes_ano and mes_ano != "todos":
        q_hist = q_hist.filter(models.HistoricoTarefa.mes_ano == mes_ano)
    tarefas_hist = q_hist.all()

    tarefas = tarefas_ativas + tarefas_hist

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
        status_visual = "NO_PRAZO"
        dias_atraso = 0
        if t.status != "ENTREGUE":
            if t.vencimento_legal and t.vencimento_legal < hoje:
                status_visual = "ATRASADA_LEGAL"
                dias_atraso = (hoje - t.vencimento_legal).days
            elif t.vencimento and t.vencimento < hoje:
                status_visual = "ATRASADA_INTERNO"
                dias_atraso = (hoje - t.vencimento).days
        else:
            status_visual = "ENTREGUE"

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
            "protocolo": t.protocolo or "-",
            "dias_atraso": dias_atraso
        })

    # Resumo global
    total = len(resultados)
    entregues = sum(1 for r in resultados if r["status_visual"] == "ENTREGUE")
    no_prazo = sum(1 for r in resultados if r["status_visual"] == "NO_PRAZO")
    atraso_interno = sum(1 for r in resultados if r["status_visual"] == "ATRASADA_INTERNO")
    atraso_legal = sum(1 for r in resultados if r["status_visual"] == "ATRASADA_LEGAL")

    resumo = {
        "total": total,
        "entregues": entregues,
        "no_prazo": no_prazo,
        "atraso_interno": atraso_interno,
        "atraso_legal": atraso_legal,
        "percentual_conclusao": round(entregues / total * 100, 1) if total > 0 else 0
    }

    # Top 5 clientes com mais atrasos
    atrasos_por_cliente = defaultdict(int)
    for r in resultados:
        if r["status_visual"] in ("ATRASADA_INTERNO", "ATRASADA_LEGAL"):
            atrasos_por_cliente[r["cliente"]] += 1
    top_atrasos = sorted(atrasos_por_cliente.items(), key=lambda x: x[1], reverse=True)[:5]
    top_atrasos = [{"nome": n, "qtd": q} for n, q in top_atrasos]

    # Agrupar com sub-resumo
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

    agrupado_enriquecido = {}
    for chave in sorted(agrupado.keys()):
        itens = agrupado[chave]
        grp_total = len(itens)
        grp_entregues = sum(1 for i in itens if i["status_visual"] == "ENTREGUE")
        grp_atrasos = sum(1 for i in itens if "ATRASADA" in i["status_visual"])
        agrupado_enriquecido[chave] = {
            "itens": itens,
            "total": grp_total,
            "entregues": grp_entregues,
            "percentual": round(grp_entregues / grp_total * 100) if grp_total > 0 else 0,
            "atrasos": grp_atrasos
        }

    return {
        "dados": agrupado_enriquecido,
        "visao": visao,
        "resumo": resumo,
        "top_atrasos": top_atrasos
    }
