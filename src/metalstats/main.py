import secrets
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.metalstats import __about__, models, routers


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
async def home_sweet_home() -> HTMLResponse:
    return HTMLResponse("Hello, World!")


@app.get("/healthcheck", response_class=JSONResponse)
async def healthcheck() -> models.HealthCheck:
    return models.HealthCheck(
        status="healthy",
        version=__about__.__version__,
        timestamp=datetime.now(UTC),
    )
