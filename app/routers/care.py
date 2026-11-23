from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from app.deps import get_db, require
from app.models import (Appointment, DailyCheckIn, ElderlyProfile, EmergencyContact, Medicine,
                        MedicineSchedule, Role)
from app.schemas import (AppointmentIn, AppointmentPatch, CheckInIn, ContactIn, ContactPatch, MedicineIn,
                         MedicinePatch, ProfileIn, ReorderIn)
from app.services import approved_family_ids, notify, utcnow
from app.utils import aware, local_today, out, patch

router = APIRouter(tags=["care"])
EL = Depends(require(Role.ELDERLY))


def own(db, model, oid, user):
    o = db.get(model, oid)
    if not o or o.elderly_id != user.id:
        raise HTTPException(404, "Not found")
    return o


# ---- profile
def _profile(db, user):
    p = db.scalar(select(ElderlyProfile).where(ElderlyProfile.user_id == user.id))
    if not p:
        p = ElderlyProfile(user_id=user.id)
        db.add(p)
        db.flush()
    return p


@router.get("/elderly/profile")
def get_profile(user=EL, db=Depends(get_db)):
    p = _profile(db, user)
    db.commit()
    return out(p, "date_of_birth", "address", "accessibility_notes")


@router.patch("/elderly/profile")
def patch_profile(d: ProfileIn, user=EL, db=Depends(get_db)):
    p = _profile(db, user)
    patch(p, d.model_dump(exclude_unset=True))
    db.commit()
    return out(p, "date_of_birth", "address", "accessibility_notes")


# ---- medicines
def med_out(m):
    d = out(m, "id", "name", "instructions", "start_date", "end_date", "active")
    d["schedules"] = [out(s, "time", "recurrence", "timezone") for s in m.schedules]
    return d


def _check_dates(m):
    if m.start_date and m.end_date and m.end_date < m.start_date:
        raise HTTPException(422, "End date cannot be before start date")


@router.get("/medicines")
def list_medicines(archived: bool = False, user=EL, db=Depends(get_db)):
    q = select(Medicine).where(Medicine.elderly_id == user.id)
    if not archived:
        q = q.where(Medicine.active.is_(True))
    return [med_out(m) for m in db.scalars(q.order_by(Medicine.name))]


@router.post("/medicines", status_code=201)
def add_medicine(d: MedicineIn, user=EL, db=Depends(get_db)):
    data = d.model_dump()
    sch = data.pop("schedules")
    m = Medicine(elderly_id=user.id, **data, schedules=[MedicineSchedule(**s) for s in sch])
    _check_dates(m)
    db.add(m)
    db.commit()
    return med_out(m)


@router.get("/medicines/{mid}")
def get_medicine(mid: int, user=EL, db=Depends(get_db)):
    return med_out(own(db, Medicine, mid, user))


@router.patch("/medicines/{mid}")
def edit_medicine(mid: int, d: MedicinePatch, user=EL, db=Depends(get_db)):
    m = own(db, Medicine, mid, user)
    data = d.model_dump(exclude_unset=True)
    sch = data.pop("schedules", None)
    patch(m, data, nonnull=("name", "active"))
    if sch is not None:
        m.schedules = [MedicineSchedule(**s) for s in sch]
    _check_dates(m)
    db.commit()
    return med_out(m)


@router.delete("/medicines/{mid}", status_code=204)
def archive_medicine(mid: int, user=EL, db=Depends(get_db)):
    own(db, Medicine, mid, user).active = False  # archived, not erased
    db.commit()


# ---- appointments
def appt_out(a):
    d = out(a, "id", "title", "provider", "location", "starts_at", "notes")
    d["upcoming"] = (a.starts_at if a.starts_at.tzinfo else a.starts_at.replace(tzinfo=utcnow().tzinfo)) >= utcnow()
    return d


@router.get("/appointments")
def list_appts(view: str = "all", user=EL, db=Depends(get_db)):
    items = [appt_out(a) for a in db.scalars(select(Appointment).where(Appointment.elderly_id == user.id)
                                             .order_by(Appointment.starts_at))]
    up = [a for a in items if a["upcoming"]]
    past = [a for a in reversed(items) if not a["upcoming"]]
    return up if view == "upcoming" else past if view == "past" else up + past


@router.post("/appointments", status_code=201)
def add_appt(d: AppointmentIn, user=EL, db=Depends(get_db)):
    data = d.model_dump()
    data["starts_at"] = aware(d.starts_at, user.timezone)
    a = Appointment(elderly_id=user.id, **data)
    db.add(a)
    db.commit()
    return appt_out(a)


