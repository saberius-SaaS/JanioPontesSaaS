import httpx
import logging
import re
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _normalize_phone(raw: str) -> Optional[str]:
    """Normaliza telefone para formato E.164 (+5534999999999)."""
    if not raw:
        return None
    digits = re.sub(r'[^0-9]', '', raw)
    if not digits:
        return None
    if digits.startswith('55') and len(digits) >= 12:
        return f'+{digits}'
    if len(digits) >= 10:
        return f'+55{digits}'
    return None


def _phones_match(a: Optional[str], b: Optional[str]) -> bool:
    """Compara dois telefones ignorando formatação."""
    if not a or not b:
        return False
    da = re.sub(r'[^0-9]', '', a)
    db = re.sub(r'[^0-9]', '', b)
    if not da or not db:
        return False
    if da == db:
        return True
    if da.startswith('55') and da[2:] == db:
        return True
    if db.startswith('55') and db[2:] == da:
        return True
    return False

class ChatwootService:
    def __init__(self):
        self.base_url = settings.CHATWOOT_BASE_URL.rstrip('/')
        self.api_token = settings.CHATWOOT_API_TOKEN
        self.account_id = settings.CHATWOOT_ACCOUNT_ID
        
        self.headers = {
            "api-access-token": self.api_token,
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
        Busca um contato por telefone no Chatwoot e retorna seu ID.
        Valida que o telefone do contato encontrado corresponde ao esperado.
        Se não existir ou o telefone não bater, cria/atualiza o contato.
        """
        normalized_phone = _normalize_phone(phone_number) if phone_number else None
        
        # 1. Buscar por telefone (prioridade) ou email
        search_query = normalized_phone or phone_number or email
        if search_query:
            safe_query = search_query.replace('+', '%2B') if search_query.startswith('+') else search_query
            search_result = await self._request("GET", f"contacts/search?q={safe_query}")
            if search_result and "payload" in search_result and search_result["payload"]:
                # Validação estrita: o contato encontrado DEVE ter o telefone correto
                for contact in search_result["payload"]:
                    contact_phone = contact.get("phone_number", "")
                    if normalized_phone and _phones_match(contact_phone, normalized_phone):
                        logger.info(f"Contato encontrado com telefone correto: {contact.get('name')} (ID: {contact.get('id')})")
                        return contact.get("id")
                
                # Se encontrou por nome/email mas telefone não bate, atualizar o primeiro com o telefone correto
                if normalized_phone:
                    first_contact = search_result["payload"][0]
                    first_phone = first_contact.get("phone_number", "")
                    logger.warning(
                        f"Contato '{first_contact.get('name')}' encontrado mas telefone diverge: "
                        f"esperado={normalized_phone}, encontrado={first_phone}. Criando novo contato."
                    )

        # 2. Criar novo contato com telefone normalizado
        contact_data = {
            "name": name,
            "email": email,
        }
        if normalized_phone:
            contact_data["phone_number"] = normalized_phone
        elif phone_number:
            contact_data["phone_number"] = phone_number

        create_result = await self._request("POST", "contacts", {"inbox_id": settings.CHATWOOT_INBOX_ID, **contact_data})
        if create_result and "payload" in create_result and create_result["payload"].get("contact"):
            new_id = create_result["payload"]["contact"].get("id")
            logger.info(f"Novo contato criado: {name} / {normalized_phone or phone_number} (ID: {new_id})")
            return new_id
            
        return None

    async def get_or_create_conversation(self, contact_id: int) -> Optional[int]:
        """
        Obtém ou cria uma conversa para o contato no inbox padrão.
        """
        # Listar conversas do contato
        conversations = await self._request("GET", f"contacts/{contact_id}/conversations")
        if conversations:
            payload_convs = []
            if "payload" in conversations:
                payload_convs = conversations["payload"]
            elif "data" in conversations and "payload" in conversations["data"]:
                payload_convs = conversations["data"]["payload"]
                
            if payload_convs:
                # Retorna a conversa que pertence ao inbox correto (WhatsApp)
                for conv in payload_convs:
                    if conv.get("inbox_id") == settings.CHATWOOT_INBOX_ID:
                        return conv.get("id")

        # Criar nova conversa no inbox correto
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

    async def send_template_notification(self, name: str, email: str, template_name: str, phone_number: Optional[str] = None, template_params: list = None) -> bool:
        """
        Busca/cria contato e conversa, depois envia um template aprovado do WhatsApp.
        template_params é uma lista de strings para preencher as variáveis {{1}}, {{2}} do corpo da mensagem.
        """
        contact_id = await self.get_or_create_contact(name, email, phone_number)
        if not contact_id:
            logger.error(f"Falha ao obter/criar contato no Chatwoot para: {email}")
            return False
            
        conversation_id = await self.get_or_create_conversation(contact_id)
        if not conversation_id:
            logger.error(f"Falha ao obter/criar conversa no Chatwoot para contato ID: {contact_id}")
            return False
            
        # Preparar os parâmetros do template (Body components)
        components = []
        if template_params:
            components = [{
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in template_params]
            }]

        processed_params = {}
        if template_params:
            for i, p in enumerate(template_params, 1):
                processed_params[str(i)] = str(p)

        # Texto que aparecerá na interface do Chatwoot para os atendentes
        preview_text = f"📱 [Notificação Automática WhatsApp]\nTemplate: {template_name}"
        if template_params:
            preview_text += f"\nVariáveis preenchidas: {', '.join(str(p) for p in template_params)}"

        msg_data = {
            "content": preview_text,
            "message_type": "template",
            "content_attributes": {},
            "template_params": {
                "name": template_name,
                "language": "pt_BR",
                "processed_params": processed_params,
                "components": components
            }
        }
        
        result = await self._request("POST", f"conversations/{conversation_id}/messages", msg_data)
        return bool(result and result.get("id"))

    async def get_agent_by_email(self, email: str) -> Optional[int]:
        """
        Lista agentes da conta e encontra o ID correspondente ao email.
        """
        agents = await self._request("GET", "agents")
        if agents and isinstance(agents, list):
            for agent in agents:
                if agent.get("email") == email:
                    return agent.get("id")
        return None

    async def get_sso_url(self, user_id: int) -> Optional[str]:
        """
        Gera um URL mágico de login para um usuário usando a Platform API.
        Requer CHATWOOT_PLATFORM_TOKEN.
        """
        if not settings.CHATWOOT_PLATFORM_TOKEN:
            logger.error("CHATWOOT_PLATFORM_TOKEN não configurado. Impossível gerar SSO.")
            return None

        url = f"{self.base_url}/platform/api/v1/users/{user_id}/login"
        headers = {
            "api-access-token": settings.CHATWOOT_PLATFORM_TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request("GET", url, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("url")
            except Exception as e:
                logger.error(f"Erro na Platform API do Chatwoot ({url}): {str(e)}")
                return None

chatwoot_service = ChatwootService()
