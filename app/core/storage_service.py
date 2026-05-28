"""
Integração com Google Cloud Storage (GCS).
Responsável pelo upload e gerenciamento de permissões dos documentos dos clientes.
"""
import os
import uuid
import logging
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Variável de ambiente que controla se usamos o mock ou a API real
STORAGE_MODE = os.getenv("STORAGE_MODE", "mock")  # "mock" ou "production"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "jpsaas-arquivos-producao")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/secrets/credentials.json" if os.path.exists("/secrets/credentials.json") else "credentials.json")

class StorageService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        """Inicializa o client do GCS."""
        if self._client:
            return self._client
            
        from google.cloud import storage
        from google.oauth2 import service_account
        
        if os.path.exists(CREDENTIALS_FILE):
            credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
            self._client = storage.Client(credentials=credentials)
        else:
            # Fallback para credenciais padrão do ambiente GCP
            self._client = storage.Client()
            
        return self._client

    async def upload_file(self, file: UploadFile, cliente_nome: str = "Geral") -> str:
        """
        Recebe um arquivo do FastAPI e faz o upload para o Google Cloud Storage.
        Retorna a URL pública do arquivo gerado.
        """
        if STORAGE_MODE == "mock":
            fake_id = str(uuid.uuid4())[:8]
            fake_url = f"https://storage.googleapis.com/mock-bucket/mock_{fake_id}_{file.filename}"
            logger.info(f"[MOCK GCS] Upload simulado: {file.filename} → {fake_url}")
            print(f"[MOCK GCS] Upload simulado: {file.filename} → {fake_url}")
            return fake_url

        try:
            client = self._get_client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            
            # Limpar nome do cliente para usar como pasta
            safe_cliente = "".join(c if c.isalnum() else "_" for c in cliente_nome)
            file_path = f"{safe_cliente}/{uuid.uuid4().hex[:8]}_{file.filename}"
            
            blob = bucket.blob(file_path)
            
            content = await file.read()
            blob.upload_from_string(content, content_type=file.content_type)
            
            # Torna o arquivo público para leitura com base em URL
            # Note: O bucket deve permitir objetos públicos (allUsers: objectViewer) ou assinar a URL
            # Aqui vamos assumir um bucket com regras públicas de leitura ou usar Signed URLs,
            # mas o padrão GCP para arquivos de visualização pública é public_url.
            
            try:
                blob.make_public()
            except Exception as e:
                # Pode falhar se o bucket tiver "Uniform bucket-level access" com restrição
                logger.warning(f"Não foi possível tornar público via make_public(): {e}")
                
            web_link = blob.public_url
            
            logger.info(f"[GCS] Upload real: {file.filename} → {web_link}")
            return web_link

        except Exception as e:
            logger.error(f"[GCS ERRO] Upload falhou: {file.filename} | Erro: {str(e)}")
            return f"ERRO: Upload falhou - {str(e)}"

storage_service = StorageService()
