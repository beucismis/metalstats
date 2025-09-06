import secrets
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from . import routers
from .models import HealthCheck
from .__about__ import __version__


app = FastAPI()
app.include_router(routers.api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32),
)


@app.get("/", response_class=HTMLResponse)
async def home() -> HTMLResponse:
    return HTMLResponse("Hello, World!")


@app.get("/healthcheck", response_class=JSONResponse)
async def healthcheck() -> HealthCheck:
    return HealthCheck(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(UTC),
    )
