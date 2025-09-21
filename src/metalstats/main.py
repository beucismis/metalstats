import secrets
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.metalstats import __about__, models, routers


app = FastAPI()
app.mount("/static", StaticFiles(directory="src/metalstats/static"), name="static")
app.include_router(routers.api)

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=["*"],
    allow_credentials=True,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32),
)

templates = Jinja2Templates(directory="src/metalstats/templates")


@app.get("/", response_class=HTMLResponse)
async def home_sweet_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/healthcheck", response_class=JSONResponse)
async def healthcheck() -> models.HealthCheck:
    return models.HealthCheck(
        status="healthy",
        version=__about__.__version__,
        timestamp=datetime.now(UTC),
    )
