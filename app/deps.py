from fastapi import Depends, HTTPException, Request
from app.core.security import read_token
from app.database.db import SessionLocal
from app.models import Role, User


def get_db():
    with SessionLocal() as db:
        yield db


def csrf(request: Request):
    # Custom header cannot be sent cross-site without CORS pre-flight; cookies are also SameSite=Lax.
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-requested-with") != "fetch":
        raise HTTPException(403, "Missing CSRF header")


def optional_user(request: Request, db=Depends(get_db)):
    t = request.cookies.get("session")
    uid = read_token(t) if t else None
    u = db.get(User, uid) if uid else None
    return u if u and u.is_active else None


def current_user(u=Depends(optional_user)):
    if not u:
        raise HTTPException(401, "Please log in")
    return u


def require(*roles: Role):
    allowed = {r.value for r in roles}

    def dep(u=Depends(current_user)):
        if u.role not in allowed:
            raise HTTPException(403, "You do not have access to this")
        return u

    return dep
