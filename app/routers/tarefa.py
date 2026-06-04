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
    
    # Botão de acesso único via Portal do Cliente (Link Mágico)
    if links_documentos:
        magic_link = f"https://app.janiopontes.com.br/acesso/{protocolo}"
        corpo += f"""
        <div style="text-align: center; margin: 25px 0;">
            <p style="margin: 8px 0;"><a href="{magic_link}" style="display: inline-block; background-color: #6366f1; color: white; padding: 14px 28px; text-decoration: none; font-weight: bold; border-radius: 8px; text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">Acessar no Portal do Cliente</a></p>
            <p style="color: #64748b; font-size: 11px; margin-top: 12px;">O link acima concede acesso seguro aos arquivos desta entrega.</p>
        </div>
        """

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


def processar_workflow(db: Session, tarefa: models.Tarefa):
    """Verifica se a tarefa concluída é gatilho de um workflow e cria a próxima fase."""
    regras_wf = db.query(models.Workflow).filter(
        models.Workflow.tenant_id == tarefa.tenant_id,
        models.Workflow.fase_atual == tarefa.obrigacao
    ).all()
    
    for wf in regras_wf:
        novo_vcto = datetime.date.today() + datetime.timedelta(days=wf.dias or 0)
        
        nova_tarefa = models.Tarefa(
            tenant_id=tarefa.tenant_id,
            mes_ano=tarefa.mes_ano,
            cliente=tarefa.cliente,
            obrigacao=wf.proxima_fase,
            vencimento=novo_vcto,
            departamento=wf.departamento or tarefa.departamento,
            status="PENDENTE",
            acao=wf.acao or "ENVIAR",
            responsavel=wf.responsavel_padrao or tarefa.responsavel,
            id_controle=f"WF-{uuid.uuid4().hex[:8]}",
            nivel=tarefa.nivel
        )
        db.add(nova_tarefa)
        logger.info(f"[WORKFLOW] Nova tarefa gerada automaticamente: {nova_tarefa.obrigacao} ({nova_tarefa.cliente})")


# ==================== ENDPOINTS ====================

@router.get("/revisoes", response_class=HTMLResponse)
async def list_revisoes(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    if current_user.nivel not in ['ADMIN', 'MASTER']:
        return RedirectResponse(url="/", status_code=303)
        
    import re
    revisoes_query = db.query(models.Tarefa, models.Protocolo.link_arquivo).outerjoin(
        models.Protocolo,
        (models.Protocolo.tenant_id == models.Tarefa.tenant_id) &
        (models.Protocolo.protocolo == models.Tarefa.protocolo)
    ).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status == 'REVISAO'
    ).order_by(models.Tarefa.vencimento.asc()).all()
    
    revisoes = []
    for t, link in revisoes_query:
        link = link or ""
        # Extrair observações/justificativas entre colchetes
        obs_match = re.search(r'\[(.*?)\]', link)
        t.justificativa = obs_match.group(1) if obs_match else ""
        
        # Extrair URLs
        base_link = re.sub(r'\[.*?\]', '', link).strip()
        t.arquivos_anexos = [l.strip() for l in base_link.split(' | ') if l.strip().startswith('http')]
        
        revisoes.append(t)
    
    return templates.TemplateResponse(request=request, name="revisoes.html", context={
        "request": request,
        "user": current_user,
        "revisoes": revisoes,
        "chatwoot_token": getattr(request.state, "chatwoot_token", ""),
        "chatwoot_base_url": getattr(request.state, "chatwoot_base_url", "")
    })

