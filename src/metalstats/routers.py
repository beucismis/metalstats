import json
from io import BytesIO
from typing import Any

import spotipy
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from .models import Album, Artist, GridTemplate, TopItemsRequest, Track
from .utils import create_grid_image, get_spotify_oauth, top_items_query


api = APIRouter()


@api.get("/login", response_class=JSONResponse)
async def login() -> JSONResponse:
    spotify_oauth = get_spotify_oauth()
    auth_url = spotify_oauth.get_authorize_url()
    return JSONResponse(content={"auth_url": auth_url})


@api.get("/logout", response_class=RedirectResponse)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/")


@api.get("/callback", response_class=JSONResponse)
async def callback(request: Request) -> JSONResponse:
    spotify_oauth = get_spotify_oauth()
    code = request.query_params.get("code")

    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    token_info = spotify_oauth.get_access_token(code, as_dict=True)
    request.session["token_info"] = token_info

    return JSONResponse(
        content={
            "access_token": token_info["access_token"],
            "expires_in": token_info["expires_in"],
            "refresh_token": token_info.get("refresh_token"),
            "scope": token_info["scope"],
            "token_type": token_info["token_type"],
        }
    )


@api.get("/top", response_class=JSONResponse)
async def top(request: Request, params: TopItemsRequest = Depends(top_items_query)) -> Any:
    token_info = request.session.get("token_info")

    if not token_info:
        return RedirectResponse("/")

    data = {}
    spotify = spotipy.Spotify(auth=token_info["access_token"])

    if params.type in ("tracks"):
        top_tracks = spotify.current_user_top_tracks(limit=params.limit, time_range=params.time_range)
        data["tracks"] = [
            Track(
                artist_name=t["artists"][0]["name"],
                song_name=t["name"],
                album_cover_url=t["album"]["images"][0]["url"],
            ).model_dump()
            for t in top_tracks["items"]
        ]

    if params.type in ("artists"):
        top_artists = spotify.current_user_top_artists(limit=params.limit, time_range=params.time_range)
        data["artists"] = [
            Artist(
                name=a["name"],
                image_url=a["images"][0]["url"],
            ).model_dump()
            for a in top_artists["items"]
        ]

    if params.type in ("albums"):
        top_tracks = spotify.current_user_top_tracks(limit=params.limit, time_range=params.time_range)
        data["albums"] = [
            Album(
                artist_name=t["artists"][0]["name"],
                name=t["album"]["name"],
                cover_url=t["album"]["images"][0]["url"],
            ).model_dump()
            for t in top_tracks["items"]
        ]

    return JSONResponse(content=data)


@api.get("/top-grid", response_class=StreamingResponse)
async def top_grid(request: Request, params: TopItemsRequest = Depends(top_items_query)):
    token_info = request.session.get("token_info")

    if not token_info:
        return RedirectResponse("/")

    grid_template = []
    top_data = await top(request, params)
    top_data = json.loads(top_data.body.decode())

    if params.type in ("tracks"):
        for track in top_data["tracks"]:
            title = track["artist_name"] + " - " + track["song_name"]
            grid_template.append(GridTemplate(title=title, image_url=track["album_cover_url"]))

    if params.type in ("artists"):
        for artist in top_data["artists"]:
            title = artist["name"]
            grid_template.append(GridTemplate(title=title, image_url=artist["image_url"]))

    if params.type in ("albums"):
        for album in top_data["albums"]:
            title = album["artist_name"] + " - " + album["name"]
            grid_template.append(GridTemplate(title=title, image_url=album["cover_url"]))

    image = create_grid_image(grid_template)

    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/jpeg")
