import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from app.core.chatwoot_service import chatwoot_service

async def teste():
    try:
        contact_id = await chatwoot_service.get_or_create_contact('Janio Pontes (TESTE)', 'janiopontes@janiopontes.com.br', '+5534999721001')
        print(f"Contact ID: {contact_id}")
        conv_id = await chatwoot_service.get_or_create_conversation(contact_id)
        print(f"Conversation ID: {conv_id}")
        msg_data = {
            'content': 'Envio de template: protocolos',
            'message_type': 'outgoing',
            'content_attributes': {},
            'template_params': {
                'name': 'protocolos',
                'language': 'pt_BR',
                'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': 'Janio Pontes (TESTE)'}, {'type': 'text', 'text': '19'}]}]
            }
        }
        result = await chatwoot_service._request('POST', f'conversations/{conv_id}/messages', msg_data)
        import json
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Erro: {e}")

asyncio.run(teste())
