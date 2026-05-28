import asyncio
from app.core.email_service import email_service

async def test():
    result = await email_service.enviar_email("janiopontes@janiopontes.com.br", "Teste", "<h1>Teste</h1>")
    print("Resultado:", result)

asyncio.run(test())
