import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Janio Pontes SaaS"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "minha-chave-super-secreta-de-desenvolvimento")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for token lifetime
    
    # URL da API de validação do Google (se usarmos o token do lado do cliente)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")

settings = Settings()
