from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import datetime
import uuid
import logging

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.email_service import email_service
from app.core.storage_service import storage_service
from typing import List, Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


def gerar_protocolo() -> str:
    """Gera um código de protocolo único no formato PRT-YYYYMMDD-XXXX."""
    agora = datetime.datetime.now()
    return f"PRT-{agora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


def obter_email_cliente(db: Session, tenant_id: str, nome_cliente: str, departamento: str = None) -> str:
    """Busca o email do cliente com roteamento por departamento (igual ao sistema legado)."""
    cliente = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == tenant_id,
        models.Cliente.cliente == nome_cliente
    ).first()
    if not cliente:
        return ""
    
    # Roteamento por departamento (emails específicos por setor)
    if departamento:
        dep_upper = departamento.upper()
        if dep_upper == "FISCAL" and cliente.email_fiscal:
            return cliente.email_fiscal
        elif dep_upper == "CONTABIL" and cliente.email_contabil:
            return cliente.email_contabil
        elif dep_upper == "PESSOAL" and cliente.email_pessoal:
            return cliente.email_pessoal
        elif dep_upper == "SOCIETARIO" and cliente.email_societario:
            return cliente.email_societario
    
    # Fallback: email principal
    return cliente.email or ""


def registrar_protocolo(db: Session, tenant_id: str, tarefa, protocolo: str, 
                        email_destino: str, link_arquivo: str, responsavel: str,
                        status_envio: str = "ENVIADO") -> models.Protocolo:
    """Registra o protocolo de entrega no banco."""
    prot = models.Protocolo(
        tenant_id=tenant_id,
        data=datetime.datetime.now(datetime.timezone.utc),
        cliente=tarefa.cliente,
        protocolo=protocolo,
        id_tarefa=tarefa.id_controle,
        obrigacao=tarefa.obrigacao,
        email=email_destino,
        responsavel=responsavel,
        link_arquivo=link_arquivo,
        status_envio=status_envio,
        vcto_legal=tarefa.vencimento_legal,
        acao=tarefa.acao
    )
    db.add(prot)
    return prot


async def enviar_notificacao_entrega(tarefa, protocolo: str, email_destino: str, 
                                      responsavel_nome: str, justificativa: str = None,
                                      links_documentos: list = None):
    """Envia email de notificação ao cliente sobre entrega concluída."""
    assunto = f"[Protocolo {protocolo}] {tarefa.obrigacao} - {tarefa.cliente}"
    
    corpo = f"""
    <div style="font-family: 'Inter', 'Roboto', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 20px;">
        <div style="background: #1C3051; color: white; padding: 30px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 18px; letter-spacing: 1px;">JANIO PONTES CONTABILIDADE</h1>
            <p style="margin: 8px 0 0; opacity: 0.8; font-size: 12px; font-weight: bold; text-transform: uppercase;">Notificação de Entrega</p>
        </div>
        <div style="background: white; padding: 30px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none;">
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Prezado(a),</p>
            <p style="color: #334155; font-size: 14px; margin: 0 0 20px;">Informamos que a obrigação abaixo foi processada com sucesso:</p>
            <table style="width: 100%; border-collapse: collapse; margin: 0 0 20px;">
                <tr>
                    <td style="padding: 10px; background: #f1f5f9; border-radius: 8px 0 0 0; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Cliente</td>
                    <td style="padding: 10px; background: #f1f5f9; border-radius: 0 8px 0 0; font-size: 14px; font-weight: bold; color: #1C3051;">{tarefa.cliente}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Obrigação</td>
                    <td style="padding: 10px; font-size: 14px; font-weight: bold; color: #1C3051;">{tarefa.obrigacao}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f1f5f9; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Competência</td>
                    <td style="padding: 10px; background: #f1f5f9; font-size: 14px; color: #334155;">{tarefa.mes_ano}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Protocolo</td>
                    <td style="padding: 10px; font-size: 14px; font-weight: bold; color: #6366f1;">{protocolo}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f1f5f9; font-size: 12px; font-weight: bold; color: #64748b; text-transform: uppercase;">Vencimento Legal</td>
                    <td style="padding: 10px; background: #f1f5f9; font-size: 14px; color: #334155;">{tarefa.vencimento_legal.strftime('%d/%m/%Y') if tarefa.vencimento_legal else '—'}</td>
                </tr>
            </table>
    """
    
    # Botões de acesso aos documentos anexos (destaque visual)
    if links_documentos:
        corpo += """<div style="text-align: center; margin: 25px 0;">"""
        for i, link in enumerate(links_documentos):
            label = f"Acessar Documento {i+1}" if len(links_documentos) > 1 else "Acessar Documento"
            corpo += f"""
                <p style="margin: 8px 0;"><a href="{link}" style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;">{label}</a></p>
            """
        corpo += """</div>"""

    if justificativa:
        corpo += f"""
            <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 15px; margin: 0 0 20px;">
                <p style="margin: 0; font-size: 12px; font-weight: bold; color: #92400e; text-transform: uppercase;">Observação</p>
                <p style="margin: 8px 0 0; font-size: 13px; color: #78350f;">{justificativa}</p>
            </div>
        """
    
    corpo += f"""
            <div style="margin-top: 30px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                <p style="color: #64748b; font-size: 12px; margin: 0; font-weight: bold;">Sistema Gestor de Tarefas - NCE (Núcleo de Consultoria Estratégica)</p>
                <p style="color: #94a3b8; font-size: 10px; margin: 5px 0 0;">Monitoramento legal de abertura de mensagem.</p>
                <p style="color: #cbd5e1; font-size: 9px; margin: 15px 0 0;">Processado por {responsavel_nome} — {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
        </div>
    </div>
    """
    
    await email_service.enviar_email(email_destino, assunto, corpo)


