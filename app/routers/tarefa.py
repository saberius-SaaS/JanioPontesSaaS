from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import datetime
import uuid

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/tarefas", response_class=HTMLResponse)
async def list_tarefas(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    tarefas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['PENDENTE', 'ATRASADO'])
    ).order_by(models.Tarefa.vencimento.asc()).limit(200).all()
    
    clientes = db.query(models.Cliente).filter(models.Cliente.tenant_id == current_user.tenant_id, models.Cliente.status == 'ATIVO').order_by(models.Cliente.cliente).all()
    usuarios = db.query(models.Usuario).filter(models.Usuario.tenant_id == current_user.tenant_id, models.Usuario.status == 'ATIVO').all()
    
    # Tipos de tarefas avulsas (tabela dedicada)
    tipos_raw = db.query(models.TipoTarefaAvulsa).filter(
        models.TipoTarefaAvulsa.tenant_id == current_user.tenant_id,
        models.TipoTarefaAvulsa.status == 'ATIVO'
    ).order_by(models.TipoTarefaAvulsa.nome).all()
    tipos_avulsa = [t.nome for t in tipos_raw]
    
    # Departamentos disponíveis
    deptos_raw = db.query(models.RegraObrigacao.departamento).filter(
        models.RegraObrigacao.tenant_id == current_user.tenant_id,
        models.RegraObrigacao.departamento != None
    ).distinct().all()
    departamentos = sorted(set(d[0] for d in deptos_raw if d[0]))
    
    return templates.TemplateResponse(request=request, name="tarefas.html", context={
        "request": request,
        "user": current_user,
        "tarefas": tarefas,
        "clientes": clientes,
        "usuarios": usuarios,
        "tipos_avulsa": tipos_avulsa,
        "departamentos": departamentos,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })


@router.post("/tarefas", response_class=HTMLResponse)
async def create_tarefa_avulsa(
    request: Request,
    cliente: str = Form(...),
    obrigacao: str = Form(...),
    vencimento: str = Form(...),
    departamento: str = Form("AVULSA"),
    responsavel: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    nova_tarefa = models.Tarefa(
        tenant_id=current_user.tenant_id,
        mes_ano=datetime.datetime.strptime(vencimento, '%Y-%m-%d').strftime('%m/%Y'),
        cliente=cliente,
        obrigacao=obrigacao,
        vencimento=datetime.datetime.strptime(vencimento, '%Y-%m-%d').date(),
        departamento=departamento,
        status="PENDENTE",
        acao="ENVIAR",
        responsavel=responsavel,
        id_controle=f"AVULSA-{uuid.uuid4().hex[:8]}",
        nivel=1
    )
    db.add(nova_tarefa)
    db.commit()
    return RedirectResponse(url="/tarefas", status_code=303)

@router.post("/tarefas/{tarefa_id}/finalizar", response_class=HTMLResponse)
async def finalizar_tarefa(
    request: Request,
    tarefa_id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    from fastapi import HTTPException
    tarefa = db.query(models.Tarefa).filter(
        models.Tarefa.id == tarefa_id,
        models.Tarefa.tenant_id == current_user.tenant_id
    ).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
    tarefa.status = 'ENTREGUE'
    
    historico = models.HistoricoTarefa(
        tenant_id=current_user.tenant_id,
        mes_ano=tarefa.mes_ano,
        cliente=tarefa.cliente,
        obrigacao=tarefa.obrigacao,
        vencimento=tarefa.vencimento,
        departamento=tarefa.departamento,
        status="ENTREGUE",
        protocolo=tarefa.protocolo,
        acao=tarefa.acao,
        responsavel=current_user.nome,
        id_controle=str(uuid.uuid4()),
        vencimento_legal=tarefa.vencimento_legal
    )
    db.add(historico)
    db.commit()
    
    return ""
