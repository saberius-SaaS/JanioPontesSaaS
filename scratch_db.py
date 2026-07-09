import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app import models
from sqlalchemy import text as sa_text

db = SessionLocal()
db.execute(sa_text("SET LOCAL app.bypass_rls = 'on';"))

licencas = db.query(models.LicencaLocalizacao).filter(models.LicencaLocalizacao.status == "INDETERMINADO").order_by(models.LicencaLocalizacao.cliente_id).all()

from collections import defaultdict
por_cliente = defaultdict(list)

for l in licencas:
    por_cliente[l.cliente_id].append(l)

excluidos = 0
for cliente_id, lista in por_cliente.items():
    if len(lista) > 1:
        print(f"Cliente {cliente_id} tem {len(lista)} licencas indeterminadas.")
        lista.sort(key=lambda x: (x.arquivo_url is not None, x.id), reverse=True)
        para_excluir = lista[1:]
        for p in para_excluir:
            db.delete(p)
            excluidos += 1

db.commit()
print(f"Total de registros excluidos: {excluidos}")
