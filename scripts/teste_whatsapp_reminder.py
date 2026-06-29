import sys
import os
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.chatwoot_service import ChatwootService

load_dotenv()

async def teste_whatsapp():
    print("Iniciando teste de envio de template de WhatsApp (automatico_protocolos)...")
    chatwoot = ChatwootService()
    
    telefone_teste = input("Digite o número de telefone com DDD para teste (ex: +5511999999999): ").strip()
    if not telefone_teste:
        print("Telefone não fornecido. Teste cancelado.")
        return
        
    try:
        resultado = await chatwoot.send_template_notification(
            name="Teste WhatsApp",
            email="teste@whatsapp.com",
            template_name="automatico_protocolos",
            phone_number=telefone_teste,
            template_params=["Teste", "1"]
        )
        print(f"Resultado do disparo: {resultado}")
        print("Teste concluido. Verifique o celular.")
    except Exception as e:
        print(f"Erro ao enviar template: {str(e)}")

if __name__ == "__main__":
    asyncio.run(teste_whatsapp())
