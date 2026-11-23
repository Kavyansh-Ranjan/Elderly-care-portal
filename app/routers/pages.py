from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.deps import optional_user

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
E, F, V, A = "ELDERLY", "FAMILY", "VOLUNTEER", "ADMIN"
TITLES = {"dashboard": "Home", "profile": "My profile", "notifications": "Notifications", "family": "Family",
          "medicines": "Medicines", "appointments": "Appointments", "contacts": "Emergency contacts",
          "help": "Help requests"}
ROLES = {"family": {E, F}, "medicines": {E}, "appointments": {E}, "contacts": {E}, "help": {E}}
NAV = {
    E: ["dashboard", "medicines", "appointments", "contacts", "help", "family", "notifications", "profile"],
    F: ["dashboard", "family", "notifications", "profile"],
    V: ["dashboard", "notifications", "profile"],
    A: ["dashboard", "notifications", "profile"],
}


def make(page):
    def handler(request: Request, user=Depends(optional_user)):
        if not user:
            return RedirectResponse("/login", 303)
        if user.role not in ROLES.get(page, {E, F, V, A}):
            return RedirectResponse("/app/dashboard", 303)
        nav = [(p, "Connections" if p == "family" and user.role == F else TITLES[p]) for p in NAV[user.role]]
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
router.get("/register")(_auth("register"))
