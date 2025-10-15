import uuid
from io import BytesIO
from pathlib import Path
from typing import List, Union

import spotipy
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse, HTMLResponse
from sqlmodel import Session

from src.metalstats import database, models, utils


api = APIRouter()
settings = models.Settings()
templates = Jinja2Templates(directory="src/metalstats/templates")


@api.get("/login", response_class=RedirectResponse)
async def login() -> RedirectResponse:
    spotify_oauth = utils.get_spotify_oauth()
    auth_url = spotify_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@api.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/")


@api.get("/auth-status", response_class=JSONResponse)
async def auth_status(request: Request) -> dict:
    token_info = request.session.get("token_info")

    if token_info:
        return {"logged_in": True, "message": "Spotify login successful."}
    return {"logged_in": False, "message": "Not logged in."}


@api.get("/callback", response_model=None)
async def callback(request: Request) -> Union[RedirectResponse, JSONResponse]:
    code = request.query_params.get("code")

    if code is None:
        return JSONResponse({"error": "No code provided."}, status_code=400)

    spotify_oauth = utils.get_spotify_oauth()
    token_info = spotify_oauth.get_access_token(code, as_dict=True)
    request.session["token_info"] = token_info

    return RedirectResponse(url="/")


@api.get("/top", response_class=JSONResponse)
async def top(
    params: models.TopItemsRequest = Depends(utils.top_items_query),
    spotify: spotipy.Spotify = Depends(utils.get_spotify_client),
) -> JSONResponse:
    data = {}
    top_handlers = {
        "tracks": utils.get_top_tracks,
        "artists": utils.get_top_artists,
        "albums": utils.get_top_albums,
    }

    for type in top_handlers.keys():
        if params.type in (type, "all"):
            handler = top_handlers[type]
            data[type] = list(handler(spotify, params))

    return JSONResponse(content=data)


@api.get("/top-canvas", response_model=None)
async def top_canvas(
    params: models.TopItemsRequest = Depends(utils.top_items_query),
    spotify: spotipy.Spotify = Depends(utils.get_spotify_client),
) -> Union[JSONResponse, StreamingResponse]:
    canvas_items = utils.build_canvas_items(spotify, params)
    image = await utils.create_canvas_image(canvas_items)

    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/jpeg")


@api.get("/showcase-items", response_model=List[database.ShowcaseItem])
def get_showcase_items(db: Session = Depends(database.get_session)):
    return db.query(database.ShowcaseItem).order_by(database.ShowcaseItem.created_at.desc()).all()


@api.post("/share-to-showcase", response_model=database.ShowcaseItem)
async def share_to_showcase(
    share_request: models.ShareRequest,
    spotify: spotipy.Spotify = Depends(utils.get_spotify_client),
    db: Session = Depends(database.get_session),
    _rate_limit: None = Depends(utils.rate_limiter),
):
    params = models.TopItemsRequest(
        type=share_request.type,
        time_range=share_request.time_range,
        limit=share_request.limit,
    )
    canvas_items = utils.build_canvas_items(spotify, params)
    image = await utils.create_canvas_image(canvas_items)

    image_dir = Path(settings.IMAGES_DIR)
    image_dir.mkdir(exist_ok=True)
    image_filename = f"{uuid.uuid4()}.jpg"
    image_path = image_dir / image_filename
    image.save(image_path, format="JPEG")

    creator_name = None
    creator_spotify_id = None

    if not share_request.share_anonymously:
        user_profile = spotify.current_user()
        creator_name = user_profile["display_name"]
        creator_spotify_id = user_profile["id"]

    showcase_item = database.ShowcaseItem(
        creator_name=creator_name,
        creator_spotify_id=creator_spotify_id,
        image_filename=image_filename,
        top_type=share_request.type,
    )

    db.add(showcase_item)
    db.commit()
    db.refresh(showcase_item)

    return showcase_item


@api.get("/showcase", response_model=None)
async def showcase(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("showcase.html", {"request": request})
