import os
import json
import sqlite3
import traceback
import httpx
import uvicorn
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks

app = FastAPI()

TYPEBOT_URL = "https://bot.janiopontes.com.br"
TYPEBOT_ID = "atendimento-razjlcs"
CHATWOOT_URL = "http://127.0.0.1:3000"
BOT_TOKEN = "bWKNBd4zhtaBUnwdcZ7bT2Bf"

DB_FILE = "/opt/typebot_sessions.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                chatwoot_conversation_id INTEGER PRIMARY KEY,
                typebot_session_id TEXT NOT NULL
            )
        """)

init_db()

def get_session(conversation_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT typebot_session_id FROM sessions WHERE chatwoot_conversation_id = ?", (conversation_id,))
        row = cursor.fetchone()
        return row[0] if row else None

def save_session(conversation_id: int, session_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR REPLACE INTO sessions (chatwoot_conversation_id, typebot_session_id) VALUES (?, ?)", (conversation_id, session_id))

def delete_session(conversation_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM sessions WHERE chatwoot_conversation_id = ?", (conversation_id,))

def extract_messages(messages):
    parsed = []
    for msg in messages:
        msg_type = msg.get("type")
        if msg_type == "text":
            content = msg.get("content", {})
            rich_text = content.get("richText", [])
            if rich_text:
                parts = []
                for block in rich_text:
                    children = block.get("children", [])
                    for child in children:
                        text = child.get("text", "")
                        if text:
                            parts.append(text)
                if parts:
                    parsed.append({'type': 'text', 'content': " ".join(parts)})
            elif content.get("plainText"):
                parsed.append({'type': 'text', 'content': content["plainText"]})
        elif msg_type == "image":
            url = msg.get("content", {}).get("url")
            if url:
                parsed.append({'type': 'image', 'url': url})
    return parsed

def merge_messages(parsed_messages):
    merged = []
    i = 0
    while i < len(parsed_messages):
        current = parsed_messages[i]
        if current['type'] == 'image' and i + 1 < len(parsed_messages) and parsed_messages[i+1]['type'] == 'text':
            merged.append({
                'type': 'image_with_caption',
                'url': current['url'],
                'caption': parsed_messages[i+1]['content']
            })
            i += 2
        else:
            merged.append(current)
            i += 1
    return merged

async def process_webhook(payload: dict):
    try:
        event = payload.get("event")
        print(f"[BRIDGE] === FULL EVENT: {event} ===", flush=True)
        print(f"[BRIDGE] Payload keys: {list(payload.keys())}", flush=True)
        
        # Log message_type for debugging
        message_type = payload.get("message_type")
        print(f"[BRIDGE] message_type: {message_type}", flush=True)
        
        # Only process message_created events
        if event != "message_created":
            print(f"[BRIDGE] Skipping event: {event}", flush=True)
            return



        # In Agent Bot webhook, message_type can be:
        # "incoming" (0) = from customer
        # "outgoing" (1) = from agent/bot  
        # "activity" (2) = system activity
        # "template" (3) = template message
        # Check both string and integer formats
        if message_type in ("outgoing", 1, "1", "activity", 2, "2", "template", 3, "3"):
            print(f"[BRIDGE] Skipping non-customer message_type: {message_type}", flush=True)
            return

        content = payload.get("content", "")
        
        # Try to extract conversation info from different payload structures
        # Agent Bot webhook format has nested conversation data
        conversation = payload.get("conversation", {})
        conversation_id = conversation.get("id") if isinstance(conversation, dict) else None

        # Verifica se é final de semana (sábado=5, domingo=6)
        import datetime
        from datetime import timezone, timedelta
        tz_br = timezone(timedelta(hours=-3)) # Horário de Brasília (UTC-3)
        agora = datetime.datetime.now(tz_br)
        if agora.weekday() >= 5:
            print(f"[BRIDGE] Ignorando mensagem (Final de semana). Aplicando etiqueta.", flush=True)
            if conversation_id:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await add_chatwoot_label(client, conversation_id, "fimdesemana")
            return
        
        # Try sender info
        sender = payload.get("sender", {})
        sender_name = sender.get("name", "Cliente") if isinstance(sender, dict) else "Cliente"
        sender_type = sender.get("type", "") if isinstance(sender, dict) else ""
        
        print(f"[BRIDGE] Content: '{content}'", flush=True)
        print(f"[BRIDGE] Conversation ID: {conversation_id}", flush=True)
        print(f"[BRIDGE] Sender: {sender_name} (type: {sender_type})", flush=True)

        # Skip messages sent by the bot itself to avoid loops
        if sender_type == "agent_bot":
            print(f"[BRIDGE] Skipping bot's own message", flush=True)
            return

        if not conversation_id or not content:
            print(f"[BRIDGE] Missing conversation_id or content", flush=True)
            return

        print(f"[BRIDGE] >>> PROCESSING message from {sender_name}: '{content}' (conv={conversation_id})", flush=True)

        typebot_session_id = get_session(conversation_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            if not typebot_session_id:
                print(f"[BRIDGE] Starting NEW Typebot session for conv {conversation_id}", flush=True)
                response = await client.post(
                    f"{TYPEBOT_URL}/api/v1/typebots/{TYPEBOT_ID}/startChat",
                    json={
                        "isOnlyRegistering": False,
                        "prefilledVariables": {"Contact Name": sender_name}
                    }
                )
                print(f"[BRIDGE] Typebot startChat status: {response.status_code}", flush=True)
                data = response.json()
                print(f"[BRIDGE] Typebot startChat response: {json.dumps(data, ensure_ascii=False)[:800]}", flush=True)

                typebot_session_id = data.get("sessionId")
                if typebot_session_id:
                    save_session(conversation_id, typebot_session_id)
                    print(f"[BRIDGE] Session saved: {typebot_session_id}", flush=True)
                else:
                    print(f"[BRIDGE] ERROR: No sessionId from Typebot!", flush=True)
                    return

                # Send initial messages from Typebot to Chatwoot
                messages = data.get("messages", [])
                parsed_messages = extract_messages(messages)
                merged = merge_messages(parsed_messages)
                for pm in merged:
                    if pm['type'] == 'text':
                        print(f"[BRIDGE] Sending text to Chatwoot: {pm['content'][:100]}", flush=True)
                        await send_chatwoot_message(client, conversation_id, pm['content'])
                        await asyncio.sleep(0.5)
                    elif pm['type'] == 'image':
                        print(f"[BRIDGE] Sending image to Chatwoot: {pm['url']}", flush=True)
                        await send_chatwoot_image(client, conversation_id, pm['url'])
                        await send_chatwoot_typing(client, conversation_id)
                        await asyncio.sleep(8.0)
                    elif pm['type'] == 'image_with_caption':
                        print(f"[BRIDGE] Sending image with caption to Chatwoot: {pm['url']}", flush=True)
                        await send_chatwoot_image(client, conversation_id, pm['url'], caption=pm['caption'])
                        await send_chatwoot_typing(client, conversation_id)
                        await asyncio.sleep(8.0)

                # Se o Typebot estiver esperando uma escolha (botões), mostrar as opções como menu interativo
                input_block = data.get("input")
                if input_block and input_block.get("type") == "choice input":
                    items = input_block.get("items", [])
                    if items:
                        chatwoot_items = [{"title": item.get("content"), "value": item.get("content")} for item in items]
                        content_attributes = {"items": chatwoot_items}
                        print(f"[BRIDGE] Enviando menu de opções interativo", flush=True)
                        await send_chatwoot_message(client, conversation_id, "Selecione uma opção:", content_type="input_select", content_attributes=content_attributes)
            else:
                print(f"[BRIDGE] Continuing session {typebot_session_id}", flush=True)
                response = await client.post(
                    f"{TYPEBOT_URL}/api/v1/sessions/{typebot_session_id}/continueChat",
                    json={"message": content}
                )
                print(f"[BRIDGE] Typebot continue status: {response.status_code}", flush=True)
                data = response.json()
                print(f"[BRIDGE] Typebot continue response: {json.dumps(data, ensure_ascii=False)[:800]}", flush=True)

                messages = data.get("messages", [])
                parsed_messages = extract_messages(messages)
                merged = merge_messages(parsed_messages)
                for pm in merged:
                    if pm['type'] == 'text':
                        print(f"[BRIDGE] Sending text to Chatwoot: {pm['content'][:100]}", flush=True)
                        await send_chatwoot_message(client, conversation_id, pm['content'])
                        await asyncio.sleep(0.5)
                    elif pm['type'] == 'image':
                        print(f"[BRIDGE] Sending image to Chatwoot: {pm['url']}", flush=True)
                        await send_chatwoot_image(client, conversation_id, pm['url'])
                        await send_chatwoot_typing(client, conversation_id)
                        await asyncio.sleep(8.0)
                    elif pm['type'] == 'image_with_caption':
                        print(f"[BRIDGE] Sending image with caption to Chatwoot: {pm['url']}", flush=True)
                        await send_chatwoot_image(client, conversation_id, pm['url'], caption=pm['caption'])
                        await send_chatwoot_typing(client, conversation_id)
                        await asyncio.sleep(8.0)

                # Mostra as opções se houver novo menu de botões no continueChat
                input_block = data.get("input")
                if input_block and input_block.get("type") == "choice input":
                    items = input_block.get("items", [])
                    if items:
                        chatwoot_items = [{"title": item.get("content"), "value": item.get("content")} for item in items]
                        content_attributes = {"items": chatwoot_items}
                        print(f"[BRIDGE] Enviando menu de opções interativo", flush=True)
                        await send_chatwoot_message(client, conversation_id, "Selecione uma opção:", content_type="input_select", content_attributes=content_attributes)

    except Exception as e:
        print(f"[BRIDGE] ERROR: {str(e)}", flush=True)
        traceback.print_exc()

async def send_chatwoot_message(client: httpx.AsyncClient, conversation_id: int, content: str, content_type: str = "text", content_attributes: dict = None):
    try:
        payload = {"content": content, "message_type": "outgoing"}
        if content_type != "text":
            payload["content_type"] = content_type
        if content_attributes:
            payload["content_attributes"] = content_attributes
            
        resp = await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/1/conversations/{conversation_id}/messages",
            headers={"api_access_token": BOT_TOKEN},
            json=payload
        )
        print(f"[BRIDGE] Chatwoot response: {resp.status_code} - {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[BRIDGE] ERROR sending to Chatwoot: {str(e)}", flush=True)

async def send_chatwoot_image(client: httpx.AsyncClient, conversation_id: int, image_url: str, caption: str = None):
    try:
        img_resp = await client.get(image_url)
        if img_resp.status_code != 200:
            print(f"[BRIDGE] Failed to download image from {image_url}", flush=True)
            return

        filename = image_url.split("/")[-1]
        if not filename or '.' not in filename:
            filename = 'image.jpg'

        files = {'attachments[]': (filename, img_resp.content, 'image/jpeg')}
        data = {'message_type': 'outgoing', 'private': 'false'}
        if caption:
            data['content'] = caption
        
        resp = await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/1/conversations/{conversation_id}/messages",
            headers={"api_access_token": BOT_TOKEN},
            data=data,
            files=files
        )
        print(f"[BRIDGE] Chatwoot image response: {resp.status_code} - {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[BRIDGE] ERROR sending image to Chatwoot: {str(e)}", flush=True)

async def send_chatwoot_typing(client: httpx.AsyncClient, conversation_id: int):
    try:
        await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/1/conversations/{conversation_id}/typing_status",
            headers={"api_access_token": BOT_TOKEN},
            json={"typing_status": "on"}
        )
    except Exception as e:
        pass

async def add_chatwoot_label(client: httpx.AsyncClient, conversation_id: int, label: str):
    try:
        resp = await client.post(
            f"{CHATWOOT_URL}/api/v1/accounts/1/conversations/{conversation_id}/labels",
            headers={"api_access_token": BOT_TOKEN},
            json={"labels": [label]}
        )
        print(f"[BRIDGE] Chatwoot label response: {resp.status_code}", flush=True)
    except Exception as e:
        print(f"[BRIDGE] ERROR adding label to Chatwoot: {str(e)}", flush=True)

@app.post("/webhook")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        body = await request.body()
        body_str = body.decode('utf-8', errors='replace')
        print(f"[BRIDGE] RAW BODY (first 500 chars): {body_str[:500]}", flush=True)
        if not body:
            print("[BRIDGE] Empty body received", flush=True)
            return {"status": "empty"}
        payload = json.loads(body)
        background_tasks.add_task(process_webhook, payload)
    except json.JSONDecodeError as e:
        print(f"[BRIDGE] JSON decode error: {e}", flush=True)
    except Exception as e:
        print(f"[BRIDGE] Webhook error: {e}", flush=True)
    return {"status": "ok"}

if __name__ == "__main__":
    print("[BRIDGE] Starting Typebot-Chatwoot Bridge v3 on port 8002...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8002)
