from __future__ import annotations
from fastapi import FastAPI

from .database import Base, engine
from .routers.ussd import router as ussd_router
from .routers.admin import router as admin_router

app = FastAPI(title="USSD Voting API")


@app.on_event("startup")
def on_startup() -> None:
	# Create tables
	Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def healthz() -> dict:
	return {"status": "ok"}


app.include_router(ussd_router)
app.include_router(admin_router)