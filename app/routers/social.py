import hmac
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from app.deps import current_user, get_db, require
from app.models import (Appointment, DailyCheckIn, EmergencyContact, FamilyConnection, Medicine,
                        MedicineSchedule, Notification, Role, User, VolunteerProfile, VolunteerRequest)
from app.schemas import FamilyReqIn, HelpIn, VolProfileIn
from app.services import (approved_family_ids, audit, get_request, move, notify, ser_request, utcnow)
from app.utils import aware, local_today, out, patch

router = APIRouter(tags=["social"])
ELD, FAM, VOL = (Depends(require(r)) for r in (Role.ELDERLY, Role.FAMILY, Role.VOLUNTEER))


# ---------------- family connections
def conn_out(c, db, viewer):
    other = db.get(User, c.family_id if viewer.role == "ELDERLY" else c.elderly_id)
    return {"id": c.id, "status": c.status, "name": other.name, "email": other.email if viewer.role == "ELDERLY" else None}


@router.post("/family-connections", status_code=202)
def request_connection(d: FamilyReqIn, user=FAM, db=Depends(get_db)):
    e = db.scalar(select(User).where(User.email == d.elderly_email.lower(), User.role == "ELDERLY",
                                     User.is_active.is_(True)))
    if e:  # same reply either way, so emails cannot be probed
        c = db.scalar(select(FamilyConnection).where(FamilyConnection.family_id == user.id,
                                                     FamilyConnection.elderly_id == e.id))
        if not c:
            db.add(FamilyConnection(family_id=user.id, elderly_id=e.id))
        elif c.status in ("REJECTED", "REVOKED"):
            c.status = "PENDING"
        else:
            return {"message": "Request already exists."}
        notify(db, e.id, "FAMILY", f"{user.name} asked to connect as family.")
        db.commit()
    return {"message": "If that person has an elderly account, they have been asked to approve."}


@router.get("/family-connections")
def list_connections(user=Depends(require(Role.ELDERLY, Role.FAMILY)), db=Depends(get_db)):
    col = FamilyConnection.elderly_id if user.role == "ELDERLY" else FamilyConnection.family_id
    return [conn_out(c, db, user) for c in db.scalars(select(FamilyConnection).where(col == user.id)
                                                     .order_by(FamilyConnection.id.desc()))]


def _decide(cid, status, user, db):
    c = db.get(FamilyConnection, cid)
    if not c or c.elderly_id != user.id:
        raise HTTPException(404, "Not found")
    if c.status != "PENDING":
        raise HTTPException(409, "This request was already answered")
    c.status = status
    notify(db, c.family_id, "FAMILY", f"{user.name} {'approved' if status == 'APPROVED' else 'declined'} your request.")
    db.commit()
    return conn_out(c, db, user)


@router.post("/family-connections/{cid}/approve")
def approve(cid: int, user=ELD, db=Depends(get_db)):
    return _decide(cid, "APPROVED", user, db)


@router.post("/family-connections/{cid}/reject")
def reject(cid: int, user=ELD, db=Depends(get_db)):
    return _decide(cid, "REJECTED", user, db)


@router.delete("/family-connections/{cid}", status_code=204)
def revoke(cid: int, user=Depends(require(Role.ELDERLY, Role.FAMILY)), db=Depends(get_db)):
    c = db.get(FamilyConnection, cid)
    if not c or user.id not in (c.elderly_id, c.family_id):
        raise HTTPException(404, "Not found")
    ok = ("APPROVED",) if user.role == "ELDERLY" else ("APPROVED", "PENDING")
    if c.status not in ok:
        raise HTTPException(409, "Nothing to revoke")
    c.status = "REVOKED"
    notify(db, c.family_id if user.role == "ELDERLY" else c.elderly_id, "FAMILY", "A family connection was ended.")
    db.commit()


@router.get("/family/elderly")
def family_view(user=FAM, db=Depends(get_db)):
    res = []
    elders = db.scalars(select(User).join(FamilyConnection, FamilyConnection.elderly_id == User.id).where(
        FamilyConnection.family_id == user.id, FamilyConnection.status == "APPROVED", User.is_active.is_(True)))
    for e in elders:
        last = db.scalar(select(DailyCheckIn).where(DailyCheckIn.elderly_id == e.id)
                         .order_by(DailyCheckIn.day.desc()).limit(1))
        today = last is not None and last.day == local_today(e)
        appts = db.scalars(select(Appointment).where(Appointment.elderly_id == e.id, Appointment.starts_at >= utcnow())
                           .order_by(Appointment.starts_at).limit(3))
        res.append({
            "id": e.id, "name": e.name, "timezone": e.timezone,
            "check_in_status": last.status if today else "UNKNOWN",
            "last_check_in": last.day.isoformat() if last else None,
            "appointments": [out(a, "title", "starts_at", "location") for a in appts],
            "medicines": [m for m in db.scalars(select(Medicine.name).where(Medicine.elderly_id == e.id, Medicine.active.is_(True)))],
            "contacts": [out(c, "name", "phone") for c in db.scalars(select(EmergencyContact).where(
                EmergencyContact.elderly_id == e.id).order_by(EmergencyContact.priority))],
            "requests": [ser_request(db, r, user) for r in db.scalars(select(VolunteerRequest).where(
                VolunteerRequest.elderly_id == e.id).order_by(VolunteerRequest.id.desc()).limit(5))],
        })
    return res


# ---------------- volunteer profile & requests
@router.get("/volunteer/profile")
def vol_profile(user=VOL, db=Depends(get_db)):
    p = db.scalar(select(VolunteerProfile).where(VolunteerProfile.user_id == user.id))
    return out(p, "availability", "service_area", "verified")


