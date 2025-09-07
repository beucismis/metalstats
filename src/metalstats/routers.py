import json
from io import BytesIO
from typing import Any, Union

import spotipy
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from src.metalstats import models, utils


api = APIRouter()
settings = models.Settings()


@api.get("/login",  response_class=RedirectResponse)
async def login() -> RedirectResponse:
    spotify_oauth = utils.get_spotify_oauth()
    auth_url = spotify_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@api.get("/logout", response_class=JSONResponse)
async def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"message": "Logged out successfully"})


@api.get("/callback", response_model=None)
async def callback(request: Request) -> Union[RedirectResponse, JSONResponse]:
    code = request.query_params.get("code")

    if code is None:
        return JSONResponse({"error": "No code provided"}, status_code=400)

    spotify_oauth = utils.get_spotify_oauth()
    token_info = spotify_oauth.get_access_token(code, as_dict=True)
    request.session["token_info"] = token_info

    if settings.METALSTATS_FRONTEND_URL:
        return RedirectResponse(settings.METALSTATS_FRONTEND_URL)
    else:
        return JSONResponse({"message": "Spotify login successful. Token saved in session."})


@api.get("/top", response_class=JSONResponse)
async def top(request: Request, params: models.TopItemsRequest = Depends(utils.top_items_query)) -> JSONResponse:
    token_info = request.session.get("token_info")

    if not token_info:
        return JSONResponse({"error": "Not authenticated. Please login first."}, status_code=401)

    data = {}
    top_handlers = {
        "tracks": utils.get_top_tracks,
        "artists": utils.get_top_artists,
        "albums": utils.get_top_albums,
    }

    spotify = utils.get_spotify_client(request)

    for type in top_handlers.keys():
        if params.type in (type, "all"):
            handler = top_handlers[type]
            data[type] = list(handler(spotify, params))

    return JSONResponse(content=data)


@api.get("/top-grid", response_model=None)
async def top_grid(
    request: Request, params: models.TopItemsRequest = Depends(utils.top_items_query)
) -> Union[JSONResponse, StreamingResponse]:
    token_info = request.session.get("token_info")

    if not token_info:
        return JSONResponse({"error": "Not authenticated. Please login first."}, status_code=401)

    spotify = utils.get_spotify_client(request)
    grid_template = utils.build_grid_template(spotify, params)
    image = utils.create_grid_image(grid_template)

    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/jpeg")
