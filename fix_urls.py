import sys
import os
import re
from datetime import date
from urllib.parse import unquote

# Configura o path para importar módulos da aplicação
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.tarefa import Protocolo
from app.core.storage_service import storage_service, GCS_BUCKET_NAME
from sqlalchemy import func

def fix_signed_urls():
    db = SessionLocal()
    db.info["bypass_rls"] = True
    # Busca protocolos pendentes de leitura que tenham links do GCS
    protocolos = db.query(Protocolo).filter(
        Protocolo.conf_recto.is_(None),
        Protocolo.link_arquivo.isnot(None),
        Protocolo.link_arquivo.like('%storage.googleapis.com%')
    ).all()
    
    if not protocolos:
        print("Nenhum protocolo encontrado hoje com link do Google Cloud Storage.")
        return

    client = storage_service._get_client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    
    atualizados = 0
    
    for prot in protocolos:
        # Extrair justificativas e separar links
        link_bruto = prot.link_arquivo
        
        # Procurar se há texto de comunicação/justificativa junto (ex: [NOTA: ok])
        obs_match = re.search(r'(\[.*?\])$', link_bruto)
        observacao = " " + obs_match.group(1) if obs_match else ""
        
        base_links = re.sub(r'\[.*?\]$', '', link_bruto).strip()
        links = [l.strip() for l in base_links.split(' | ') if l.strip()]
        
        novos_links = []
        alterou = False
        
        for link in links:
            if "storage.googleapis.com" in link and "Expires=" in link:
                try:
                    base_url = link.split('?')[0]
                    # formato: https://storage.googleapis.com/bucket-name/folder/file.pdf
                    parts = base_url.split('/')
                    # partes da URL para achar o path do objeto
                    bucket_index = parts.index(GCS_BUCKET_NAME)
                    blob_path = "/".join(parts[bucket_index+1:])
                    blob_path = unquote(blob_path)
                    
                    blob = bucket.blob(blob_path)
                    # Gera a nova URL assinada com a correção que fizemos
                    novo_link = storage_service._generate_signed_url(blob)
                    novos_links.append(novo_link)
                    alterou = True
                except Exception as e:
                    print(f"Erro ao processar link {link}: {e}")
                    novos_links.append(link)
            else:
                novos_links.append(link)
                
        if alterou:
            novo_link_completo = " | ".join(novos_links) + observacao
            prot.link_arquivo = novo_link_completo.strip()
            atualizados += 1
            print(f"Protocolo {prot.protocolo} corrigido.")
            
    if atualizados > 0:
        db.commit()
        print(f"Sucesso: {atualizados} protocolos atualizados no banco de dados.")
    else:
        print("Nenhum link precisou ser atualizado.")
        
    db.close()

if __name__ == "__main__":
    fix_signed_urls()
