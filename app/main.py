from fastapi import FastAPI
from sqlalchemy import extract as sa_extract
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

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request, Depends

from app.api.deps import require_login
from app import models
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_

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
                
        # Criar tabela de solicitações recorrentes caso não exista
        try:
            from app.models.solicitacao_recorrente import SolicitacaoRecorrente
            SolicitacaoRecorrente.__table__.create(engine, checkfirst=True)
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE solicitacoes_recorrentes ENABLE ROW LEVEL SECURITY;"))
                # Cria a policy se não existir
                conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies WHERE tablename = 'solicitacoes_recorrentes' AND policyname = 'tenant_isolation_policy'
                    ) THEN
                        CREATE POLICY tenant_isolation_policy ON solicitacoes_recorrentes 
                        USING (tenant_id::text = current_setting('app.current_tenant', true) OR current_setting('app.bypass_rls', true) = 'on');
                    END IF;
                END
                $$;
                """))
                conn.commit()
            logger.info("[SCHEMA] Tabela 'solicitacoes_recorrentes' e RLS verificados/criados.")
        except Exception as e:
            logger.warning(f"[SCHEMA] Erro ao criar tabela solicitacoes_recorrentes: {e}")
        
        if "regras_roteamento" not in colunas:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN regras_roteamento TEXT"))
                conn.commit()
                logger.info("[SCHEMA] Coluna 'regras_roteamento' adicionada à tabela 'clientes'.")
    except Exception as e:
        logger.warning(f"[SCHEMA] Não foi possível verificar/criar coluna data_entrada ou regras_roteamento: {e}")

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
from app.routers import auth, cliente, regra, protocolo, webhook, scheduler, usuario, equipe, perfil, tarefa, historico, solicitacao, tipo_tarefa, workflow, compliance, portal, ferramentas, certificados, sobre
app.include_router(auth.router, tags=["Autenticação"])
app.include_router(ferramentas.router, tags=["Ferramentas"])
app.include_router(sobre.router, tags=["Sobre"])
app.include_router(portal.router, tags=["Portal do Cliente"])
app.include_router(workflow.router, tags=["Workflows"])
app.include_router(tarefa.router, tags=["Tarefas"])
app.include_router(historico.router, tags=["Histórico"])
app.include_router(solicitacao.router, tags=["Solicitações"])
app.include_router(compliance.router, tags=["Compliance"])
app.include_router(cliente.router, tags=["Clientes"])
app.include_router(certificados.router, tags=["Certificados"])
app.include_router(regra.router, tags=["Regras e Obrigações"])
app.include_router(usuario.router, tags=["Usuários"])
app.include_router(equipe.router, tags=["Equipes"])

app.include_router(perfil.router, tags=["Perfis"])
app.include_router(tipo_tarefa.router, tags=["Tipos de Tarefa"])
app.include_router(protocolo.router, tags=["Protocolos"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(scheduler.router, prefix="/scheduler", tags=["Rotinas Agendadas"])

from app.routers import solicitacao_recorrente
app.include_router(solicitacao_recorrente.router, tags=["Solicitações Recorrentes"])

from app.routers import painel_gestao
app.include_router(painel_gestao.router, tags=["Painel de Gestão"])

@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request, 
    departamento: str = None,
    periodo: str = None,
    tipo_pesquisa: str = "vencimento",
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(require_login)
):
    from datetime import date
    hoje = date.today()
    
    # Buscar meses que possuem tarefas pendentes
    periodos_db = db.query(models.Tarefa.mes_ano).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.notin_(['ENTREGUE'])
    ).distinct().all()
    
    periodos_lista = [p[0] for p in periodos_db if p[0]]
    
    # Garantir que o mês atual sempre esteja na lista para não ficar vazia
    mes_atual_str = f"{hoje.month:02d}/{hoje.year}"
    if mes_atual_str not in periodos_lista:
        periodos_lista.append(mes_atual_str)
        
    # Ordenar cronologicamente (Ano, depois Mês)
    def parse_mes_ano(ma):
        try:
            m, y = map(int, ma.split('/'))
            return (y, m)
        except:
            return (0, 0)
            
    periodos_lista.sort(key=parse_mes_ano)
    periodos = periodos_lista
        
    periodo_selecionado = periodo if periodo else f"{hoje.month:02d}/{hoje.year}"
    
    filtro_periodo = []
    filtro_periodo_hist = []
    
    if periodo_selecionado != 'todos':
        if tipo_pesquisa == 'vencimento':
            try:
                mes, ano = periodo_selecionado.split('/')
                filtro_periodo = [
                    sa_extract('month', models.Tarefa.vencimento) == int(mes),
                    sa_extract('year', models.Tarefa.vencimento) == int(ano)
                ]
                filtro_periodo_hist = [
                    sa_extract('month', models.HistoricoTarefa.vencimento) == int(mes),
                    sa_extract('year', models.HistoricoTarefa.vencimento) == int(ano)
                ]
            except ValueError:
                filtro_periodo = [models.Tarefa.mes_ano == periodo_selecionado]
                filtro_periodo_hist = [models.HistoricoTarefa.mes_ano == periodo_selecionado]
        else:
            filtro_periodo = [models.Tarefa.mes_ano == periodo_selecionado]
            filtro_periodo_hist = [models.HistoricoTarefa.mes_ano == periodo_selecionado]

    # Buscar lista de departamentos disponíveis para o filtro
    departamentos_db = db.query(models.Equipe.departamento).filter(
        models.Equipe.tenant_id == current_user.tenant_id
    ).distinct().order_by(models.Equipe.departamento).all()
    departamentos_lista = [d[0] for d in departamentos_db if d[0]]

    # Preparar filtro base
    filtro_depto = []
    if departamento and departamento != 'TODOS':
        filtro_depto = [models.Tarefa.departamento == departamento]
        
    filtro_depto_hist = []
    if departamento and departamento != 'TODOS':
        filtro_depto_hist = [models.HistoricoTarefa.departamento == departamento]

    # Pendentes do período
    filtro_pendentes = [
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.notin_(['ENTREGUE'])
    ] + filtro_periodo
        
    pendentes = db.query(models.Tarefa).filter(
        *filtro_pendentes,
        *filtro_depto
    ).count()

    # Entregas do período: ENTREGUE na fila ativa + histórico
    filtro_entregues = [
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'ENTREGUE'
    ] + filtro_periodo

    entregues_ativas = db.query(models.Tarefa).filter(
        *filtro_entregues,
        *filtro_depto
    ).count()
    
    filtro_entregues_hist = [
        models.HistoricoTarefa.tenant_id == current_user.tenant_id,
        models.HistoricoTarefa.status == 'ENTREGUE'
    ] + filtro_periodo_hist

    entregues_historico = db.query(models.HistoricoTarefa).filter(
        *filtro_entregues_hist,
        *filtro_depto_hist
    ).count()
    entregues = entregues_ativas + entregues_historico

    # Risco Legal: Tarefas não entregues (PENDENTE, REVISAO, etc) com vencimento_legal ou interno vencidos
    atrasadas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.notin_(['ENTREGUE']),
        or_(
            models.Tarefa.vencimento < hoje,
            models.Tarefa.vencimento_legal < hoje
        ),
        *filtro_depto,
        *filtro_periodo
    ).count()

    
    # Protocolos pendentes de leitura foram movidos para o endpoint /api/badges

    # --- Desempenho e Ranking (Ativas + Histórico do Período) ---
    from sqlalchemy import select, union_all
    
    filtro_desempenho_ativa = [models.Tarefa.tenant_id == current_user.tenant_id] + filtro_periodo
        
    stmt1 = select(
        models.Tarefa.tenant_id,
        models.Tarefa.departamento,
        models.Tarefa.responsavel,
        models.Tarefa.status,
        models.Tarefa.id
    ).where(*filtro_desempenho_ativa)
    
    filtro_desempenho_hist = [models.HistoricoTarefa.tenant_id == current_user.tenant_id] + filtro_periodo_hist
        
    stmt2 = select(
        models.HistoricoTarefa.tenant_id,
        models.HistoricoTarefa.departamento,
        models.HistoricoTarefa.responsavel,
        models.HistoricoTarefa.status,
        models.HistoricoTarefa.id
    ).where(*filtro_desempenho_hist)
    
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
    desempenho_setorial.sort(key=lambda x: x['departamento'])

    # Ranking Equipe
    ranking_raw = db.query(
        subq.c.responsavel,
        subq.c.departamento,
        func.count(subq.c.id).label('total'),
        func.sum(case((subq.c.status == 'ENTREGUE', 1), else_=0)).label('entregues')
    ).group_by(subq.c.responsavel, subq.c.departamento).all()

    equipes_db = db.query(models.Equipe).filter(models.Equipe.tenant_id == current_user.tenant_id).all()
    email_to_equipe = {}
    dep_to_equipe = {}
    for eq in equipes_db:
        if eq.departamento not in dep_to_equipe:
            dep_to_equipe[eq.departamento] = eq.nome
        for m in eq.membros:
            if m.usuario and m.usuario.email:
                email_to_equipe[m.usuario.email.lower()] = eq.nome

    ranking_equipe_dict = {}
    for r in ranking_raw:
        if not r.responsavel: continue
        total_resp = r.total or 0
        entregues_resp = r.entregues or 0
        if total_resp == 0: continue
        
        primeiro_email = r.responsavel.split(',')[0].strip().lower()
        team_name = None
        if primeiro_email in email_to_equipe:
            team_name = email_to_equipe[primeiro_email]
        elif r.departamento in dep_to_equipe:
            team_name = dep_to_equipe[r.departamento]
        else:
            # Fallback legacy
            team_name = r.responsavel.split('@')[0].capitalize()

        if team_name not in ranking_equipe_dict:
            ranking_equipe_dict[team_name] = {"total": 0, "entregues": 0}
        
        ranking_equipe_dict[team_name]["total"] += total_resp
        ranking_equipe_dict[team_name]["entregues"] += entregues_resp

    ranking_equipe = []
    for team, data in ranking_equipe_dict.items():
        percentual = int((data["entregues"] / data["total"] * 100)) if data["total"] > 0 else 0
        ranking_equipe.append({
            "responsavel": team,
            "total": data["total"],
            "entregues": data["entregues"],
            "percentual": percentual
        })
    ranking_equipe.sort(key=lambda x: x['responsavel'])

    return templates.TemplateResponse(request=request, name="base.html", context={
        "request": request,
        "user": current_user,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", ""),
        "pendentes": pendentes,
        "entregues": entregues,
        "atrasadas": atrasadas,
        "desempenho_setorial": desempenho_setorial,
        "ranking_equipe": ranking_equipe,
        "departamentos": departamentos_lista,
        "departamento_selecionado": departamento or 'TODOS',
        "periodos": periodos,
        "periodo_selecionado": periodo_selecionado,
        "tipo_pesquisa_selecionado": tipo_pesquisa
    })

@app.get("/api/badges")
async def get_badges(db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    from sqlalchemy import not_, or_
    from datetime import datetime, timedelta, date
    
    revisoes = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'REVISAO'
    ).count()

    solicitacoes = db.query(models.Solicitacao).filter(
        models.Solicitacao.tenant_id == current_user.tenant_id,
        models.Solicitacao.status == 'PENDENTE'
    ).count()

    protocolos = db.query(models.Protocolo).filter(
        models.Protocolo.tenant_id == current_user.tenant_id,
        models.Protocolo.conf_recto == None,
        models.Protocolo.status_envio == 'ENVIADO',
        models.Protocolo.acao.ilike('%ENVIAR%'),
        or_(
            models.Protocolo.link_arquivo == None,
            not_(models.Protocolo.link_arquivo.startswith('SEM_ENVIO:'))
        )
    ).count()

    from datetime import timezone
    agora = datetime.now(timezone.utc)
    limite_online = agora - timedelta(seconds=90)
    hoje = date.today()
    
    online_count = db.query(models.FrequenciaAcesso).filter(
        models.FrequenciaAcesso.tenant_id == current_user.tenant_id,
        models.FrequenciaAcesso.data == hoje,
        models.FrequenciaAcesso.atualizado_em >= limite_online
    ).count()

    return {
        "revisoes": revisoes,
        "solicitacoes": solicitacoes,
        "protocolos": protocolos,
        "equipe": online_count
    }

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
