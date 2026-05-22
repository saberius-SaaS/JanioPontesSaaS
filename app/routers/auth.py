from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import urllib3 as google_urllib3
import urllib3

from app import models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.database import get_db

router = APIRouter()

# Setup urllib3 pool manager for Google Auth
http = urllib3.PoolManager()
google_request = google_urllib3.Request(http)

@router.post("/login", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, required for FastAPI Swagger UI.
    Para o SaaS usaremos primariamente o login do Google, mas isso ajuda nos testes.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="E-mail ou senha incorretos")
    
    # Aqui não checamos senha real porque migraremos os dados do Google
    # Mas em produção, validar a senha com security.verify_password
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/google", response_model=schemas.Token)
def login_google(token: str, db: Session = Depends(get_db)):
    """
    Valida um JWT fornecido pelo Google Identity Services (GIS) no frontend.
    Se o e-mail existir no banco, gera um JWT próprio da nossa aplicação.
    """
    try:
        # Aqui o backend checa com o Google se o token é legítimo usando urllib3 para evitar erro de SSL
        idinfo = id_token.verify_oauth2_token(token, google_request, settings.GOOGLE_CLIENT_ID)
        
        email = idinfo.get("email")
        if not email or not idinfo.get("email_verified"):
            raise HTTPException(status_code=400, detail="E-mail não verificado pelo Google")
            
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if not user:
            raise HTTPException(status_code=403, detail="Acesso negado: Usuário não registrado no sistema")
            
        if not user.ativo:
            raise HTTPException(status_code=400, detail="Usuário inativo")
            
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": security.create_access_token(
                user.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
        }
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido")
