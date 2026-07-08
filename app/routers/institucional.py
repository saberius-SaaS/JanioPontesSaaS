from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging

from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/contato")
async def enviar_contato(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(...),
    mensagem: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Recebe mensagens do formulario de contato do site institucional.
    Dispara logs e pode ser integrado com e-mail ou banco futuramente.
    """
    logger.info(f"[SITE CONTATO] Nome: {nome} | E-mail: {email} | Telefone: {telefone} | Mensagem: {mensagem}")
    
    # OPCIONAL: Enviar email interno avisando do contato
    from app.core.email_service import email_service
    
    assunto = f"Novo Contato via Site - {nome}"
    corpo_html = f"""
    <h3>Novo contato recebido pelo site institucional:</h3>
    <p><b>Nome:</b> {nome}</p>
    <p><b>E-mail:</b> {email}</p>
    <p><b>Telefone:</b> {telefone}</p>
    <p><b>Mensagem:</b><br>{mensagem}</p>
    """
    
    # Envia para o email do administrador
    await email_service.enviar_email(
        para="janiopontes@janiopontes.com.br",
        assunto=assunto,
        corpo_html=corpo_html
    )
    
    # Retorna uma resposta amigavel de sucesso
    return JSONResponse(content={"ok": True, "message": "Mensagem enviada com sucesso! Entraremos em contato em breve."})
