import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, Header, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.database import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

SCHEDULER_API_KEY = os.getenv("SCHEDULER_API_KEY", "dev-scheduler-key-change-me")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.Usuario:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não foi possível validar as credenciais",
            )
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não foi possível validar as credenciais",
        )
        
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    # ATIVAÇÃO DO ROW-LEVEL SECURITY (RLS)
    try:
        db.execute(text(f"SET LOCAL app.current_tenant = '{str(user.tenant_id)}';"))
        db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
    except Exception:
        # SQLite em ambiente de teste não suporta SET LOCAL
        pass
    
    return user


def get_current_active_user(
    current_user: models.Usuario = Depends(get_current_user),
) -> models.Usuario:
    if not current_user.ativo:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user


def get_user_from_cookie(request: Request, db: Session = Depends(get_db)) -> Optional[models.Usuario]:
    """
    Extrai o JWT do cookie '__session' para páginas SSR (Jinja2).
    Retorna o usuário ou None (para redirecionar ao login).
    """
    token = request.cookies.get("__session")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        # Bypass RLS para buscar o usuário pelo ID do JWT (ainda não temos tenant_id)
        try:
            db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        except Exception:
            pass
        user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
        if user:
            # Agora que temos o tenant, ativa o isolamento correto para as queries seguintes
            try:
                db.execute(text(f"SET LOCAL app.current_tenant = '{str(user.tenant_id)}';"))
                db.execute(text("SET LOCAL app.bypass_rls = 'off';"))
            except Exception:
                pass
        return user
    except Exception:
        return None


def require_login(request: Request, db: Session = Depends(get_db)) -> models.Usuario:
    """
    Dependency para rotas SSR que exigem login.
    Redireciona para /login se não autenticado.
    """
    user = get_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    if not user.ativo:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return user


# ==========================================
# Autenticação do Portal do Cliente
# ==========================================

def get_cliente_from_cookie(request: Request) -> Optional[dict]:
    """
    Extrai o JWT do cookie '__session' para o Portal do Cliente.
    Retorna um dicionário com tenant_id e cliente_nome, ou None.
    """
    token = request.cookies.get("__session")
    if not token:
        return None
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        cliente_nome = payload.get("cliente")
        tenant_id = payload.get("tenant_id")
        if not cliente_nome or not tenant_id:
            return None
        return {"cliente": cliente_nome, "tenant_id": tenant_id}
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Erro ao decodificar token do cliente: {e}")
        return None

def require_cliente_login(request: Request):
    """
    Exige que o cliente esteja logado para acessar rotas do /portal.
    Se não estiver, redireciona para uma tela de aviso ou login.
    """
    cliente_data = get_cliente_from_cookie(request)
    if not cliente_data:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/portal/login"}
        )
    return cliente_data


def require_admin(current_user: models.Usuario = Depends(require_login)) -> models.Usuario:
    """
    Dependency para rotas SSR que exigem nível ADMIN.
    """
    if current_user.nivel != "ADMIN" and current_user.nivel != "MASTER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito apenas a administradores."
        )
    return current_user



def verify_scheduler_key(x_scheduler_key: str = Header(None)) -> bool:
    """
    Protege as rotas de CRON/Scheduler com uma chave secreta.
    O Cloud Scheduler envia este header em cada chamada.
    """
    if x_scheduler_key != SCHEDULER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de agendamento inválida"
        )
    return True
