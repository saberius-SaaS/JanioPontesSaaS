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

templates = Jinja2Templates(directory="app/templates")

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
from app.routers import auth, cliente, regra, protocolo, webhook, scheduler, usuario, perfil
app.include_router(auth.router, tags=["Autenticação"])
app.include_router(cliente.router, tags=["Clientes"])
app.include_router(regra.router, tags=["Regras e Obrigações"])
app.include_router(usuario.router, tags=["Usuários"])
app.include_router(perfil.router, tags=["Perfis"])
app.include_router(protocolo.router, tags=["Protocolos"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["Rotinas Agendadas"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user: models.Usuario = Depends(require_login)):
    return templates.TemplateResponse(request=request, name="base.html", context={
        "request": request,
        "user": current_user,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@app.get("/htmx-test", response_class=HTMLResponse)
async def htmx_test(request: Request):
    return "<p class='text-green-600 font-bold'>Requisição HTMX funcionou com sucesso!</p>"
