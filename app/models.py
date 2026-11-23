import enum
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.db import Base


def now():
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    ELDERLY = "ELDERLY"
    FAMILY = "FAMILY"
    VOLUNTEER = "VOLUNTEER"
    ADMIN = "ADMIN"


def _fk(t):
    return mapped_column(ForeignKey(t, ondelete="CASCADE"), index=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ElderlyProfile(Base):
    __tablename__ = "elderly_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(300))
    accessibility_notes: Mapped[str | None] = mapped_column(Text)


class FamilyConnection(Base):
    __tablename__ = "family_connections"
    __table_args__ = (UniqueConstraint("family_id", "elderly_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = _fk("users.id")
    elderly_id: Mapped[int] = _fk("users.id")
    status: Mapped[str] = mapped_column(String(10), default="PENDING")  # PENDING/APPROVED/REJECTED/REVOKED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    availability: Mapped[str | None] = mapped_column(String(300))
    service_area: Mapped[str | None] = mapped_column(String(200))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class MedicineSchedule(Base):
    __tablename__ = "medicine_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[int] = _fk("medicines.id")
    time: Mapped[str] = mapped_column(String(5))
    recurrence: Mapped[str] = mapped_column(String(12), default="DAILY")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")


class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[int] = mapped_column(primary_key=True)
    elderly_id: Mapped[int] = _fk("users.id")
    name: Mapped[str] = mapped_column(String(150))
    instructions: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    schedules: Mapped[list[MedicineSchedule]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    elderly_id: Mapped[int] = _fk("users.id")
    title: Mapped[str] = mapped_column(String(150))
    provider: Mapped[str | None] = mapped_column(String(150))
    location: Mapped[str | None] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    elderly_id: Mapped[int] = _fk("users.id")
    name: Mapped[str] = mapped_column(String(100))
    relationship_: Mapped[str | None] = mapped_column("relationship", String(60))
    phone: Mapped[str] = mapped_column(String(30))
    priority: Mapped[int] = mapped_column(Integer, default=0)


class DailyCheckIn(Base):
    __tablename__ = "daily_check_ins"
    __table_args__ = (UniqueConstraint("elderly_id", "day"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    elderly_id: Mapped[int] = _fk("users.id")
    day: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VolunteerRequest(Base):
    __tablename__ = "volunteer_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    elderly_id: Mapped[int] = _fk("users.id")
    volunteer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    requested_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _fk("users.id")
    type: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(200))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(60))
    target: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
