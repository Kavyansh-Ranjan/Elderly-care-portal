import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["CRON_SECRET"] = "cron"
import pytest
from fastapi.testclient import TestClient
from app.core.security import hash_pw
from app.database.db import Base, SessionLocal, engine
from app.main import app
from app.models import User


@pytest.fixture(autouse=True)
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture
def make():
    def _make(role, name=None):
        c = TestClient(app, headers={"X-Requested-With": "fetch"})
        email = f"{name or role.lower()}@example.com"
        if role == "ADMIN":
            with SessionLocal() as s:
                s.add(User(name="Admin", email=email, role="ADMIN", password_hash=hash_pw("password1")))
                s.commit()
        else:
            assert c.post("/auth/register", json={"name": name or role, "email": email, "password": "password1", "role": role}).status_code == 201
        assert c.post("/auth/login", json={"email": email, "password": "password1"}).status_code == 200
        c.email = email
        return c
    return _make
