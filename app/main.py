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
    # Contexto para o template
    request.state.chatwoot_token = os.getenv("CHATWOOT_TOKEN", "")
    request.state.chatwoot_base_url = os.getenv("CHATWOOT_BASE_URL", "https://chat.janiopontes.com.br")
    
    response = await call_next(request)
    
    # Headers de Segurança (9.5.4)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

# Inclusão de Rotas
from app.routers import auth, cliente, regra, protocolo, webhook, scheduler, usuario, perfil, tarefa, historico, solicitacao, tipo_tarefa, workflow
app.include_router(auth.router, tags=["Autenticação"])
app.include_router(workflow.router, tags=["Workflows"])
app.include_router(tarefa.router, tags=["Tarefas"])
app.include_router(historico.router, tags=["Histórico"])
app.include_router(solicitacao.router, tags=["Solicitações"])
app.include_router(cliente.router, tags=["Clientes"])
app.include_router(regra.router, tags=["Regras e Obrigações"])
app.include_router(usuario.router, tags=["Usuários"])
app.include_router(perfil.router, tags=["Perfis"])
app.include_router(tipo_tarefa.router, tags=["Tipos de Tarefa"])
app.include_router(protocolo.router, tags=["Protocolos"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["Rotinas Agendadas"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    pendentes = db.query(models.Tarefa).filter(models.Tarefa.tenant_id == current_user.tenant_id, models.Tarefa.status == 'PENDENTE').count()
    entregues = db.query(models.Tarefa).filter(models.Tarefa.tenant_id == current_user.tenant_id, models.Tarefa.status == 'ENTREGUE').count()
    atrasadas = db.query(models.Tarefa).filter(models.Tarefa.tenant_id == current_user.tenant_id, models.Tarefa.status == 'ATRASADO').count()

    # Desempenho Setorial
    setores_raw = db.query(
        models.Tarefa.departamento,
        func.count(models.Tarefa.id).label('total'),
        func.sum(case((models.Tarefa.status == 'ENTREGUE', 1), else_=0)).label('entregues')
    ).filter(
        models.Tarefa.tenant_id == current_user.tenant_id
    ).group_by(models.Tarefa.departamento).all()
    
    desempenho_setorial = []
    for s in setores_raw:
        if not s.departamento: continue
        total = s.total or 0
        entregues = s.entregues or 0
        percentual = int((entregues / total * 100)) if total > 0 else 0
        desempenho_setorial.append({
            "departamento": s.departamento,
            "total": total,
            "entregues": entregues,
            "percentual": percentual
        })
    desempenho_setorial.sort(key=lambda x: x['percentual'], reverse=True)

    # Ranking Equipe (Entregues)
    ranking_raw = db.query(
        models.Tarefa.responsavel,
        func.count(models.Tarefa.id).label('entregues')
    ).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'ENTREGUE'
    ).group_by(models.Tarefa.responsavel).order_by(func.count(models.Tarefa.id).desc()).limit(5).all()

    ranking_equipe = [{"responsavel": r.responsavel or "Nao atribuido", "entregues": r.entregues} for r in ranking_raw]

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