@router.put("/volunteer/profile")
def set_vol_profile(d: VolProfileIn, user=VOL, db=Depends(get_db)):
    p = db.scalar(select(VolunteerProfile).where(VolunteerProfile.user_id == user.id))
    patch(p, d.model_dump())
    db.commit()
    return out(p, "availability", "service_area", "verified")


def _verified(db, user):
    p = db.scalar(select(VolunteerProfile).where(VolunteerProfile.user_id == user.id))
    return bool(p and p.verified)


@router.get("/volunteer-requests")
def list_requests(user=Depends(current_user), db=Depends(get_db)):
    q = select(VolunteerRequest).order_by(VolunteerRequest.id.desc()).limit(100)
    if user.role == "ELDERLY":
        q = q.where(VolunteerRequest.elderly_id == user.id)
    elif user.role == "FAMILY":
        ids = select(FamilyConnection.elderly_id).where(FamilyConnection.family_id == user.id,
                                                        FamilyConnection.status == "APPROVED")
        q = q.where(VolunteerRequest.elderly_id.in_(ids))
    elif user.role == "VOLUNTEER":
        if not _verified(db, user):
            return []
        q = q.where(or_(VolunteerRequest.status == "OPEN", VolunteerRequest.volunteer_id == user.id))
    return [ser_request(db, r, user) for r in db.scalars(q)]


@router.post("/volunteer-requests", status_code=201)
def create_request(d: HelpIn, user=ELD, db=Depends(get_db)):
    when = aware(d.requested_time, user.timezone)
    if when < utcnow() - timedelta(minutes=5):
        raise HTTPException(422, "Requested time must be in the future")
    r = VolunteerRequest(elderly_id=user.id, category=d.category, description=d.description,
                         requested_time=when, location=d.location)
    db.add(r)
    db.commit()
    return ser_request(db, r, user)


def _act(rid, user, db, frm, to, who, msg):
    r = get_request(db, rid)
    if who == "volunteer" and r.volunteer_id != user.id:
        raise HTTPException(403, "This request is not assigned to you")
    extra = (VolunteerRequest.volunteer_id == user.id,) if who == "volunteer" else ()
    move(db, rid, frm, to, extra)
    notify(db, r.elderly_id, "REQUEST", msg)
    db.commit()
    db.refresh(r)
    return ser_request(db, r, user)


@router.post("/volunteer-requests/{rid}/accept")
def accept(rid: int, user=VOL, db=Depends(get_db)):
    r = get_request(db, rid)
    if not _verified(db, user):
        raise HTTPException(403, "Your volunteer account is not verified yet")
    move(db, rid, ["OPEN"], "ACCEPTED", volunteer_id=user.id)
    notify(db, r.elderly_id, "REQUEST", "A volunteer accepted your help request.")
    db.commit()
    db.refresh(r)
    return ser_request(db, r, user)


@router.post("/volunteer-requests/{rid}/start")
def start(rid: int, user=VOL, db=Depends(get_db)):
    return _act(rid, user, db, ["ACCEPTED"], "IN_PROGRESS", "volunteer", "Your volunteer has started your request.")


@router.post("/volunteer-requests/{rid}/complete")
def complete(rid: int, user=VOL, db=Depends(get_db)):
    return _act(rid, user, db, ["IN_PROGRESS"], "COMPLETED", "volunteer", "Your help request was completed.")


@router.post("/volunteer-requests/{rid}/cancel")
def cancel(rid: int, user=ELD, db=Depends(get_db)):
    r = get_request(db, rid)
    if r.elderly_id != user.id:
        raise HTTPException(404, "Request not found")
    vol = r.volunteer_id
    move(db, rid, ["OPEN", "ACCEPTED"], "CANCELLED")
    if vol:
        notify(db, vol, "REQUEST", "A request you accepted was cancelled.")
    db.commit()
    db.refresh(r)
    return ser_request(db, r, user)


# ---------------- notifications
@router.get("/notifications")
def notifications(user=Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.id.desc()).limit(50))
    return [out(n, "id", "type", "message", "read", "created_at") for n in rows]


@router.post("/notifications/{nid}/read")
def read(nid: int, user=Depends(current_user), db=Depends(get_db)):
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Not found")
    n.read = True
    db.commit()
    return out(n, "id", "read")


# ---------------- reminders (Vercel Cron). Idempotent: dedupe keys make retries safe.
@router.get("/internal/reminders")
def reminders(request: Request, db=Depends(get_db)):
    secret = os.getenv("CRON_SECRET")
    if not secret:
        raise HTTPException(503, "CRON_SECRET is not configured")
    if not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {secret}"):
        raise HTTPException(401, "Unauthorized")
    now, created = utcnow(), 0
    for a in db.scalars(select(Appointment).where(Appointment.starts_at > now,
                                                  Appointment.starts_at <= now + timedelta(hours=24))):
        created += notify(db, a.elderly_id, "REMINDER", f"Reminder: appointment '{a.title}' is coming up.",
                          f"appt:{a.id}:{val_day(a.starts_at)}")
    today = now.date()
    rows = db.execute(select(Medicine.elderly_id, func.count(MedicineSchedule.id))
                      .join(MedicineSchedule, MedicineSchedule.medicine_id == Medicine.id)
                      .where(Medicine.active.is_(True)).group_by(Medicine.elderly_id)).all()
    for uid, n in rows:
        created += notify(db, uid, "REMINDER", f"You have {n} medicine time(s) scheduled today.", f"meds:{uid}:{today}")
    db.commit()
    return {"created": created}


def val_day(dt):
    return dt.date().isoformat()
