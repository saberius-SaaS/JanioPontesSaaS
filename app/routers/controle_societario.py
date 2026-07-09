from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID
import datetime

from app import models
from app.database import get_db
from app.api.deps import require_login
from app.core.storage_service import storage_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def check_permission(user: models.Usuario):
    if user.nivel in ["ADMIN", "MASTER"]:
        return
    nomes_equipes = [eq.equipe.nome.upper() for eq in user.equipes]
    if not any("SOCIETARIO" in nome or "SOCIETÁRIO" in nome for nome in nomes_equipes):
        raise HTTPException(status_code=403, detail="Acesso restrito ao Societário e Admin.")

def get_model_and_template(tipo_servico: str):
    if tipo_servico == "licencas":
        return models.LicencaLocalizacao, "licenca_localizacao.html", "Licença/Localização"
    elif tipo_servico == "alvaras":
        return models.AlvaraSanitario, "alvara_sanitario.html", "Alvará Sanitário"
    elif tipo_servico == "avcbs":
        return models.AVCB, "avcb.html", "AVCB"
    elif tipo_servico == "inscricoes":
        return models.InscricaoMunicipal, "inscricao_municipal.html", "Inscrição Municipal"
    else:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")

@router.get("/societario/{tipo_servico}", response_class=HTMLResponse)
async def list_societario(
    tipo_servico: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    Model, template_name, title = get_model_and_template(tipo_servico)
    
    documentos = db.query(Model).filter(
        Model.tenant_id == current_user.tenant_id
    ).order_by(Model.vencimento.asc().nullslast()).all()
    
    hoje = datetime.date.today()
    for doc in documentos:
        if doc.vencimento is None:
            doc.status = "INDETERMINADO"
        elif doc.vencimento < hoje:
            doc.status = "VENCIDO"
        elif (doc.vencimento - hoje).days <= 30:
            doc.status = "ALERTA"
        else:
            doc.status = "ATIVO"

    clientes = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == current_user.tenant_id,
        models.Cliente.status == "ATIVO"
    ).order_by(models.Cliente.cliente).all()

    return templates.TemplateResponse(request, template_name, {
        "user": current_user,
        "documentos": documentos,
        "clientes": clientes,
        "servico_atual": tipo_servico
    })

@router.post("/societario/{tipo_servico}", response_class=HTMLResponse)
async def create_societario(
    tipo_servico: str,
    request: Request,
    cliente_id: UUID = Form(...),
    vencimento: str = Form(""),
    anotacao: str = Form(""),
    doc_id: str = Form(""),
    arquivo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    Model, _, _ = get_model_and_template(tipo_servico)
    
    dt_venc = None
    if vencimento and vencimento.strip():
        try:
            dt_venc = datetime.datetime.strptime(vencimento.strip(), '%Y-%m-%d').date()
        except ValueError:
            return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Erro', 'Data inválida.', 'error');}else{alert('Data inválida');}</script>")

    arquivo_url = None
    if arquivo and arquivo.filename:
        cliente_db = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
        cliente_nome = cliente_db.cliente if cliente_db else "Desconhecido"
        arquivo_url = await storage_service.upload_file(arquivo, cliente_nome=cliente_nome)

    if doc_id:
        doc = db.query(Model).filter(
            Model.id == doc_id,
            Model.tenant_id == current_user.tenant_id
        ).first()
        
        if not doc:
            return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Erro', 'Documento não encontrado.', 'error');}</script>")
            
        doc.cliente_id = cliente_id
        doc.vencimento = dt_venc
        doc.status = "INDETERMINADO" if dt_venc is None else "ATIVO"
        doc.anotacao = anotacao.strip() if anotacao else None
        if arquivo_url:
            doc.arquivo_url = arquivo_url
            
        db.commit()
        return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Sucesso', 'Atualizado com sucesso.', 'success'); setTimeout(() => window.location.reload(), 1000);}else{window.location.reload();}</script>")
    else:
        # Bloquear duplicidade de registros (especialmente indeterminado)
        query_dup = db.query(Model).filter(
            Model.cliente_id == cliente_id,
            Model.tenant_id == current_user.tenant_id
        )
        if dt_venc is None:
            query_dup = query_dup.filter(Model.vencimento == None, Model.status == "INDETERMINADO")
        else:
            query_dup = query_dup.filter(Model.vencimento == dt_venc)
            
        if query_dup.first():
            return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Erro', 'Já existe um documento com este prazo para o cliente selecionado.', 'error'); setTimeout(() => window.location.reload(), 1500);}else{alert('Já existe um documento cadastrado.'); window.location.reload();}</script>")

        novo_doc = Model(
            tenant_id=current_user.tenant_id,
            cliente_id=cliente_id,
            vencimento=dt_venc,
            status="INDETERMINADO" if dt_venc is None else "ATIVO",
            arquivo_url=arquivo_url,
            anotacao=anotacao.strip() if anotacao else None
        )
        db.add(novo_doc)
        db.commit()

        return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Sucesso', 'Cadastrado com sucesso.', 'success'); setTimeout(() => window.location.reload(), 1000);}else{window.location.reload();}</script>")

    return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Sucesso', 'Cadastrado com sucesso.', 'success'); setTimeout(() => window.location.reload(), 1000);}else{window.location.reload();}</script>")

@router.delete("/societario/{tipo_servico}/{doc_id}", response_class=HTMLResponse)
async def delete_societario(
    tipo_servico: str,
    doc_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    Model, _, _ = get_model_and_template(tipo_servico)
    
    obj = db.query(Model).filter(
        Model.id == doc_id,
        Model.tenant_id == current_user.tenant_id
    ).first()
    if obj:
        db.delete(obj)
        db.commit()
        return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Sucesso', 'Excluído com sucesso.', 'success'); setTimeout(() => window.location.reload(), 1000);}else{window.location.reload();}</script>")
    return HTMLResponse("<script>if(typeof showToast === 'function'){showToast('Erro', 'Documento não encontrado.', 'error');}</script>")