@router.get("/tarefas", response_class=HTMLResponse)
async def list_tarefas(request: Request, db: Session = Depends(get_db), current_user: models.Usuario = Depends(require_login)):
    tarefas_raw = db.query(models.Tarefa, models.RegraObrigacao.revisao).outerjoin(
        models.RegraObrigacao,
        (models.RegraObrigacao.tenant_id == models.Tarefa.tenant_id) &
        (models.RegraObrigacao.obrigacao == models.Tarefa.obrigacao)
    ).filter(
        models.Tarefa.tenant_id == current_user.tenant_id,
        models.Tarefa.status.in_(['PENDENTE', 'ATRASADO'])
    ).order_by(models.Tarefa.vencimento.asc()).limit(200).all()
    
    tarefas = []
    for t, rev in tarefas_raw:
        # Mesmo flag do backend
        is_revisao = (rev and str(rev).strip().upper() == 'S')
        t.precisa_revisao_flag = 'S' if is_revisao else 'N'
        tarefas.append(t)
    
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
    complemento: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    if complemento:
        obrigacao_final = f"{obrigacao} - {complemento}"
    else:
        obrigacao_final = obrigacao

    nova_tarefa = models.Tarefa(
        tenant_id=current_user.tenant_id,
        mes_ano=datetime.datetime.strptime(vencimento, '%Y-%m-%d').strftime('%m/%Y'),
        cliente=cliente,
        obrigacao=obrigacao_final,
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
    
    # === DEBUG: Diagnóstico de upload ===
    logger.warning(f"[DEBUG UPLOAD] tarefa_id={tarefa_id}")
    logger.warning(f"[DEBUG UPLOAD] form keys: {list(form.keys())}")
    logger.warning(f"[DEBUG UPLOAD] 'arquivos' in form: {'arquivos' in form}")
    logger.warning(f"[DEBUG UPLOAD] lista_arquivos count: {len(lista_arquivos)}")
    for i, arq in enumerate(lista_arquivos):
        is_upload = isinstance(arq, UploadFile)
        fname = getattr(arq, 'filename', 'N/A')
        fsize = getattr(arq, 'size', 'N/A')
        logger.warning(f"[DEBUG UPLOAD] arquivo[{i}]: is_UploadFile={is_upload}, filename='{fname}', size={fsize}, type={type(arq).__name__}")
    
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
            # Duck-typing: form.getlist() retorna starlette.datastructures.UploadFile,
            # que NÃO é isinstance de fastapi.UploadFile. Usamos hasattr para aceitar ambos.
            fname = getattr(arq, 'filename', None)
            has_read = hasattr(arq, 'read')
            logger.warning(f"[DEBUG GCS] Processando: has_read={has_read}, filename='{fname}', type={type(arq).__name__}")
            if has_read and fname:
                try:
                    url = await storage_service.upload_file(arq, cliente_nome=tarefa.cliente)
                    logger.warning(f"[DEBUG GCS] Resultado upload: url='{url[:80] if url else 'None'}...'")
                    if url and "ERRO" not in url:
                        links_gerados.append(url)
                    else:
                        logger.error(f"[GCS FALHA] Upload retornou erro: {url}")
                except Exception as e:
                    logger.error(f"Falha ao subir arquivo {fname}: {str(e)}")
            else:
                logger.warning(f"[DEBUG GCS] Arquivo ignorado: has_read={has_read}, fname='{fname}'")
    else:
        logger.warning(f"[DEBUG GCS] lista_arquivos está vazia, nenhum upload tentado")
                    
    logger.warning(f"[DEBUG RESULTADO] links_gerados: {len(links_gerados)}")
    
    if precisa_revisao and not links_gerados:
        return JSONResponse(content={
            "success": False, 
            "message": "Esta tarefa exige revisão. É obrigatório anexar o arquivo/documento para o revisor."
        })
        
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
        logger.warning(f"[DEBUG EMAIL] acao={acao}, email_destino='{email_destino}', links_gerados={len(links_gerados)}")
        try:
            if email_destino and "ARQUIVAR" not in acao:
                # Para ação ENVIAR: só envia e-mail se houver documentos anexados
                # Para ação COMUNICAR: sempre envia (é uma mensagem, não um documento)
                deve_enviar = True
                if "ENVIAR" in acao and not links_gerados:
                    deve_enviar = False  # Sem arquivo = sem envio ao cliente
                
                logger.warning(f"[DEBUG EMAIL] deve_enviar={deve_enviar}")
                
                if deve_enviar:
                    msg_texto = mensagem_comunicar if "COMUNICAR" in acao else justificativa
                    
                    await enviar_notificacao_entrega(
                        tarefa, protocolo, email_destino, 
                        current_user.nome,
                        justificativa=msg_texto if msg_texto else None,
                        links_documentos=links_gerados if links_gerados else None
                    )
                    logger.warning(f"[ENTREGA] {tarefa.obrigacao} ({tarefa.cliente}) -> {email_destino} | Proto: {protocolo}")
                else:
                    logger.warning(f"[SEM ENVIO] {tarefa.obrigacao} ({tarefa.cliente}) — acao=ENVIAR mas links_gerados vazio. E-mail bloqueado.")
            else:
                logger.warning(f"[DEBUG EMAIL] Email NÃO enviado: email_destino='{email_destino}', acao contém ARQUIVAR={('ARQUIVAR' in acao)}")
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
        
        # Dispara workflow, se aplicável
        processar_workflow(db, tarefa)
    
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
    
    # Atualizar o status do Protocolo associado
    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.tenant_id == current_user.tenant_id,
        models.Protocolo.protocolo == tarefa.protocolo
    ).first()
    if protocolo:
        protocolo.status_envio = "ENVIADO"
    
    # Dispara workflow, se aplicável
    processar_workflow(db, tarefa)
    
    db.commit()
    
    return RedirectResponse(url="/revisoes", status_code=303)

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

    # Atualizar o status do Protocolo associado para REJEITADO
    protocolo = db.query(models.Protocolo).filter(
        models.Protocolo.tenant_id == current_user.tenant_id,
        models.Protocolo.protocolo == tarefa.protocolo
    ).first()
    if protocolo:
        protocolo.status_envio = "REJEITADO"
        
    # Devolve a tarefa para o funcionário refazer
    if tarefa.vencimento and tarefa.vencimento < datetime.date.today():
        tarefa.status = 'ATRASADO'
    else:
        tarefa.status = 'PENDENTE'
        
    tarefa.protocolo = None # Limpa o protocolo para gerar um novo na próxima entrega
        
    db.commit()
    return RedirectResponse(url="/revisoes", status_code=303)
