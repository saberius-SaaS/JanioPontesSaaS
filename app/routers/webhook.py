from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
import json

from app.database import get_db

router = APIRouter()

def processar_evento_chatwoot(payload: dict):
    """Processa o evento em background para liberar o webhook imediatamente"""
    event_type = payload.get("event")
    if event_type == "message_created":
        message_type = payload.get("message_type")
        content = payload.get("content")
        sender = payload.get("sender", {}).get("name")
        
        # Ignorar mensagens enviadas pelo próprio agente
        if message_type == "incoming":
            print(f"[BACKGROUND] Processando mensagem de {sender}: {content}")
            # Lógica de atualização de protocolo no banco entrará aqui...

@router.post("/chatwoot")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Recebe eventos em tempo real do Chatwoot (ex: mensagem recebida, contato criado).
    """
    payload = await request.json()
    
    # 7.1.2 Adiciona a rotina na fila de execução em segundo plano
    background_tasks.add_task(processar_evento_chatwoot, payload)
            
    return {"status": "success"}
