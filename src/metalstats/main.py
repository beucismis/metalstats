import secrets
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from src.metalstats import __about__, models, routers


app = FastAPI()
app.include_router(routers.api)

settings = models.Settings()

origins = ["https://beucismis.github.io"]
origins.append(settings.METALSTATS_FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origins=origins,
    allow_credentials=True,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_hex(32),
)


@app.get("/", response_class=HTMLResponse)
async def home_sweet_home(request: Request) -> HTMLResponse:
    return HTMLResponse(
        f"<b>metalstats</b> - {__about__.__description__} </br>"
        f'Docs: <a href="{request.base_url}docs">{request.base_url}docs</a> </br>'
        f'Source: <a href="{__about__.__source__}">{__about__.__source__}</a>'
    )


@app.get("/healthcheck", response_class=JSONResponse)
async def healthcheck() -> models.HealthCheck:
    return models.HealthCheck(
        status="healthy",
        version=__about__.__version__,
        timestamp=datetime.now(UTC),
    )
