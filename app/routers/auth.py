import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from app.core.config import PRODUCTION, SESSION_HOURS
from app.core.security import hash_pw, make_token, verify_pw
from app.deps import current_user, get_db
from app.models import ElderlyProfile, User, VolunteerProfile
from app.schemas import LoginIn, RegisterIn, UserPatch
from app.services import audit
from app.utils import out, patch

router = APIRouter(tags=["auth"])
FIELDS = ("id", "name", "email", "phone", "role", "timezone")
_fails: dict[str, list[float]] = {}  # per-instance limiter (best effort on serverless)


def _limited(key):
    t = time.time()
    _fails[key] = [x for x in _fails.get(key, []) if t - x < 300]
    return len(_fails[key]) >= 5


@router.post("/auth/register", status_code=201)
def register(d: RegisterIn, db=Depends(get_db)):
    email = d.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    u = User(name=d.name, email=email, phone=d.phone, password_hash=hash_pw(d.password),
             role=d.role, timezone=d.timezone)
    db.add(u)
    db.flush()
    if d.role == "ELDERLY":
        db.add(ElderlyProfile(user_id=u.id))
    if d.role == "VOLUNTEER":
        db.add(VolunteerProfile(user_id=u.id))
    db.commit()
    return out(u, *FIELDS)


@router.post("/auth/login")
def login(d: LoginIn, request: Request, response: Response, db=Depends(get_db)):
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "?"))
    key = f"{ip}|{d.email.lower()}"
    if _limited(key):
        raise HTTPException(429, "Too many failed attempts. Please wait a few minutes.")
    u = db.scalar(select(User).where(User.email == d.email.lower()))
    if not verify_pw(d.password, u.password_hash if u else None) or not u.is_active:
        _fails.setdefault(key, []).append(time.time())
        raise HTTPException(401, "Incorrect email or password")
    _fails.pop(key, None)
    response.set_cookie("session", make_token(u.id), httponly=True, samesite="lax",
                        secure=PRODUCTION, max_age=SESSION_HOURS * 3600, path="/")
    return out(u, *FIELDS)


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie("session", path="/")


@router.get("/auth/me")
def me(u=Depends(current_user)):
    return out(u, *FIELDS)


@router.get("/users/me")
def get_me(u=Depends(current_user)):
    return out(u, *FIELDS)


@router.patch("/users/me")
def patch_me(d: UserPatch, u=Depends(current_user), db=Depends(get_db)):
    patch(u, d.model_dump(exclude_unset=True), nonnull=("name", "timezone"))
    db.commit()
    return out(u, *FIELDS)


@router.delete("/users/me", status_code=204)
def deactivate(response: Response, u=Depends(current_user), db=Depends(get_db)):
    """Accounts are deactivated (login disabled); an admin can purge data on request."""
    u.is_active = False
    audit(db, u.id, "ACCOUNT_DEACTIVATED", u.id)
    db.commit()
    response.delete_cookie("session", path="/")
