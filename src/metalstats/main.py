import secrets
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import database
from src.metalstats import __about__, models, routers


app = FastAPI()
settings = models.Settings()
app.mount("/static", StaticFiles(directory="src/metalstats/static"), name="static")
app.mount("/images", StaticFiles(directory=settings.IMAGES_DIR), name="images")
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


@app.on_event("startup")
def on_startup():
    database.create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
async def home_sweet_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/po-tos", response_class=HTMLResponse)
async def po_tos(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("po-tos.html", {"request": request})


@app.get("/healthcheck", response_class=JSONResponse)
async def healthcheck() -> models.HealthCheck:
    return models.HealthCheck(
        status="healthy",
        version=__about__.__version__,
        timestamp=datetime.now(UTC),
    )
