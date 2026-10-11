from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.deps import optional_user

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
E = "ELDERLY"
TITLES = {"dashboard": "Home", "profile": "My Profile", "notifications": "Notifications",
          "medicines": "Medicines", "appointments": "Appointments", "contacts": "Emergency Contacts",
          "help": "Help Requests"}
ROLES = {"medicines": {E}, "appointments": {E}, "contacts": {E}, "help": {E},
         "dashboard": {E}, "profile": {E}, "notifications": {E}}
NAV = {E: ["dashboard", "medicines", "appointments", "contacts", "help", "notifications", "profile"]}


def make(page):
    def handler(request: Request, user=Depends(optional_user)):
        if not user:
            return RedirectResponse("/login", 303)
        if user.role not in ROLES.get(page, {E}):
            return RedirectResponse("/app/dashboard", 303)
        if user.role != E:
            return RedirectResponse("/login", 303)
        nav = [(p, TITLES[p]) for p in NAV[E]]
        return templates.TemplateResponse(request, "app.html", {"user": user, "page": page, "title": TITLES[page], "nav": nav})
    return handler


for _p in TITLES:
    router.get(f"/app/{_p}")(make(_p))


@router.get("/")
def home(user=Depends(optional_user)):
    return RedirectResponse("/app/dashboard" if user else "/login", 303)


def _auth(mode):
    def handler(request: Request, user=Depends(optional_user)):
        if user:
            return RedirectResponse("/app/dashboard", 303)
        return templates.TemplateResponse(request, "auth.html", {"user": None, "mode": mode, "title": mode.title()})
    return handler


router.get("/login")(_auth("login"))
