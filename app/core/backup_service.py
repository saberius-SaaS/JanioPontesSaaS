"""
Backup do banco PostgreSQL para o Google Drive.
Exporta todas as tabelas como CSV, compacta em ZIP e faz upload
na pasta BACKUPS_SISTEMA do Drive corporativo.
"""
from app.core.timezone import agora_br, hoje_br
import io
import csv
import zipfile
import logging
from datetime import datetime

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BACKUP_FOLDER_ID = "1gFvKQhakxFtEWQTv5vzeI92wegeGfmdj"

TABELAS_SISTEMA = [
    "tenants", "usuarios", "usuarios_equipes",
    "clientes", "regras_obrigacoes", "tarefas",
    "historico_tarefas", "protocolos", "equipes",
]


def gerar_backup_zip(db: Session) -> tuple[bytes, str]:
    """
    Exporta as tabelas do banco como CSVs e retorna
    um ZIP em memória com todos os arquivos.
    """
    try:
        db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
    except Exception:
        pass

    agora = agora_br()
    nome_arquivo = f"backup_jpsaas_{agora.strftime('%Y%m%d_%H%M%S')}.zip"

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        inspector = inspect(db.bind)
        tabelas_existentes = inspector.get_table_names()

        for tabela in TABELAS_SISTEMA:
            if tabela not in tabelas_existentes:
                logger.warning(f"[BACKUP] Tabela '{tabela}' nao existe, pulando.")
                continue

            try:
                result = db.execute(text(f"SELECT * FROM {tabela}"))
                colunas = list(result.keys())
                linhas = result.fetchall()

                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(colunas)
                for linha in linhas:
                    writer.writerow(list(linha))

                zf.writestr(f"{tabela}.csv", csv_buffer.getvalue())
                logger.info(f"[BACKUP] {tabela}: {len(linhas)} registros exportados.")
            except Exception as e:
                logger.error(f"[BACKUP] Erro ao exportar '{tabela}': {e}")
                zf.writestr(f"{tabela}_ERRO.txt", str(e))

        # Metadados do backup
        meta = f"Data: {agora.isoformat()}\nTabelas: {', '.join(TABELAS_SISTEMA)}\n"
        zf.writestr("_meta.txt", meta)

    zip_buffer.seek(0)
    return zip_buffer.getvalue(), nome_arquivo


def upload_backup_drive(zip_bytes: bytes, nome_arquivo: str) -> str:
    """
    Faz upload do ZIP de backup para a pasta BACKUPS_SISTEMA no Google Drive.
    Retorna o link do arquivo.
    """
    from googleapiclient.http import MediaIoBaseUpload
    from app.core.drive_service import drive_service

    service = drive_service._get_service()

    file_metadata = {
        'name': nome_arquivo,
        'parents': [BACKUP_FOLDER_ID],
        'mimeType': 'application/zip'
    }

    media = MediaIoBaseUpload(
        io.BytesIO(zip_bytes),
        mimetype='application/zip',
        resumable=True
    )

    result = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    link = result.get('webViewLink', f"https://drive.google.com/file/d/{result.get('id')}/view")
    logger.info(f"[BACKUP] Upload concluido: {nome_arquivo} -> {link}")
    return link


def limpar_backups_antigos(dias_retencao: int = 30):
    """
    Remove backups com mais de N dias da pasta do Drive
    para evitar acumulo infinito.
    """
    from app.core.drive_service import drive_service
    from datetime import timedelta

    service = drive_service._get_service()
    limite = (agora_br() - timedelta(days=dias_retencao)).isoformat() + "Z"

    try:
        resultados = service.files().list(
            q=f"'{BACKUP_FOLDER_ID}' in parents and name contains 'backup_jpsaas_' and createdTime < '{limite}'",
            fields='files(id, name, createdTime)',
            orderBy='createdTime'
        ).execute()

        arquivos = resultados.get('files', [])
        for arq in arquivos:
            service.files().delete(fileId=arq['id']).execute()
            logger.info(f"[BACKUP] Removido backup antigo: {arq['name']}")

        return len(arquivos)
    except Exception as e:
        logger.error(f"[BACKUP] Erro ao limpar backups antigos: {e}")
        return 0
