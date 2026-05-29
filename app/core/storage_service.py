"""
Integração com Google Cloud Storage (GCS).
Responsável pelo upload e gerenciamento de permissões dos documentos dos clientes.

O bucket usa Uniform Bucket-Level Access + Public Access Prevention (enforced),
portanto não é possível usar make_public() nem ACLs por objeto.
A estratégia de acesso é via Signed URLs com validade de 7 dias.
"""
import os
import uuid
import logging
import datetime
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Variável de ambiente que controla se usamos o mock ou a API real
STORAGE_MODE = os.getenv("STORAGE_MODE", "mock")  # "mock" ou "production"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "jpsaas-arquivos-producao")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/secrets/credentials.json" if os.path.exists("/secrets/credentials.json") else "credentials.json")
SIGNED_URL_EXPIRATION_DAYS = int(os.getenv("SIGNED_URL_EXPIRATION_DAYS", "7"))

class StorageService:
    def __init__(self):
        self._client = None
        self._credentials = None

    def _get_client(self):
        """Inicializa o client do GCS."""
        if self._client:
            return self._client
            
        from google.cloud import storage
        from google.oauth2 import service_account
        
        if os.path.exists(CREDENTIALS_FILE):
            self._credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
            self._client = storage.Client(credentials=self._credentials)
        else:
            # Fallback para credenciais padrão do ambiente GCP
            self._client = storage.Client()
            
        return self._client

    def _generate_signed_url(self, blob) -> str:
        """
        Gera uma Signed URL com validade configurável (padrão: 7 dias).
        Funciona mesmo com Uniform Bucket-Level Access e Public Access Prevention habilitados.
        """
        try:
            expiration = datetime.timedelta(days=SIGNED_URL_EXPIRATION_DAYS)
            
            # Se temos credenciais de Service Account, usa diretamente
            if self._credentials:
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET",
                    credentials=self._credentials
                )
            else:
                # Em ambiente Cloud Run sem arquivo de credenciais,
                # usa as credenciais padrão do compute engine
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET"
                )
            return url
        except Exception as e:
            logger.error(f"[GCS] Falha ao gerar Signed URL: {str(e)}")
            # Fallback: retorna URL pública padrão (provavelmente dará 403)
            return blob.public_url

    async def upload_file(self, file: UploadFile, cliente_nome: str = "Geral") -> str:
        """
        Recebe um arquivo do FastAPI e faz o upload para o Google Cloud Storage.
        Retorna uma Signed URL com validade de 7 dias para acesso ao documento.
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
            
            # Gera Signed URL (acesso temporário seguro, sem necessidade de tornar público)
            web_link = self._generate_signed_url(blob)
            
            logger.info(f"[GCS] Upload real: {file.filename} → Signed URL gerada (expira em {SIGNED_URL_EXPIRATION_DAYS} dias)")
            return web_link

        except Exception as e:
            logger.error(f"[GCS ERRO] Upload falhou: {file.filename} | Erro: {str(e)}")
            return f"ERRO: Upload falhou - {str(e)}"

storage_service = StorageService()

