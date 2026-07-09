from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import UUID
import datetime

from app import models
from app.database import get_db
from app.api.deps import require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def check_permission(user: models.Usuario):
    if user.nivel in ["ADMIN", "MASTER"]:
        return
    nomes_equipes = [eq.equipe.nome.upper() for eq in user.equipes]
    if not any("SOCIETARIO" in nome or "SOCIETÁRIO" in nome for nome in nomes_equipes):
        raise HTTPException(status_code=403, detail="Acesso restrito ao Societário e Admin.")

@router.get("/certificados", response_class=HTMLResponse)
async def list_certificados(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    
    certificados = db.query(models.CertificadoDigital).filter(
        models.CertificadoDigital.tenant_id == current_user.tenant_id
    ).order_by(models.CertificadoDigital.vencimento.asc()).all()
    
    # Atualiza o status dinamicamente para exibição
    hoje = datetime.date.today()
    for cert in certificados:
        if cert.vencimento < hoje:
            cert.status = "VENCIDO"
        elif (cert.vencimento - hoje).days <= 30:
            cert.status = "ALERTA"
        else:
            cert.status = "ATIVO"

    clientes = db.query(models.Cliente).filter(
        models.Cliente.tenant_id == current_user.tenant_id,
        models.Cliente.status == "ATIVO"
    ).order_by(models.Cliente.cliente).all()

    return templates.TemplateResponse(request, "certificados.html", {
        "user": current_user,
        "certificados": certificados,
        "clientes": clientes
    })

@router.post("/certificados", response_class=HTMLResponse)
async def create_certificado(
    request: Request,
    cliente_id: UUID = Form(...),
    tipo: str = Form(...),
    vencimento: str = Form(...),
    senha: str = Form(None),
    anotacao: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    
    try:
        dt_venc = datetime.datetime.strptime(vencimento, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida")

    # Verifica duplicidade
    existente = db.query(models.CertificadoDigital).filter(
        models.CertificadoDigital.tenant_id == current_user.tenant_id,
        models.CertificadoDigital.cliente_id == cliente_id,
        models.CertificadoDigital.tipo == tipo,
        models.CertificadoDigital.vencimento == dt_venc
    ).first()
    
    if existente:
        return HTMLResponse("<script>window.location.reload();</script>")

    novo_cert = models.CertificadoDigital(
        tenant_id=current_user.tenant_id,
        cliente_id=cliente_id,
        tipo=tipo,
        vencimento=dt_venc,
        senha=senha,
        status="ATIVO",
        anotacao=anotacao.strip() if anotacao else None
    )
    db.add(novo_cert)
    db.commit()

    # Redireciona de volta com HX-Refresh ou apenas response
    return HTMLResponse("<script>window.location.reload();</script>")

@router.delete("/certificados/{cert_id}", response_class=HTMLResponse)
async def delete_certificado(
    request: Request,
    cert_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    check_permission(current_user)
    obj = db.query(models.CertificadoDigital).filter(
        models.CertificadoDigital.id == cert_id,
        models.CertificadoDigital.tenant_id == current_user.tenant_id
    ).first()
    if obj:
        db.delete(obj)
        db.commit()
    return HTMLResponse("")

@router.get("/api/certificados/vencimentos")
async def get_vencimentos(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(require_login)
):
    # API para dashboard ou automação
    check_permission(current_user)
    
    hoje = datetime.date.today()
    limite = hoje + datetime.timedelta(days=30)
    
    certificados = db.query(models.CertificadoDigital).filter(
        models.CertificadoDigital.tenant_id == current_user.tenant_id,
        models.CertificadoDigital.vencimento <= limite
    ).order_by(models.CertificadoDigital.vencimento.asc()).all()
    
    resultados = []
    for cert in certificados:
        resultados.append({
            "id": str(cert.id),
            "cliente": cert.cliente.cliente if cert.cliente else "Desconhecido",
            "tipo": cert.tipo,
            "vencimento": cert.vencimento.strftime('%d/%m/%Y'),
            "dias_restantes": (cert.vencimento - hoje).days,
            "status": "VENCIDO" if cert.vencimento < hoje else "ALERTA"
        })
        
    return JSONResponse(content={"data": resultados})
