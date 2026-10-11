from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException


def val(v):
    if isinstance(v, datetime):
        v = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(v, date):
        return v.isoformat()
    return v


def out(o, *fields):
    return {k: val(getattr(o, k)) for k in fields}


def aware(dt: datetime, tz: str) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(timezone.utc)


def local_today(user) -> date:
    return datetime.now(ZoneInfo(user.timezone)).date()


def patch(obj, data: dict, nonnull=()):
    for k, v in data.items():
        if v is None and k in nonnull:
            raise HTTPException(422, f"{k} cannot be empty")
        setattr(obj, k, v)
