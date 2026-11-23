import time
import bcrypt
import jwt
from app.core.config import SECRET_KEY, SESSION_HOURS

_DUMMY = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()


def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()


def verify_pw(p: str, h: str | None) -> bool:
    try:
        return bcrypt.checkpw(p.encode()[:72], (h or _DUMMY).encode()) and h is not None
    except ValueError:
        return False


def make_token(uid: int) -> str:
    return jwt.encode({"sub": str(uid), "exp": int(time.time()) + SESSION_HOURS * 3600}, SECRET_KEY, "HS256")


def read_token(t: str) -> int | None:
    try:
        return int(jwt.decode(t, SECRET_KEY, algorithms=["HS256"])["sub"])
    except Exception:
        return None
