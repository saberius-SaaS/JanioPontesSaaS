"""
Integração de E-mail via Gmail API (Workspace)
Substitui a antiga classe EmailService.js do GAS.

Utiliza Service Account com delegação de domínio para enviar e-mails
em nome de um usuário do Google Workspace (ex: sistema@janiopontes.com.br).
"""
import os
import base64
import logging
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Variável de ambiente que controla se usamos o mock ou a API real
EMAIL_MODE = os.getenv("EMAIL_MODE", "intercept")  # "mock", "intercept" ou "production"
EMAIL_INTERCEPT_ADDRESS = os.getenv("EMAIL_INTERCEPT_ADDRESS", "janiopontes@janiopontes.com.br")
GMAIL_DELEGATED_USER = os.getenv("GMAIL_DELEGATED_USER", "janiopontes@janiopontes.com.br")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "/secrets/credentials.json" if os.path.exists("/secrets/credentials.json") else "credentials.json")


class EmailService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/gmail.send']
        self._service = None

    def _get_service(self):
        """Inicializa o serviço Gmail API com Service Account + delegação."""
        if self._service:
            return self._service

        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=self.scopes
        )
        # Delegação de domínio: a Service Account "se passa" pelo usuário do Workspace
        delegated_credentials = credentials.with_subject(GMAIL_DELEGATED_USER)
        self._service = build('gmail', 'v1', credentials=delegated_credentials)
        return self._service

    def _build_message(self, para: str, assunto: str, corpo_html: str) -> dict:
        """Monta o objeto EmailMessage codificado em base64 para a Gmail API."""
        message = EmailMessage()
        message.set_content(corpo_html, subtype='html')
        message['To'] = para
        message['From'] = GMAIL_DELEGATED_USER
        message['Subject'] = assunto

        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': encoded}

    async def enviar_email(self, para: str, assunto: str, corpo_html: str, anexos: list = None) -> bool:
        """
        Envia um e-mail.
        Em modo 'mock', apenas loga no console.
        Em modo 'intercept', envia o e-mail real via API, mas substitui o destinatário para avaliação segura.
        Em modo 'production', usa a Gmail API de verdade enviando para o cliente real.
        """
        if EMAIL_MODE == "mock":
            logger.info(f"[MOCK EMAIL] Para: {para} | Assunto: {assunto}")
            print(f"[MOCK EMAIL] Para: {para} | Assunto: {assunto}")
            return True
            
        destino_final = para
        if EMAIL_MODE == "intercept":
            assunto = f"[INTERCEPTADO de {para}] {assunto}"
            destino_final = EMAIL_INTERCEPT_ADDRESS
            corpo_html = f"<div style='background-color:#fff3cd; padding:10px; border:1px solid #ffe69c; color:#664d03; margin-bottom:20px; border-radius:5px;'><strong>Modo de Interceptação de Teste (Homologação)</strong><br>Este e-mail seria enviado originalmente para: <b>{para}</b></div>" + corpo_html

        try:
            service = self._get_service()
            body = self._build_message(destino_final, assunto, corpo_html)
            service.users().messages().send(userId='me', body=body).execute()
            logger.info(f"[EMAIL ENVIADO] Para: {destino_final} | Assunto: {assunto}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL ERRO] Para: {para} | Erro: {str(e)}")
            return False


email_service = EmailService()
