from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app

FUT = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")


def test_health_csrf_and_auth(make):
    anon = TestClient(app)
    assert anon.get("/health").json() == {"status": "ok"}
    assert anon.post("/auth/login", json={"email": "a@b.co", "password": "x"}).status_code == 403
    assert anon.get("/medicines").status_code == 401
    c = make("ELDERLY")
    assert c.get("/auth/me").json()["role"] == "ELDERLY"
    bad = {"name": "x", "email": "z@example.com", "password": "password1", "role": "ADMIN"}
    assert c.post("/auth/register", json=bad).status_code == 422
    assert c.post("/auth/register", json={**bad, "role": "FAMILY", "email": c.email}).status_code == 409
    c2 = TestClient(app, headers={"X-Requested-With": "fetch"})
    assert c2.post("/auth/login", json={"email": c.email, "password": "wrongpass"}).status_code == 401
    assert c.get("/login", follow_redirects=False).status_code == 303
    assert c.get("/app/dashboard").status_code == 200


def test_isolation_and_roles(make):
    a, b, v = make("ELDERLY", "a"), make("ELDERLY", "b"), make("VOLUNTEER")
    r = a.post("/medicines", json={"name": "Aspirin", "schedules": [{"time": "08:00"}]})
    assert r.status_code == 201
    mid = r.json()["id"]
    assert b.get(f"/medicines/{mid}").status_code == 404
    assert b.patch(f"/medicines/{mid}", json={"name": "x"}).status_code == 404
    assert v.get("/medicines").status_code == 403
    assert a.post("/medicines", json={"name": "B", "schedules": [{"time": "25:00"}]}).status_code == 422
    assert a.delete(f"/medicines/{mid}").status_code == 204 and a.get("/medicines").json() == []


def test_crud_appointments_contacts_checkin(make):
    a = make("ELDERLY")
    assert a.post("/appointments", json={"title": "Doc", "starts_at": FUT}).status_code == 201
    assert len(a.get("/appointments?view=upcoming").json()) == 1
    c1 = a.post("/emergency-contacts", json={"name": "A", "phone": "+91 98765 43210"}).json()
    c2 = a.post("/emergency-contacts", json={"name": "B", "phone": "12345"}).json()
    out = a.post("/emergency-contacts/reorder", json={"ids": [c2["id"], c1["id"]]}).json()
    assert [c["name"] for c in out] == ["B", "A"]
    assert a.get("/check-ins/today").json()["status"] == "UNKNOWN"
    assert a.post("/check-ins", json={"status": "WELL"}).status_code == 201
    assert a.get("/check-ins/today").json()["status"] == "WELL"


def test_family_consent(make):
    e, f = make("ELDERLY", "e"), make("FAMILY", "f")
    assert f.get("/family/elderly").json() == []
    assert f.post("/family-connections", json={"elderly_email": e.email}).status_code == 202
    assert f.get("/family/elderly").json() == []  # pending: no access
    cid = e.get("/family-connections").json()[0]["id"]
    assert f.post(f"/family-connections/{cid}/approve").status_code == 403
    assert e.post(f"/family-connections/{cid}/approve").status_code == 200
    e.post("/check-ins", json={"status": "NOT_WELL"})
    view = f.get("/family/elderly").json()
    assert view[0]["check_in_status"] == "NOT_WELL"
    assert any("not feeling well" in n["message"] for n in f.get("/notifications").json())
    assert e.delete(f"/family-connections/{cid}").status_code == 204
    assert f.get("/family/elderly").json() == []


def test_volunteer_workflow(make):
    e, v1, v2, adm = make("ELDERLY"), make("VOLUNTEER", "v1"), make("VOLUNTEER", "v2"), make("ADMIN")
    assert e.post("/volunteer-requests", json={"category": "GROCERIES", "description": "milk", "requested_time": "2020-01-01T10:00:00"}).status_code == 422
    rid = e.post("/volunteer-requests", json={"category": "GROCERIES", "description": "milk", "requested_time": FUT}).json()["id"]
    assert v1.get("/volunteer-requests").json() == []
    assert v1.post(f"/volunteer-requests/{rid}/accept").status_code == 403
    for v in (v1, v2):
        uid = v.get("/auth/me").json()["id"]
        assert adm.post(f"/admin/volunteers/{uid}/verify", json={"value": True}).status_code == 200
    assert v1.post(f"/volunteer-requests/{rid}/accept").status_code == 200
    assert v2.post(f"/volunteer-requests/{rid}/accept").status_code == 409
    assert v2.post(f"/volunteer-requests/{rid}/start").status_code == 403
    assert v1.post(f"/volunteer-requests/{rid}/complete").status_code == 409  # must start first
    assert v1.post(f"/volunteer-requests/{rid}/start").json()["status"] == "IN_PROGRESS"
    assert v1.post(f"/volunteer-requests/{rid}/complete").json()["status"] == "COMPLETED"
    assert e.post(f"/volunteer-requests/{rid}/cancel").status_code == 409
    assert any(a["action"] == "VOLUNTEER_VERIFIED" for a in adm.get("/admin/audit").json())
    assert e.get("/admin/users").status_code == 403


def test_reminders_idempotent(make):
    e = make("ELDERLY")
    e.post("/appointments", json={"title": "Doc", "starts_at": (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S+00:00")})
    anon = TestClient(app)
    assert anon.get("/internal/reminders").status_code == 401
    h = {"Authorization": "Bearer cron"}
    assert anon.get("/internal/reminders", headers=h).json()["created"] == 1
    assert anon.get("/internal/reminders", headers=h).json()["created"] == 0


def test_pages_render_html_for_every_role(make):
    for role in ("ELDERLY", "FAMILY", "VOLUNTEER", "ADMIN"):
        c = make(role, role.lower() + "p")
        for p in ("dashboard", "profile", "notifications", "family", "medicines", "appointments", "contacts", "help"):
            r = c.get(f"/app/{p}", follow_redirects=False)
            assert r.status_code in (200, 303), (role, p)
            if r.status_code == 200:
                assert "text/html" in r.headers["content-type"]
