import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Janio Pontes SaaS"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "minha-chave-super-secreta-de-desenvolvimento")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours for token lifetime (horário comercial)
    
    # URL da API de validação do Google (se usarmos o token do lado do cliente)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    
    # Chatwoot Configuration
    CHATWOOT_BASE_URL: str = os.getenv("CHATWOOT_BASE_URL", "https://chat.janiopontes.com.br")
    CHATWOOT_API_TOKEN: str = os.getenv("CHATWOOT_API_TOKEN", "") # Access token do administrador (para API)
    CHATWOOT_ACCOUNT_ID: int = int(os.getenv("CHATWOOT_ACCOUNT_ID", "1"))
    CHATWOOT_INBOX_ID: int = int(os.getenv("CHATWOOT_INBOX_ID", "1")) # Inbox do WhatsApp ou Web
    CHATWOOT_WEB_TOKEN: str = os.getenv("CHATWOOT_WEB_TOKEN", "") # Website Token para o widget

settings = Settings()
