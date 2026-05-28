import asyncio
import os
from dotenv import load_dotenv
load_dotenv('G:/Meu Drive/JanioPontesSaas/.env')

# Mock models
class MockTarefa:
    def __init__(self):
        self.obrigacao = "TESTE"
        self.cliente = "CLIENTE TESTE"
        self.mes_ano = "05/2026"
        self.vencimento_legal = None

from app.core.email_service import email_service

async def test_email():
    print(f"EMAIL_MODE is: {os.getenv('EMAIL_MODE')}")
    print(f"EMAIL_INTERCEPT_ADDRESS is: {os.getenv('EMAIL_INTERCEPT_ADDRESS')}")
    try:
        from app.routers.tarefa import enviar_notificacao_entrega
        tarefa = MockTarefa()
        await enviar_notificacao_entrega(tarefa, "PRT-12345", "test@test.com", "Test User", "Test Justification")
        print("Test passed!")
    except Exception as e:
        print(f"Exception: {str(e)}")

asyncio.run(test_email())
