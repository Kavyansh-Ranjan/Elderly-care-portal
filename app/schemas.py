from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

TIME = r"^([01]\d|2[0-3]):[0-5]\d$"
PHONE = r"^[+0-9()\-\s]{5,20}$"


def _tz(v):
    try:
        ZoneInfo(v)
    except Exception:
        raise ValueError("Unknown timezone")
    return v


class B(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterIn(B):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=30)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["ELDERLY", "FAMILY", "VOLUNTEER"]
    timezone: str = "UTC"
    _t = field_validator("timezone")(_tz)


class LoginIn(B):
    email: EmailStr
    password: str = Field(max_length=72)


class UserPatch(B):
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=30)
    timezone: str | None = None

    @field_validator("timezone")
    def _t(cls, v):
        return v if v is None else _tz(v)


class ProfileIn(B):
    date_of_birth: date | None = None
    address: str | None = Field(None, max_length=300)
    accessibility_notes: str | None = Field(None, max_length=1000)


class ScheduleIn(B):
    time: str = Field(pattern=TIME)
    recurrence: Literal["DAILY", "WEEKLY", "AS_NEEDED"] = "DAILY"
    timezone: str = "UTC"
    _t = field_validator("timezone")(_tz)


class MedicineIn(B):
    name: str = Field(min_length=1, max_length=150)
    instructions: str | None = Field(None, max_length=1000)
    start_date: date | None = None
    end_date: date | None = None
    schedules: list[ScheduleIn] = Field(default_factory=list, max_length=12)


class MedicinePatch(B):
    name: str | None = Field(None, min_length=1, max_length=150)
    instructions: str | None = Field(None, max_length=1000)
    start_date: date | None = None
    end_date: date | None = None
    active: bool | None = None
    schedules: list[ScheduleIn] | None = Field(None, max_length=12)


class AppointmentIn(B):
    title: str = Field(min_length=1, max_length=150)
    provider: str | None = Field(None, max_length=150)
    location: str | None = Field(None, max_length=200)
    starts_at: datetime
    notes: str | None = Field(None, max_length=1000)


class AppointmentPatch(B):
    title: str | None = Field(None, min_length=1, max_length=150)
    provider: str | None = Field(None, max_length=150)
    location: str | None = Field(None, max_length=200)
    starts_at: datetime | None = None
    notes: str | None = Field(None, max_length=1000)


class ContactIn(B):
    name: str = Field(min_length=1, max_length=100)
    relationship: str | None = Field(None, max_length=60)
    phone: str = Field(pattern=PHONE)


class ContactPatch(B):
    name: str | None = Field(None, min_length=1, max_length=100)
    relationship: str | None = Field(None, max_length=60)
    phone: str | None = Field(None, pattern=PHONE)


class ReorderIn(B):
    ids: list[int]


class CheckInIn(B):
    status: Literal["WELL", "NOT_WELL"]
    note: str | None = Field(None, max_length=300)


class FamilyReqIn(B):
    elderly_email: EmailStr


class HelpIn(B):
    category: Literal["GROCERIES", "TRANSPORT", "COMPANIONSHIP", "HOME_HELP", "TECH_HELP", "OTHER"]
    description: str = Field(min_length=1, max_length=1000)
    requested_time: datetime
    location: str | None = Field(None, max_length=200)


class VolProfileIn(B):
    availability: str | None = Field(None, max_length=300)
    service_area: str | None = Field(None, max_length=200)


class FlagIn(B):
    value: bool
