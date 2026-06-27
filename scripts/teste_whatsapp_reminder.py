"""
Teste de WhatsApp Reminder — Envia UMA mensagem de teste para o celular do admin.
NÃO altera protocolos. NÃO envia para clientes.
"""
import os, sys, asyncio, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from app.core.chatwoot_service import chatwoot_service

TELEFONE_TESTE = "+5534999721001"
NOME_TESTE = "Janio Pontes (TESTE)"
EMAIL_TESTE = "janiopontes@janiopontes.com.br"

async def main():
    print("\n" + "="*60)
    print("  TESTE DE WHATSAPP REMINDER")
    print("="*60)
    print(f"  Destino: {TELEFONE_TESTE}")
    print(f"  Template: protocolos")
    print(f"  Parametros: ['{NOME_TESTE}', '19']")
    print("="*60)

    # Usa o mesmo método que a rota /scheduler/whatsapp-reminders
    sucesso = await chatwoot_service.send_template_notification(
        name=NOME_TESTE,
        email=EMAIL_TESTE,
        template_name="protocolos",
        phone_number=TELEFONE_TESTE,
        template_params=[NOME_TESTE, "19"]
    )

    if sucesso:
        print(f"\n  SUCESSO! Mensagem enviada para {TELEFONE_TESTE}.")
        print(f"  Verifique seu WhatsApp agora.\n")
    else:
        print(f"\n  FALHA ao enviar. Verifique os logs acima.")
        print(f"  Possiveis causas:")
        print(f"    - Template 'protocolos' nao aprovado no WhatsApp Business")
        print(f"    - Inbox do Chatwoot nao configurado para WhatsApp")
        print(f"    - Contato nao encontrado/criado no Chatwoot\n")

if __name__ == "__main__":
    asyncio.run(main())
