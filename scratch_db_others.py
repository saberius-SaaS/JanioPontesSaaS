import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.database import SessionLocal
from app import models
from sqlalchemy import text as sa_text

db = SessionLocal()
db.execute(sa_text("SET LOCAL app.bypass_rls = 'on';"))

modelos = [
    models.AlvaraSanitario,
    models.AVCB,
    models.InscricaoMunicipal
]

total_excluidos = 0

for Model in modelos:
    docs = db.query(Model).filter(Model.status == "INDETERMINADO").order_by(Model.cliente_id).all()
    from collections import defaultdict
    por_cliente = defaultdict(list)

    for d in docs:
        por_cliente[d.cliente_id].append(d)

    for cliente_id, lista in por_cliente.items():
        if len(lista) > 1:
            lista.sort(key=lambda x: (x.arquivo_url is not None, x.id), reverse=True)
            para_excluir = lista[1:]
            for p in para_excluir:
                db.delete(p)
                total_excluidos += 1

db.commit()
print(f"Total de registros excluidos nas outras tabelas: {total_excluidos}")
