from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, update
from app.models import (AuditEvent, FamilyConnection, Notification, User, VolunteerRequest)


def utcnow():
    return datetime.now(timezone.utc)


def audit(db, actor_id, action, target=""):
    db.add(AuditEvent(actor_id=actor_id, action=action, target=str(target)))


def notify(db, user_id, kind, message, dedupe_key=None) -> bool:
    if dedupe_key and db.scalar(select(Notification.id).where(Notification.dedupe_key == dedupe_key)):
        return False
    db.add(Notification(user_id=user_id, type=kind, message=message[:200], dedupe_key=dedupe_key))
    return True


def approved_family_ids(db, elderly_id):
    return list(db.scalars(select(FamilyConnection.family_id).where(
        FamilyConnection.elderly_id == elderly_id, FamilyConnection.status == "APPROVED")))


def get_request(db, rid) -> VolunteerRequest:
    r = db.get(VolunteerRequest, rid)
    if not r:
        raise HTTPException(404, "Request not found")
    return r


def move(db, rid, frm, to, extra=(), **vals):
    """Atomic compare-and-set status change: only one caller can win a race."""
    res = db.execute(update(VolunteerRequest).where(
        VolunteerRequest.id == rid, VolunteerRequest.status.in_(frm), *extra).values(status=to, **vals))
    if res.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "This request cannot be changed that way right now")


def ser_request(db, r, viewer):
    d = {"id": r.id, "category": r.category, "status": r.status,
         "requested_time": r.requested_time, "created_at": r.created_at}
    from app.utils import val
    d = {k: val(v) for k, v in d.items()}
    if viewer.role == "FAMILY":
        return d
    d.update(description=r.description, location=r.location)
    if viewer.role in ("ELDERLY", "ADMIN") and r.volunteer_id:
        v = db.get(User, r.volunteer_id)
        d["volunteer_name"] = v.name if v else None
    if viewer.role == "ADMIN":
        e = db.get(User, r.elderly_id)
        d["elderly_name"] = e.name if e else None
    if viewer.role == "VOLUNTEER":
        mine = r.volunteer_id == viewer.id
        e = db.get(User, r.elderly_id) if mine else None
        d["elderly_name"] = e.name if e else "Neighbour"
        d["elderly_phone"] = e.phone if e else None
        d["mine"] = mine
    return d
