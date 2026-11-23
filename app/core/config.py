import os

PRODUCTION = bool(os.getenv("VERCEL")) or os.getenv("ENV") == "production"
_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
for _p in ("postgres://", "postgresql://"):
    if _url.startswith(_p):
        _url = "postgresql+psycopg://" + _url[len(_p):]
DATABASE_URL = _url
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret")
if PRODUCTION and SECRET_KEY == "dev-insecure-secret":
    raise RuntimeError("SECRET_KEY must be set in production")
SESSION_HOURS = 8
