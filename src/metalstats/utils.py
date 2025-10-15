import asyncio
import math
from collections import deque
from io import BytesIO
from pathlib import Path
from time import time
from typing import Iterator, List

import httpx
import spotipy
from fastapi import Query, Request, HTTPException, status
from PIL import Image, ImageDraw, ImageFont
from spotipy.oauth2 import SpotifyOAuth

from src.metalstats import models


settings = models.Settings()
canvas_settings = models.CanvasSettings()

request_timestamps = {}
RATE_LIMIT_DURATION = 60
RATE_LIMIT_REQUESTS = 5

spotify_cache = {}
CACHE_TTL = 3600


def get_cached_spotify_data(cache_key, func, **kwargs):
    current_time = time()

    if cache_key in spotify_cache:
        cached_data, timestamp = spotify_cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            return cached_data

    new_data = func(**kwargs)
    spotify_cache[cache_key] = (new_data, current_time)

    return new_data


def get_spotify_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        scope=settings.SPOTIFY_SCOPE,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    )


def get_spotify_client(request: Request) -> spotipy.Spotify:
    token_info = request.session.get("token_info")

    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login first.",
        )

    if get_spotify_oauth().is_token_expired(token_info):
        token_info = get_spotify_oauth().refresh_access_token(token_info["refresh_token"])
        request.session["token_info"] = token_info

    return spotipy.Spotify(auth=token_info["access_token"])


def get_top_tracks(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    cache_key = f"top_tracks_{params.time_range}_{params.limit}_{spotify.current_user()['id']}"
    top_tracks = get_cached_spotify_data(
        cache_key,
        spotify.current_user_top_tracks,
        time_range=params.time_range,
        limit=params.limit,
    )

    for t in top_tracks["items"]:
        yield models.Track(
            artist_name=t["artists"][0]["name"],
            song_name=t["name"],
            album_name=t["album"]["name"],
            album_cover_url=t["album"]["images"][0]["url"],
        ).model_dump()


def get_top_artists(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    cache_key = f"top_artists_{params.time_range}_{params.limit}_{spotify.current_user()['id']}"
    top_artists = get_cached_spotify_data(
        cache_key,
        spotify.current_user_top_artists,
        time_range=params.time_range,
        limit=params.limit,
    )

    for a in top_artists["items"]:
        yield models.Artist(
            name=a["name"],
            image_url=a["images"][0]["url"],
        ).model_dump()


def get_top_albums(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    top_tracks_iterator = get_top_tracks(spotify, params)
    processed_albums = set()

    for t in top_tracks_iterator:
        album_name = t["album_name"]

        if album_name not in processed_albums:
            yield models.Album(
                artist_name=t["artist_name"],
                name=album_name,
                cover_url=t["album_cover_url"],
            ).model_dump()
            processed_albums.add(album_name)


def top_items_query(
    type: str = Query("tracks", regex="^(tracks|artists|albums)$"),
    time_range: str = Query("medium_term", regex="^(short_term|medium_term|long_term)$"),
    limit: int = Query(10, ge=1, le=50),
) -> models.TopItemsRequest:
    return models.TopItemsRequest(type=type, time_range=time_range, limit=limit)


def build_canvas_items(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> List[models.CanvasItem]:
    canvas_items: List[models.CanvasItem] = []

    type_handlers = {
        "tracks": get_top_tracks,
        "artists": get_top_artists,
        "albums": get_top_albums,
    }

    types_to_process = [params.type] if params.type != "all" else ["tracks", "artists", "albums"]

    for type in types_to_process:
        if type not in type_handlers:
            continue

        items = list(type_handlers[type](spotify, params))

        for item in items:
            if type == "tracks":
                title = f"{item['artist_name']} - {item['song_name']}"
                image_url = item["album_cover_url"]
            elif type == "artists":
                title = item["name"]
                image_url = item["image_url"]
            elif type == "albums":
                title = f"{item['artist_name']} - {item['name']}"
                image_url = item["cover_url"]

            canvas_items.append(models.CanvasItem(title=title, image_url=image_url))

    return canvas_items


def _process_image(content: bytes) -> Image.Image:
    """Helper function to run synchronous Pillow code."""
    return Image.open(BytesIO(content)).convert("RGB").resize(canvas_settings.COVER_SIZE)


async def fetch_image(client, url, default_image_path):
    if not url:
        return await asyncio.to_thread(Image.open, default_image_path)
    try:
        response = await client.get(url)
        response.raise_for_status()
        # Run the synchronous (blocking) Pillow operations in a separate thread
        return await asyncio.to_thread(_process_image, response.content)
    except (httpx.HTTPStatusError, httpx.RequestError):
        return await asyncio.to_thread(Image.open, default_image_path)


async def create_canvas_image(canvas_items: list[models.CanvasItem]) -> Image.Image:
    max_label_width = 0
    rows = math.ceil(len(canvas_items) / canvas_settings.COVERS_PER_ROW)
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    font = ImageFont.truetype(
        Path(__file__).parent / "static" / canvas_settings.FONT_FILENAME,
        canvas_settings.FONT_SIZE,
    )

    for idx, template in enumerate(canvas_items):
        text = f"{idx + 1:2}. {template.title}"
        text_width = draw_dummy.textlength(text, font=font)

        if text_width > max_label_width:
            max_label_width = text_width

    canvas_width = (
        canvas_settings.COVERS_PER_ROW * canvas_settings.COVER_SIZE[0]
        + (canvas_settings.COVERS_PER_ROW + 1) * canvas_settings.PADDING
        + int(max_label_width)
        + canvas_settings.PADDING * 2
    )
    canvas_height = rows * canvas_settings.COVER_SIZE[1] + (rows + 1) * canvas_settings.PADDING

    image = Image.new("RGB", (canvas_width, canvas_height), color=canvas_settings.BG_COLOR)
    draw = ImageDraw.Draw(image)

    default_image = Path(__file__).parent / "static" / "none.png"
    async with httpx.AsyncClient() as client:
        tasks = [fetch_image(client, item.image_url, default_image) for item in canvas_items]
        images = await asyncio.gather(*tasks)

    for idx, (template, img) in enumerate(zip(canvas_items, images)):
        row = idx // canvas_settings.COVERS_PER_ROW
        col = idx % canvas_settings.COVERS_PER_ROW

        image.paste(
            img,
            (
                canvas_settings.PADDING + col * (canvas_settings.COVER_SIZE[0] + canvas_settings.PADDING),
                canvas_settings.PADDING + row * (canvas_settings.COVER_SIZE[1] + canvas_settings.PADDING),
            ),
        )

        label_x = (
            canvas_settings.COVERS_PER_ROW * (canvas_settings.COVER_SIZE[0] + canvas_settings.PADDING)
            + canvas_settings.PADDING * 2
        )
        label_y = (
            canvas_settings.PADDING
            + row * (canvas_settings.COVER_SIZE[1] + canvas_settings.PADDING)
            + col * (canvas_settings.FONT_SIZE + 5)
        )
        draw.text(
            (label_x, label_y),
            f"{idx + 1:2}. {template.title}",
            fill=canvas_settings.FG_COLOR,
            font=font,
        )

    return image


def rate_limiter(request: Request):
    client_ip = request.client.host
    timestamps = request_timestamps.setdefault(client_ip, deque())
    current_time = time()

    while timestamps and timestamps[0] < current_time - RATE_LIMIT_DURATION:
        timestamps.popleft()

    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a minute.",
        )

    timestamps.append(current_time)
