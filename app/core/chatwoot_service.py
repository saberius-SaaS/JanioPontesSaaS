import httpx
import logging
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class ChatwootService:
    def __init__(self):
        self.base_url = settings.CHATWOOT_BASE_URL.rstrip('/')
        self.api_token = settings.CHATWOOT_API_TOKEN
        self.account_id = settings.CHATWOOT_ACCOUNT_ID
        
        self.headers = {
            "api_access_token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.api_token:
            logger.warning("Chatwoot API Token não configurado. Ignorando chamada.")
            return None
            
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=self.headers, json=data, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP na API do Chatwoot ({url}): {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Erro na API do Chatwoot ({url}): {str(e)}")
                return None

    async def get_or_create_contact(self, name: str, email: str, phone_number: Optional[str] = None) -> Optional[int]:
        """
        Busca um contato por email (ou telefone) no Chatwoot e retorna seu ID.
        Se não existir, cria o contato.
        """
        # 1. Tentar buscar por email
        search_result = await self._request("GET", f"contacts/search?q={email}")
        if search_result and "payload" in search_result and search_result["payload"]:
            return search_result["payload"][0].get("id")

        # 2. Se não encontrou, criar
        contact_data = {
            "name": name,
            "email": email,
        }
        if phone_number:
            contact_data["phone_number"] = phone_number

        create_result = await self._request("POST", "contacts", {"inbox_id": settings.CHATWOOT_INBOX_ID, **contact_data})
        if create_result and "payload" in create_result and create_result["payload"].get("contact"):
            return create_result["payload"]["contact"].get("id")
            
        return None

    async def get_or_create_conversation(self, contact_id: int) -> Optional[int]:
        """
        Obtém ou cria uma conversa para o contato no inbox padrão.
        """
        # Listar conversas do contato
        conversations = await self._request("GET", f"conversations?status=all&contact_id={contact_id}")
        if conversations and "data" in conversations and "meta" in conversations["data"]:
            payload_convs = conversations["data"].get("payload", [])
            if payload_convs:
                # Retorna a conversa mais recente aberta, ou a primeira que encontrar
                return payload_convs[0].get("id")

        # Criar nova conversa
        conv_data = {
            "inbox_id": settings.CHATWOOT_INBOX_ID,
            "contact_id": contact_id,
            "status": "open"
        }
        new_conv = await self._request("POST", "conversations", conv_data)
        if new_conv and new_conv.get("id"):
            return new_conv.get("id")
            
        return None

    async def send_message(self, conversation_id: int, content: str) -> bool:
        """
        Envia uma mensagem (outbound) em uma conversa existente.
        """
        msg_data = {
            "content": content,
            "message_type": "outgoing",
            "private": False
        }
        
        result = await self._request("POST", f"conversations/{conversation_id}/messages", msg_data)
        return bool(result and result.get("id"))
        
    async def send_notification(self, name: str, email: str, message: str, phone_number: Optional[str] = None) -> bool:
        """
        Método de alto nível: Busca/cria contato, busca/cria conversa e envia a mensagem.
        """
        contact_id = await self.get_or_create_contact(name, email, phone_number)
        if not contact_id:
            logger.error(f"Falha ao obter/criar contato no Chatwoot para: {email}")
            return False
            
        conversation_id = await self.get_or_create_conversation(contact_id)
        if not conversation_id:
            logger.error(f"Falha ao obter/criar conversa no Chatwoot para contato ID: {contact_id}")
            return False
            
        return await self.send_message(conversation_id, message)

chatwoot_service = ChatwootService()