@router.get("/appointments/{aid}")
def get_appt(aid: int, user=EL, db=Depends(get_db)):
    return appt_out(own(db, Appointment, aid, user))


@router.patch("/appointments/{aid}")
def edit_appt(aid: int, d: AppointmentPatch, user=EL, db=Depends(get_db)):
    a = own(db, Appointment, aid, user)
    data = d.model_dump(exclude_unset=True)
    if data.get("starts_at"):
        data["starts_at"] = aware(data["starts_at"], user.timezone)
    patch(a, data, nonnull=("title", "starts_at"))
    db.commit()
    return appt_out(a)


@router.delete("/appointments/{aid}", status_code=204)
def del_appt(aid: int, user=EL, db=Depends(get_db)):
    db.delete(own(db, Appointment, aid, user))
    db.commit()


# ---- emergency contacts
def contact_out(c):
    d = out(c, "id", "name", "phone", "priority")
    d["relationship"] = c.relationship_
    return d


@router.get("/emergency-contacts")
def list_contacts(user=EL, db=Depends(get_db)):
    return [contact_out(c) for c in db.scalars(select(EmergencyContact)
            .where(EmergencyContact.elderly_id == user.id).order_by(EmergencyContact.priority, EmergencyContact.id))]


@router.post("/emergency-contacts", status_code=201)
def add_contact(d: ContactIn, user=EL, db=Depends(get_db)):
    top = db.scalar(select(func.max(EmergencyContact.priority)).where(EmergencyContact.elderly_id == user.id))
    c = EmergencyContact(elderly_id=user.id, name=d.name, relationship_=d.relationship, phone=d.phone,
                         priority=(top if top is not None else -1) + 1)
    db.add(c)
    db.commit()
    return contact_out(c)


@router.post("/emergency-contacts/reorder")
def reorder_contacts(d: ReorderIn, user=EL, db=Depends(get_db)):
    mine = {c.id: c for c in db.scalars(select(EmergencyContact).where(EmergencyContact.elderly_id == user.id))}
    if set(d.ids) != set(mine) or len(d.ids) != len(mine):
        raise HTTPException(422, "ids must list all of your contacts exactly once")
    for i, cid in enumerate(d.ids):
        mine[cid].priority = i
    db.commit()
    return list_contacts(user, db)


@router.patch("/emergency-contacts/{cid}")
def edit_contact(cid: int, d: ContactPatch, user=EL, db=Depends(get_db)):
    c = own(db, EmergencyContact, cid, user)
    data = d.model_dump(exclude_unset=True)
    if "relationship" in data:
        data["relationship_"] = data.pop("relationship")
    patch(c, data, nonnull=("name", "phone"))
    db.commit()
    return contact_out(c)


@router.delete("/emergency-contacts/{cid}", status_code=204)
def del_contact(cid: int, user=EL, db=Depends(get_db)):
    db.delete(own(db, EmergencyContact, cid, user))
    db.commit()


# ---- daily check-in (a missing check-in means UNKNOWN, never "danger")
@router.post("/check-ins", status_code=201)
def check_in(d: CheckInIn, user=EL, db=Depends(get_db)):
    today = local_today(user)
    c = db.scalar(select(DailyCheckIn).where(DailyCheckIn.elderly_id == user.id, DailyCheckIn.day == today))
    if c:
        c.status, c.note, c.created_at = d.status, d.note, utcnow()
    else:
        c = DailyCheckIn(elderly_id=user.id, day=today, status=d.status, note=d.note)
        db.add(c)
    if d.status == "NOT_WELL":
        for fid in approved_family_ids(db, user.id):
            notify(db, fid, "CHECK_IN", f"{user.name} reported not feeling well today.")
    db.commit()
    return out(c, "day", "status", "note", "created_at")


@router.get("/check-ins/today")
def today_check_in(user=EL, db=Depends(get_db)):
    c = db.scalar(select(DailyCheckIn).where(DailyCheckIn.elderly_id == user.id,
                                             DailyCheckIn.day == local_today(user)))
    return out(c, "day", "status", "note", "created_at") if c else {"status": "UNKNOWN"}


@router.get("/check-ins/history")
def history(user=EL, db=Depends(get_db)):
    return [out(c, "day", "status", "note", "created_at") for c in db.scalars(
        select(DailyCheckIn).where(DailyCheckIn.elderly_id == user.id).order_by(DailyCheckIn.day.desc()).limit(30))]
