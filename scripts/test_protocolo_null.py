import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.database import SessionLocal
from sqlalchemy import text, not_, or_
from app.models import Protocolo

db = SessionLocal()
db.execute(text("SET SESSION app.bypass_rls = 'on';"))
print('Total Nao Lidos:', db.query(Protocolo).filter(
    Protocolo.conf_recto == None,
    Protocolo.status_envio == 'ENVIADO',
    Protocolo.acao.ilike('%ENVIAR%'),
    or_(Protocolo.link_arquivo == None, not_(Protocolo.link_arquivo.startswith('SEM_ENVIO:')))
).count())
