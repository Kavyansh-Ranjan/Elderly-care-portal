from fastapi import Depends, FastAPI, Request
from sqlalchemy import text
from app.deps import csrf, get_db
from app.routers import auth, care, pages, social

app = FastAPI(title="Elderly Care & Assistance Portal", dependencies=[Depends(csrf)])


@app.middleware("http")
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                      "Referrer-Policy": "same-origin", "Cache-Control": "no-store"})
    return r


@app.get("/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


for m in (auth, care, social, pages):
    app.include_router(m.router)
