"""Create tables and the single elderly demo account."""
import os
from sqlalchemy import select
import app.models as m
from app.core.security import hash_pw
from app.database.db import Base, SessionLocal, engine

Base.metadata.create_all(engine)
users = [("Demo Elderly", "elder@example.com", "ELDERLY", "Demo12345!")]
with SessionLocal() as db:
    for name, email, role, pw in users:
        if db.scalar(select(m.User.id).where(m.User.email == email)):
            continue
        u = m.User(name=name, email=email, role=role, password_hash=hash_pw(pw), timezone="Asia/Kolkata")
        db.add(u)
        db.flush()
        if role == "ELDERLY":
            db.add(m.ElderlyProfile(user_id=u.id))
    db.commit()
print("Seeded elderly demo account: elder@example.com / Demo12345!")
