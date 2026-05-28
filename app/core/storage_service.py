"""
Integração com Google Cloud Storage (GCS).
Responsável pelo upload de documentos e geração de URLs assinadas/públicas seguras.
Substitui a integração legada do Google Drive, oferecendo maior performance,
desacoplamento e redução dramática de custos e limites de API.
"""
import os
import uuid
import logging
from datetime import timedelta

from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GCS_MODE = os.getenv("DRIVE_MODE", "mock")  # usando a mesma variável do .env legado por conveniência
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/secrets/credentials.json" if os.path.exists("/secrets/credentials.json") else "credentials.json")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "janio-pontes-saas-docs")


class StorageService:
    def __init__(self):
        self._client = None
        self._bucket = None

    def _get_client(self):
        """Inicializa o cliente do Google Cloud Storage."""
        if self._client:
            return self._client

        from google.cloud import storage
        from google.oauth2 import service_account

        # Verifica se estamos no Cloud Run (usa credenciais default) ou ambiente local
        if os.path.exists(CREDENTIALS_FILE):
            credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
            self._client = storage.Client(credentials=credentials)
        else:
            # Fallback para as credenciais padrão do ambiente do GCP (útil para Cloud Run)
            self._client = storage.Client()
            
        return self._client

    def _get_bucket(self):
        """Recupera a instância do Bucket configurado."""
        if self._bucket:
            return self._bucket
            
        client = self._get_client()
        self._bucket = client.bucket(GCS_BUCKET_NAME)
        return self._bucket

    async def upload_file(self, file: UploadFile, cliente_nome: str = "Geral") -> str:
        """
        Recebe um arquivo do FastAPI e faz o upload para o Google Cloud Storage.
        Retorna uma Signed URL válida por 7 dias, ou URL pública.
        """
        if GCS_MODE == "mock":
            fake_id = str(uuid.uuid4())[:8]
            fake_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/mock/{cliente_nome}/{fake_id}_{file.filename}"
            logger.info(f"[MOCK GCS] Upload simulado: {file.filename} → {fake_url}")
            print(f"[MOCK GCS] Upload simulado: {file.filename} → {fake_url}")
            return fake_url

        try:
            content = await file.read()
            
            # Sanitiza o nome do cliente para a estrutura de pastas
            safe_cliente = cliente_nome.replace(" ", "_").replace("/", "-")
            safe_filename = file.filename.replace(" ", "_")
            unique_id = str(uuid.uuid4())[:6]
            
            # Caminho dentro do bucket: clientes/nome_do_cliente/id_arquivo.pdf
            blob_path = f"clientes/{safe_cliente}/{unique_id}_{safe_filename}"
            
            bucket = self._get_bucket()
            blob = bucket.blob(blob_path)
            
            # Faz o upload diretamente
            blob.upload_from_string(
                content,
                content_type=file.content_type or 'application/octet-stream'
            )
            
            # Opção 1: Arquivo Público (Se o bucket for configurado como público)
            # blob.make_public()
            # web_link = blob.public_url
            
            # Opção 2: Signed URL (URL segura que expira em X dias) - Mais seguro para documentos contábeis
            # Se a credencial não for de Service Account diretamente (ex: Compute Engine Default),
            # gerar Signed URLs pode exigir permissão de IAM 'Service Account Token Creator'
            try:
                web_link = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=30),  # Link expira em 30 dias para segurança do cliente
                    method="GET"
                )
            except Exception as sign_error:
                # Se falhar a assinatura (geralmente por falta de permissão no Cloud Run default SA),
                # retornamos a URL autenticada do console (que exige login) ou public url
                logger.warning(f"Não foi possível assinar a URL (falta de IAM?): {str(sign_error)}")
                # Cai para a URL pública (O bucket deve ter 'allUsers: Storage Object Viewer' ou ser acessado via API)
                web_link = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"

            logger.info(f"[GCS] Upload real: {file.filename} → {web_link[:60]}...")
            return web_link

        except Exception as e:
            logger.error(f"[GCS ERRO] Upload falhou: {file.filename} | Erro: {str(e)}")
            return f"ERRO: Upload GCS falhou - {str(e)}"


storage_service = StorageService()
