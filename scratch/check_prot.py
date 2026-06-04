from app.database import SessionLocal
from app import models
from sqlalchemy import text

db = SessionLocal()
db.execute(text("SET LOCAL app.bypass_rls = 'on';"))
ps = db.query(models.Protocolo).all()
print([p.protocolo for p in ps[-5:]])
