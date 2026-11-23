from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.deps import get_db, require
from app.models import AuditEvent, Role, User, VolunteerProfile, VolunteerRequest
from app.schemas import FlagIn
from app.services import audit, get_request, move, notify, ser_request
from app.utils import out

router = APIRouter(prefix="/admin", tags=["admin"])
ADM = Depends(require(Role.ADMIN))


@router.get("/users")
def users(user=ADM, db=Depends(get_db)):
    return [out(u, "id", "name", "email", "role", "is_active", "created_at")
            for u in db.scalars(select(User).order_by(User.id))]


@router.post("/users/{uid}/active")
def set_active(uid: int, d: FlagIn, user=ADM, db=Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Not found")
    if u.id == user.id:
        raise HTTPException(409, "You cannot deactivate yourself")
    u.is_active = d.value
    audit(db, user.id, "USER_ACTIVE" if d.value else "USER_DEACTIVATED", uid)
    db.commit()
    return out(u, "id", "is_active")


@router.get("/volunteers")
def volunteers(user=ADM, db=Depends(get_db)):
    rows = db.execute(select(User, VolunteerProfile).join(VolunteerProfile, VolunteerProfile.user_id == User.id))
    return [{"id": u.id, "name": u.name, "email": u.email, "service_area": p.service_area, "verified": p.verified}
            for u, p in rows]


@router.post("/volunteers/{uid}/verify")
def verify(uid: int, d: FlagIn, user=ADM, db=Depends(get_db)):
    p = db.scalar(select(VolunteerProfile).where(VolunteerProfile.user_id == uid))
    if not p:
        raise HTTPException(404, "Volunteer not found")
    p.verified = d.value
    audit(db, user.id, "VOLUNTEER_VERIFIED" if d.value else "VOLUNTEER_UNVERIFIED", uid)
    notify(db, uid, "ACCOUNT", "Your volunteer verification status was updated.")
    db.commit()
    return {"id": uid, "verified": p.verified}


@router.get("/requests")
def requests(user=ADM, db=Depends(get_db)):
    return [ser_request(db, r, user) for r in db.scalars(select(VolunteerRequest).order_by(VolunteerRequest.id.desc()).limit(100))]


@router.post("/requests/{rid}/cancel")
def moderate_cancel(rid: int, user=ADM, db=Depends(get_db)):
    r = get_request(db, rid)
    move(db, rid, ["OPEN", "ACCEPTED", "IN_PROGRESS"], "CANCELLED")
    audit(db, user.id, "REQUEST_CANCELLED", rid)
    notify(db, r.elderly_id, "REQUEST", "A help request was cancelled by an administrator.")
    db.commit()
    db.refresh(r)
    return ser_request(db, r, user)


@router.get("/audit")
def audit_log(user=ADM, db=Depends(get_db)):
    return [out(a, "id", "actor_id", "action", "target", "created_at")
            for a in db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100))]
