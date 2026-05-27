"""
Integração com Google Drive API.
Responsável pelo upload e gerenciamento de permissões dos documentos dos clientes.

Utiliza Service Account do Google Workspace para acessar o Drive corporativo.
"""
import os
import io
import uuid
import logging

from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DRIVE_MODE = os.getenv("DRIVE_MODE", "mock")  # "mock" ou "production"
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/secrets/credentials.json" if os.path.exists("/secrets/credentials.json") else "credentials.json")
DRIVE_ROOT_FOLDER = os.getenv("DRIVE_ROOT_FOLDER", "")  # ID da pasta raiz no Drive


class DriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self._service = None

    def _get_service(self):
        """Inicializa o serviço Drive API com Service Account."""
        if self._service:
            return self._service

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=self.scopes
        )
        self._service = build('drive', 'v3', credentials=credentials)
        return self._service

    async def upload_file(self, file: UploadFile, folder_id: str = None) -> str:
        """
        Recebe um arquivo do FastAPI e faz o upload para o Google Drive.
        Retorna a URL de visualização do arquivo gerado.
        """
        if DRIVE_MODE == "mock":
            fake_id = str(uuid.uuid4())[:8]
            fake_url = f"https://drive.google.com/file/d/mock_{fake_id}/view?usp=sharing"
            logger.info(f"[MOCK DRIVE] Upload simulado: {file.filename} → {fake_url}")
            print(f"[MOCK DRIVE] Upload simulado: {file.filename} → {fake_url}")
            return fake_url

        try:
            from googleapiclient.http import MediaIoBaseUpload

            service = self._get_service()
            content = await file.read()

            file_metadata = {'name': file.filename}
            target_folder = folder_id or DRIVE_ROOT_FOLDER
            if target_folder:
                file_metadata['parents'] = [target_folder]

            media = MediaIoBaseUpload(
                io.BytesIO(content),
                mimetype=file.content_type or 'application/octet-stream',
                resumable=True
            )

            result = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = result.get('id')
            web_link = result.get('webViewLink', self.get_file_link(file_id))

            # Torna o arquivo acessível via link (anyone with link can view)
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            logger.info(f"[DRIVE] Upload real: {file.filename} → {web_link}")
            return web_link

        except Exception as e:
            logger.error(f"[DRIVE ERRO] Upload falhou: {file.filename} | Erro: {str(e)}")
            return f"ERRO: Upload falhou - {str(e)}"

    def get_file_link(self, file_id: str) -> str:
        """Gera o link de visualização com permissões de leitura."""
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


drive_service = DriveService()
