"""
Módulo de Autenticação — Janio Pontes SaaS
Fluxo: Google Identity Services (One Tap) → validação backend → JWT em cookie seguro.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from google.oauth2 import id_token
from google.auth.transport import urllib3 as google_urllib3
import urllib3

from app import models
from app.core import security
from app.core.config import settings
from app.database import get_db

router = APIRouter()

# Setup urllib3 pool manager for Google token verification
_http = urllib3.PoolManager()
google_request = google_urllib3.Request(_http)

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID


from app.core.limiter import limiter

# ─────────────────────────────────────────────
# GET /login — Tela de login com Google OAuth
# ─────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
@limiter.limit("10/minute")
def login_page(request: Request):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login — Janio Pontes SaaS</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; }}
            .gradient-bg {{
                background: linear-gradient(135deg, #1C3051 0%, #1e3a5f 50%, #312e81 100%);
            }}
            .glass-card {{
                background: rgba(255,255,255,0.97);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255,255,255,0.2);
            }}
            .logo-glow {{
                filter: drop-shadow(0 0 20px rgba(99,102,241,0.4));
            }}
        </style>
    </head>
    <body class="gradient-bg min-h-screen flex items-center justify-center p-4">

        <div class="absolute inset-0 overflow-hidden pointer-events-none">
            <div class="absolute top-1/4 right-1/4 w-64 h-64 bg-indigo-500 rounded-full opacity-5 blur-3xl"></div>
            <div class="absolute bottom-1/3 left-1/4 w-96 h-96 bg-purple-500 rounded-full opacity-5 blur-3xl"></div>
        </div>

        <div class="glass-card rounded-2xl shadow-2xl p-10 w-full max-w-md relative z-10">

            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center mb-4">
                    <img src="/static/logo.jpg" class="h-24 w-auto object-contain drop-shadow-xl rounded-lg logo-glow" alt="Jânio Pontes Logo">
                </div>
                <h1 class="text-2xl font-extrabold text-gray-900 tracking-tight">Janio Pontes SaaS</h1>
                <p class="text-gray-500 text-sm mt-1">Plataforma de Gestão Contábil</p>
            </div>

            <div class="border-t border-gray-100 my-6"></div>

            <p class="text-center text-sm text-gray-500 mb-6">
                Acesse com a sua conta Google corporativa
            </p>

            <div id="g_id_onload"
                data-client_id="{GOOGLE_CLIENT_ID}"
                data-callback="handleGoogleSignIn"
                data-auto_prompt="false">
            </div>

            <div class="flex justify-center">
                <div class="g_id_signin"
                    data-type="standard"
                    data-size="large"
                    data-theme="outline"
                    data-text="signin_with"
                    data-shape="rectangular"
                    data-logo_alignment="left"
                    data-width="320">
                </div>
            </div>

            <div id="error-msg" class="hidden mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm text-center"></div>
            <div id="loading-msg" class="hidden mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-700 text-sm text-center">
                ⏳ Verificando credenciais...
            </div>

            <div class="mt-8 pt-6 border-t border-gray-100 text-center">
                <p class="text-xs text-gray-400">
                    Acesso restrito a usuários autorizados.<br>
                    Em caso de dificuldades, contate o administrador.
                </p>
            </div>
        </div>

        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <script>
            async function handleGoogleSignIn(response) {{
                document.getElementById('error-msg').classList.add('hidden');
                document.getElementById('loading-msg').classList.remove('hidden');
                try {{
                    const res = await fetch('/google', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                        body: 'credential=' + encodeURIComponent(response.credential),
                        redirect: 'manual'
                    }});
                    if (res.ok || res.type === 'opaqueredirect' || res.status === 0) {{
                        window.location.href = '/';
                        return;
                    }} else {{
                        const data = await res.json().catch(() => ({{detail: 'Erro desconhecido'}}));
                        document.getElementById('loading-msg').classList.add('hidden');
                        document.getElementById('error-msg').textContent = '❌ ' + (data.detail || 'Acesso negado.');
                        document.getElementById('error-msg').classList.remove('hidden');
                    }}
                }} catch (e) {{
                    document.getElementById('loading-msg').classList.add('hidden');
                    document.getElementById('error-msg').textContent = '❌ Erro de conexão. Tente novamente.';
                    document.getElementById('error-msg').classList.remove('hidden');
                }}
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ─────────────────────────────────────────────
# POST /google — Valida token Google, gera cookie de sessão
# ─────────────────────────────────────────────
@router.post("/google")
@limiter.limit("5/minute")
def login_google_oauth(
    request: Request,
    credential: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Recebe o ID Token do Google Identity Services.
    Valida com o Google, busca o usuário no banco e define o cookie de sessão JWT.
    """
    try:
        idinfo = id_token.verify_oauth2_token(credential, google_request, GOOGLE_CLIENT_ID)
        email = idinfo.get("email")
        if not email or not idinfo.get("email_verified"):
            raise HTTPException(status_code=400, detail="E-mail não verificado pelo Google.")
            
        if not email.endswith("@janiopontes.com.br"):
            raise HTTPException(
                status_code=403, 
                detail="Acesso negado: Apenas e-mails corporativos @janiopontes.com.br são permitidos."
            )

        # Bypass RLS para encontrar o usuário pelo e-mail (tenant ainda desconhecido)
        try:
            db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        except Exception:
            pass
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()

        if not user:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado: '{email}' não está registrado no sistema."
            )
        if not user.ativo:
            raise HTTPException(status_code=400, detail="Usuário inativo. Contate o administrador.")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = security.create_access_token(user.id, expires_delta=access_token_expires)

        response = JSONResponse(content={"ok": True, "message": "Login realizado com sucesso."})
        response.set_cookie(
            key="__session",
            value=token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=True
        )
        return response

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido ou expirado.")


# ─────────────────────────────────────────────
# GET /logout — Limpa o cookie de sessão
# ─────────────────────────────────────────────
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="__session")
    return response
