from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from app.routers import auth

app = FastAPI(title="Janio Pontes SaaS", description="API para a plataforma Janio Pontes SaaS")

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
import os

from app.api.deps import require_login
from app import models

templates = Jinja2Templates(directory="app/templates")

# Middleware para injetar variáveis globais nos templates
@app.middleware("http")
async def add_global_template_context(request: Request, call_next):
    # Pode não estar presente para rotas que não usam templates, mas não atrapalha
    request.state.chatwoot_token = os.getenv("CHATWOOT_TOKEN", "")
    request.state.chatwoot_base_url = os.getenv("CHATWOOT_BASE_URL", "https://chat.janiopontes.com.br")
    response = await call_next(request)
    return response

# Inclusão de Rotas
from app.routers import auth, cliente, regra, protocolo, webhook, scheduler
app.include_router(auth.router, tags=["Autenticação"])
app.include_router(cliente.router, tags=["Clientes"])
app.include_router(regra.router, tags=["Regras e Obrigações"])
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
