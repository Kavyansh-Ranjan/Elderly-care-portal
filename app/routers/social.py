"""Elderly-only social features for the Review 2 prototype."""
import hmac
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from app.deps import current_user, get_db, require
from app.models import Medicine, MedicineSchedule, Notification, Role, VolunteerRequest
from app.schemas import HelpIn
from app.services import get_request, move, notify, ser_request, utcnow
from app.utils import aware, out

router = APIRouter(tags=["elderly support"])
ELD = Depends(require(Role.ELDERLY))


@router.get("/volunteer-requests")
def list_requests(user=ELD, db=Depends(get_db)):
    rows = db.scalars(
        select(VolunteerRequest)
        .where(VolunteerRequest.elderly_id == user.id)
        .order_by(VolunteerRequest.id.desc())
        .limit(100)
    )
    return [ser_request(db, r, user) for r in rows]


@router.post("/volunteer-requests", status_code=201)
def create_request(d: HelpIn, user=ELD, db=Depends(get_db)):
    when = aware(d.requested_time, user.timezone)
    if when < utcnow() - timedelta(minutes=5):
        raise HTTPException(422, "Requested time must be in the future")
    r = VolunteerRequest(
        elderly_id=user.id,
        category=d.category,
        description=d.description,
        requested_time=when,
        location=d.location,
    )
    db.add(r)
    db.commit()
    return ser_request(db, r, user)


@router.post("/volunteer-requests/{rid}/cancel")
def cancel_request(rid: int, user=ELD, db=Depends(get_db)):
    r = get_request(db, rid)
    if r.elderly_id != user.id:
        raise HTTPException(404, "Request not found")
    move(db, rid, ["OPEN", "ACCEPTED"], "CANCELLED")
    if r.volunteer_id:
        notify(db, r.volunteer_id, "REQUEST", "A request you accepted was cancelled.")
    db.commit()
    db.refresh(r)
    return ser_request(db, r, user)


@router.get("/notifications")
def notifications(user=ELD, db=Depends(get_db)):
    rows = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(50)
    )
    return [out(n, "id", "type", "message", "read", "created_at") for n in rows]


@router.post("/notifications/{nid}/read")
def read_notification(nid: int, user=ELD, db=Depends(get_db)):
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Not found")
    n.read = True
    db.commit()
    return out(n, "id", "read")


@router.get("/internal/reminders")
def reminders(request: Request, db=Depends(get_db)):
    secret = os.getenv("CRON_SECRET")
    if not secret:
        raise HTTPException(503, "CRON_SECRET is not configured")
    if not hmac.compare_digest(request.headers.get("authorization", ""), f"Bearer {secret}"):
        raise HTTPException(401, "Unauthorized")
    now, created = utcnow(), 0
    from app.models import Appointment
    for a in db.scalars(select(Appointment).where(
        Appointment.starts_at > now,
        Appointment.starts_at <= now + timedelta(hours=24),
    )):
        created += notify(
            db, a.elderly_id, "REMINDER",
            f"Reminder: appointment '{a.title}' is coming up.",
            f"appt:{a.id}:{a.starts_at.date().isoformat()}",
        )
    today = now.date()
    rows = db.execute(
        select(Medicine.elderly_id, func.count(MedicineSchedule.id))
        .join(MedicineSchedule, MedicineSchedule.medicine_id == Medicine.id)
        .where(Medicine.active.is_(True))
        .group_by(Medicine.elderly_id)
    ).all()
    for uid, n in rows:
        created += notify(
            db, uid, "REMINDER",
            f"You have {n} medicine time(s) scheduled today.",
            f"meds:{uid}:{today}",
        )
    db.commit()
    return {"created": created}