# ==================== ENDPOINTS ====================

@router.get("/revisoes", response_class=HTMLResponse)
async def list_revisoes(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)
        
    revisoes = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'REVISAO'
    ).order_by(models.Tarefa.vencimento.asc()).all()
    
    return templates.TemplateResponse(request=request, name="revisoes.html", context={
        "request": request,
        "user": current_user,
        "revisoes": revisoes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.get("/tarefas", response_class=HTMLResponse)
async def list_tarefas(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    tarefas = db.query(models.Tarefa).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['PENDENTE', 'ATRASADO'])
    ).order_by(models.Tarefa.vencimento.asc()).limit(200).all()
    
    clientes = db.query(models.Cliente).filter(models.Cliente.tenant_id == current_user.tenant_id, models.Cliente.status == 'ATIVO').order_by(models.Cliente.cliente).all()
    usuarios = db.query(models.Usuario).filter(models.Usuario.tenant_id == current_user.tenant_id, models.Usuario.ativo == True).all()
    
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


@router.post("/tarefas/{tarefa_id}/finalizar", response_class=JSONResponse)
async def finalizar_tarefa(
    request: Request,
    tarefa_id: str,
    arquivos: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    """Motor de Ação principal — processa a finalização da tarefa conforme tipo de ação."""
    form = await request.form()
    justificativa = form.get("justificativa", "")
    mensagem_comunicar = form.get("mensagem_comunicar", "")
    
    # Tratamento para arquivos caso venham pelo form
    # O FastAPI costuma popular `arquivos` direto pelo parâmetro, mas às vezes o formulário é lido por request.form()
    # Vamos garantir a extração dos arquivos:
    lista_arquivos = form.getlist("arquivos") if "arquivos" in form else (arquivos or [])
    
    tarefa = db.query(models.Tarefa).filter(
        models.Tarefa.id == tarefa_id,
        models.Tarefa.tenant_id == current_user.tenant_id
    ).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    acao = (tarefa.acao or "ENVIAR").upper().strip()
    protocolo = gerar_protocolo()
    email_destino = obter_email_cliente(db, current_user.tenant_id, tarefa.cliente, tarefa.departamento)
    
    # Verificar se a regra de obrigação exige revisão (Coluna M = 'S')
    regra = db.query(models.RegraObrigacao).filter(
        models.RegraObrigacao.tenant_id == current_user.tenant_id,
        models.RegraObrigacao.obrigacao == tarefa.obrigacao
    ).first()
    
    precisa_revisao = False
    if regra and regra.revisao and str(regra.revisao).strip().upper() == 'S':
        # Apenas USER precisa de revisão; ADMIN/MASTER já aprovam direto
        if current_user.nivel not in ['ADMIN', 'MASTER']:
            precisa_revisao = True
    
    # Determinar status final
    status_final = 'REVISAO' if precisa_revisao else 'ENTREGUE'
    
    # Upload dos arquivos no Google Cloud Storage (GCS)
    links_gerados = []
    
    if lista_arquivos:
        for arq in lista_arquivos:
            if isinstance(arq, UploadFile) and arq.filename:
                try:
                    url = await storage_service.upload_file(arq, cliente_nome=tarefa.cliente)
                    if url and "ERRO" not in url:
                        links_gerados.append(url)
                except Exception as e:
                    logger.error(f"Falha ao subir arquivo {arq.filename}: {str(e)}")
                    
    # Descrição do protocolo para registro
    link_arquivo = " | ".join(links_gerados) if links_gerados else ""
    
    if "COMUNICAR" in acao:
        if mensagem_comunicar:
            link_arquivo += f" [COMUNICADO: {mensagem_comunicar}]"
        elif justificativa:
            link_arquivo += f" [SEM_COMUNICADO: {justificativa}]"
    elif "ARQUIVAR" in acao:
        link_arquivo += f" [ARQUIVADO: {justificativa}]" if justificativa else " [ARQUIVADO]"
    elif "ENVIAR" in acao:
        if not links_gerados and justificativa:
            link_arquivo = f"[SEM_ENVIO: {justificativa}]"
        elif links_gerados and justificativa:
            link_arquivo += f" [NOTA: {justificativa}]"
    else:
        if not link_arquivo:
            link_arquivo = justificativa or "PROCESSADO"
            
    link_arquivo = link_arquivo.strip()
    
    # Atualiza a tarefa
    tarefa.status = status_final
    tarefa.protocolo = protocolo
    
    # Registra protocolo
    registrar_protocolo(
        db, current_user.tenant_id, tarefa, protocolo,
        email_destino, link_arquivo, current_user.nome,
        status_envio="REVISAO" if precisa_revisao else "ENVIADO"
    )
    
    # Só envia email e arquiva se NÃO for revisão
    if not precisa_revisao:
        # Envia notificação por email conforme o tipo de ação
        try:
            if email_destino and "ARQUIVAR" not in acao:
                # Para ação ENVIAR: só envia e-mail se houver documentos anexados
                # Para ação COMUNICAR: sempre envia (é uma mensagem, não um documento)
                deve_enviar = True
                if "ENVIAR" in acao and not links_gerados:
                    deve_enviar = False  # Sem arquivo = sem envio ao cliente
                
                if deve_enviar:
                    msg_texto = mensagem_comunicar if "COMUNICAR" in acao else justificativa
                    
                    await enviar_notificacao_entrega(
                        tarefa, protocolo, email_destino, 
                        current_user.nome,
                        justificativa=msg_texto if msg_texto else None,
                        links_documentos=links_gerados if links_gerados else None
                    )
                    logger.info(f"[ENTREGA] {tarefa.obrigacao} ({tarefa.cliente}) -> {email_destino} | Proto: {protocolo}")
                else:
                    logger.info(f"[SEM ENVIO] {tarefa.obrigacao} ({tarefa.cliente}) — Finalizada com justificativa, sem arquivo. E-mail não enviado.")
        except Exception as e:
            logger.error(f"[EMAIL ERRO] Tarefa finalizada mas email falhou: {str(e)}")
        
        # Arquiva no histórico
        historico = models.HistoricoTarefa(
            tenant_id=current_user.tenant_id,
            mes_ano=tarefa.mes_ano,
            cliente=tarefa.cliente,
            obrigacao=tarefa.obrigacao,
            vencimento=tarefa.vencimento,
            departamento=tarefa.departamento,
            status="ENTREGUE",
            protocolo=protocolo,
            acao=tarefa.acao,
            responsavel=current_user.nome,
            id_controle=str(uuid.uuid4()),
            vencimento_legal=tarefa.vencimento_legal
        )
        db.add(historico)
    
    db.commit()
    
    return JSONResponse(content={
        "success": True,
        "protocolo": protocolo,
        "status": status_final,
        "acao": acao,
        "email_destino": email_destino or "N/A",
        "message": f"Tarefa movida para REVISÃO (aguardando aprovação)." if precisa_revisao 
                   else f"Tarefa concluída com protocolo {protocolo}."
    })


@router.post("/tarefas/{tarefa_id}/aprovar", response_class=HTMLResponse)
async def aprovar_revisao(
    request: Request,
    tarefa_id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        raise HTTPException(status_code=403, detail="Apenas administradores podem aprovar tarefas.")

    tarefa = db.query(models.Tarefa).filter(
        models.Tarefa.id == tarefa_id,
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'REVISAO'
    ).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa em revisão não encontrada")
    
    # Ao aprovar, dispara o e-mail que ficou pendente
    email_destino = obter_email_cliente(db, current_user.tenant_id, tarefa.cliente, tarefa.departamento)
    acao = (tarefa.acao or "").upper()
    
    try:
        if email_destino and "ARQUIVAR" not in acao:
            await enviar_notificacao_entrega(
                tarefa, tarefa.protocolo or "N/A", email_destino,
                current_user.nome
            )
    except Exception as e:
        logger.error(f"[EMAIL ERRO APROVACAO] {str(e)}")
        
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
        responsavel=tarefa.responsavel,
        id_controle=str(uuid.uuid4()),
        vencimento_legal=tarefa.vencimento_legal
    )
    db.add(historico)
    db.commit()
    
    return ""

@router.post("/tarefas/{tarefa_id}/rejeitar", response_class=HTMLResponse)
async def rejeitar_revisao(
    request: Request,
    tarefa_id: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        raise HTTPException(status_code=403, detail="Apenas administradores podem rejeitar tarefas.")

    tarefa = db.query(models.Tarefa).filter(
        models.Tarefa.id == tarefa_id,
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'REVISAO'
    ).first()
    
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa em revisão não encontrada")
        
    # Devolve a tarefa para o funcionário refazer
    if tarefa.vencimento and tarefa.vencimento < datetime.date.today():
        tarefa.status = 'ATRASADO'
    else:
        tarefa.status = 'PENDENTE'
        
    db.commit()
    return ""
