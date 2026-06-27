import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from app.core.chatwoot_service import chatwoot_service

async def teste():
    try:
        result = await chatwoot_service._request('GET', 'inboxes')
        for inbox in result.get('payload', []):
            print(f"ID: {inbox.get('id')} | Name: {inbox.get('name')} | Channel: {inbox.get('channel_type')}")
    except Exception as e:
        print(f"Erro: {e}")

asyncio.run(teste())
