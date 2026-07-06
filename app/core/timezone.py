from datetime import datetime, date, timezone, timedelta

# Fuso horário de Brasília (UTC-3 fixo, sem horário de verão)
BRT = timezone(timedelta(hours=-3), name="America/Sao_Paulo")

def agora_br() -> datetime:
    """Retorna o datetime atual no fuso horário de Brasília."""
    return datetime.now(BRT)

def hoje_br() -> date:
    """Retorna a data atual no fuso horário de Brasília."""
    return datetime.now(BRT).date()
