from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

app = FastAPI(
    title="Janio Pontes SaaS", 
    description="API para a plataforma Janio Pontes SaaS",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if ENVIRONMENT != "production" else None
)

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Configuração de CORS (necessário para o frontend interagir com a API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar as origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Montar diretório de arquivos estáticos (CSS Tailwind, JS, Imagens)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request, Depends

from app.api.deps import require_login
from app import models
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, case

templates = Jinja2Templates(directory="app/templates")

# Evento de startup para migrações incrementais de schema
@app.on_event("startup")
def ensure_schema_updates():
    """Garante que colunas novas existam no banco (migrações leves)."""
    from app.database import engine
    from sqlalchemy import text, inspect
    import logging
    logger = logging.getLogger(__name__)
    try:
        insp = inspect(engine)
        colunas = [c["name"] for c in insp.get_columns("clientes")]
        if "data_entrada" not in colunas:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN data_entrada DATE"))
                conn.commit()
                logger.info("[SCHEMA] Coluna 'data_entrada' adicionada à tabela 'clientes'.")
    except Exception as e:
        logger.warning(f"[SCHEMA] Não foi possível verificar/criar coluna data_entrada: {e}")

# Middleware para injetar variáveis globais nos templates e Headers de Segurança
@app.middleware("http")
async def add_global_template_context_and_security(request: Request, call_next):
    from app.core.config import settings
    # Contexto para o template
    request.state.chatwoot_token = settings.CHATWOOT_WEB_TOKEN
    request.state.chatwoot_base_url = settings.CHATWOOT_BASE_URL
    
    response = await call_next(request)
    
    # Headers de Segurança (9.5.4)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# Inclusão de Rotas
from app.routers import auth, cliente, regra, protocolo, webhook, scheduler, usuario, equipe, perfil, tarefa, historico, solicitacao, tipo_tarefa, workflow, compliance, portal, ferramentas
app.include_router(auth.router, tags=["Autenticação"])
app.include_router(ferramentas.router, tags=["Ferramentas"])
app.include_router(portal.router, tags=["Portal do Cliente"])
app.include_router(workflow.router, tags=["Workflows"])
app.include_router(tarefa.router, tags=["Tarefas"])
app.include_router(historico.router, tags=["Histórico"])
app.include_router(solicitacao.router, tags=["Solicitações"])
app.include_router(compliance.router, tags=["Compliance"])
app.include_router(cliente.router, tags=["Clientes"])
app.include_router(regra.router, tags=["Regras e Obrigações"])
app.include_router(usuario.router, tags=["Usuários"])
app.include_router(equipe.router, tags=["Equipes"])

app.include_router(perfil.router, tags=["Perfis"])
app.include_router(tipo_tarefa.router, tags=["Tipos de Tarefa"])
app.include_router(protocolo.router, tags=["Protocolos"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["Rotinas Agendadas"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    from datetime import date
    hoje = date.today()
    inicio_mes = date(hoje.year, hoje.month, 1)
    if hoje.month == 12:
        fim_mes = date(hoje.year + 1, 1, 1)
    else:
        fim_mes = date(hoje.year, hoje.month + 1, 1)
    mes_ano_ref = f"{hoje.month:02d}/{hoje.year}"

    # Pendentes do mês: tarefas NÃO-entregues com vencimento <= fim do mês
    # (Alinhado com GAS DashboardService: inclui PENDENTE, REVISAO, REPROVADO, ATRASADO)
    pendentes = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.notin_(['ENTREGUE']),
        models.Tarefa.vencimento != None,
        models.Tarefa.vencimento < fim_mes
    ).count()

    # Entregas do mês: ENTREGUE na fila ativa + histórico do mês atual
    entregues_ativas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'ENTREGUE',
        models.Tarefa.vencimento != None,
        models.Tarefa.vencimento >= inicio_mes,
        models.Tarefa.vencimento < fim_mes
    ).count()
    entregues_historico = db.query(models.HistoricoTarefa).filter(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id,
        models.HistoricoTarefa.status == 'ENTREGUE',
        models.HistoricoTarefa.vencimento != None,
        models.HistoricoTarefa.vencimento >= inicio_mes,
        models.HistoricoTarefa.vencimento < fim_mes
    ).count()
    entregues = entregues_ativas + entregues_historico

    # Risco Legal: tarefas PENDENTE com vencimento <= hoje
    # (Alinhado com GAS WebAppRoute: apenas status PENDENTE, vencimento vencido)
    atrasadas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'PENDENTE',
        models.Tarefa.vencimento != None,
        models.Tarefa.vencimento <= hoje
    ).count()

    # --- Desempenho e Ranking (Ativas + Histórico do Mês) ---
    from sqlalchemy import select, union_all
    
    stmt1 = select(
        models.Tarefa.tenant_id,
        models.Tarefa.departamento,
        models.Tarefa.responsavel,
        models.Tarefa.status,
        models.Tarefa.id
    ).where(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.vencimento >= inicio_mes,
        models.Tarefa.vencimento < fim_mes
    )
    
    stmt2 = select(
        models.HistoricoTarefa.tenant_id,
        models.HistoricoTarefa.departamento,
        models.HistoricoTarefa.responsavel,
        models.HistoricoTarefa.status,
        models.HistoricoTarefa.id
    ).where(
        models.HistoricoTarefa.tenant_id == current_user.tenant_id,
        models.HistoricoTarefa.vencimento >= inicio_mes,
        models.HistoricoTarefa.vencimento < fim_mes
    )
    
    subq = union_all(stmt1, stmt2).subquery()
    
    # Desempenho Setorial
    setores_raw = db.query(
        subq.c.departamento,
        func.count(subq.c.id).label('total'),
        func.sum(case((subq.c.status == 'ENTREGUE', 1), else_=0)).label('entregues')
    ).group_by(subq.c.departamento).all()
    
    desempenho_setorial = []
    for s in setores_raw:
        if not s.departamento: continue
        total_setor = s.total or 0
        entregues_setor = s.entregues or 0
        percentual = int((entregues_setor / total_setor * 100)) if total_setor > 0 else 0
        desempenho_setorial.append({
            "departamento": s.departamento,
            "total": total_setor,
            "entregues": entregues_setor,
            "percentual": percentual
        })
    desempenho_setorial.sort(key=lambda x: x['percentual'], reverse=True)

    # Ranking Equipe
    ranking_raw = db.query(
        subq.c.responsavel,
        func.count(subq.c.id).label('total'),
        func.sum(case((subq.c.status == 'ENTREGUE', 1), else_=0)).label('entregues')
    ).group_by(subq.c.responsavel).all()

    ranking_equipe = []
    for r in ranking_raw:
        if not r.responsavel: continue
        total_resp = r.total or 0
        entregues_resp = r.entregues or 0
        if total_resp == 0: continue
        percentual = int((entregues_resp / total_resp * 100))
        ranking_equipe.append({
            "responsavel": r.responsavel,
            "total": total_resp,
            "entregues": entregues_resp,
            "percentual": percentual
        })
    ranking_equipe.sort(key=lambda x: x['total'], reverse=True)
    ranking_equipe = ranking_equipe[:5]

    return templates.TemplateResponse(request=request, name="base.html", context={
        "request": request,
        "user": current_user,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", ""),
        "pendentes": pendentes,
        "entregues": entregues,
        "atrasadas": atrasadas,
        "desempenho_setorial": desempenho_setorial,
        "ranking_equipe": ranking_equipe
    })

@app.get("/htmx-test", response_class=HTMLResponse)
async def htmx_test(request: Request):
    return "<p class='text-green-600 font-bold'>Requisição HTMX funcionou com sucesso!</p>"

@app.get("/atendimento", response_class=HTMLResponse)
async def atendimento_view(request: Request, current_user: models.Usuario = Depends(require_login)):
    chatwoot_url = getattr(request.state, "chatwoot_base_url", "https://chat.janiopontes.com.br")
    return templates.TemplateResponse(request, "atendimento.html", {
        "request": request,
        "user": current_user,
        "chatwoot_url": chatwoot_url
    })

@app.get("/chatwoot-sso")
async def chatwoot_sso(request: Request, current_user: models.Usuario = Depends(require_login)):
    """
    Tenta logar o agente automaticamente no Chatwoot via Platform API.
    Se não for possível, redireciona para a tela de login manual do Chatwoot.
    """
    from app.core.chatwoot_service import chatwoot_service
    from app.core.config import settings
    from fastapi.responses import RedirectResponse
    
    fallback_url = f"{settings.CHATWOOT_BASE_URL.rstrip('/')}/app/login"
    
    # 1. Encontra o agente pelo email
    agent_id = await chatwoot_service.get_agent_by_email(current_user.email)
    if not agent_id:
        return RedirectResponse(url=fallback_url)
        
    # 2. Gera o URL de SSO
    sso_url = await chatwoot_service.get_sso_url(agent_id)
    if not sso_url:
        return RedirectResponse(url=fallback_url)
        
    # 3. Redireciona com o token
    return RedirectResponse(url=sso_url)
