import math
from io import BytesIO
from pathlib import Path
from typing import Iterator, List

import requests
import spotipy
from fastapi import Query, Request
from PIL import Image, ImageDraw, ImageFont
from spotipy.oauth2 import SpotifyOAuth

from src.metalstats import models


settings = models.Settings()
grid_settings = models.GridSettings()


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
        raise Exception("Not logged in!")

    if get_spotify_oauth().is_token_expired(token_info):
        token_info = get_spotify_oauth().refresh_access_token(token_info["refresh_token"])
        request.session["token_info"] = token_info

    spotify = spotipy.Spotify(auth=token_info["access_token"])
    return spotify


def get_top_tracks(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    top_tracks = spotify.current_user_top_tracks(time_range=params.time_range, limit=params.limit)

    for t in top_tracks["items"]:
        yield models.Track(
            artist_name=t["artists"][0]["name"],
            song_name=t["name"],
            album_cover_url=t["album"]["images"][0]["url"],
        ).model_dump()


def get_top_artists(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    top_artists = spotify.current_user_top_artists(time_range=params.time_range, limit=params.limit)

    for a in top_artists["items"]:
        yield models.Artist(
            name=a["name"],
            image_url=a["images"][0]["url"],
        ).model_dump()


def get_top_albums(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> Iterator[dict]:
    top_tracks = spotify.current_user_top_tracks(time_range=params.time_range, limit=params.limit)

    for t in top_tracks["items"]:
        yield models.Album(
            artist_name=t["artists"][0]["name"],
            name=t["album"]["name"],
            cover_url=t["album"]["images"][0]["url"],
        ).model_dump()


def top_items_query(
    type: str = Query("tracks", regex="^(tracks|artists|albums)$"),
    time_range: str = Query("medium_term", regex="^(short_term|medium_term|long_term)$"),
    limit: int = Query(10, ge=1, le=50),
) -> models.TopItemsRequest:
    return models.TopItemsRequest(type=type, time_range=time_range, limit=limit)


def build_grid_template(spotify: spotipy.Spotify, params: models.TopItemsRequest) -> List[models.GridTemplate]:
    grid_template: List[models.GridTemplate] = []

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

            grid_template.append(models.GridTemplate(title=title, image_url=image_url))

    return grid_template


def create_grid_image(grid_template: list[models.GridTemplate]) -> Image.Image:
    max_label_width = 0
    rows = math.ceil(len(grid_template) / grid_settings.COVERS_PER_ROW)
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    font = ImageFont.truetype(
        Path(__file__).parent / "static" / grid_settings.FONT_FILENAME,
        grid_settings.FONT_SIZE,
    )

    for idx, template in enumerate(grid_template):
        text = f"{idx+1:2}. {template.title}"
        text_width = draw_dummy.textlength(text, font=font)

        if text_width > max_label_width:
            max_label_width = text_width

    grid_width = (
        grid_settings.COVERS_PER_ROW * grid_settings.COVER_SIZE[0]
        + (grid_settings.COVERS_PER_ROW + 1) * grid_settings.PADDING
        + int(max_label_width)
        + grid_settings.PADDING * 2
    )
    grid_height = rows * grid_settings.COVER_SIZE[1] + (rows + 1) * grid_settings.PADDING

    image = Image.new("RGB", (grid_width, grid_height), color=grid_settings.BG_COLOR)
    draw = ImageDraw.Draw(image)

    for idx, template in enumerate(grid_template):
        if template.image_url is None:
            img = Image.open(Path(__file__).parent / "static" / "none.png")
        else:
            response = requests.get(template.image_url)
            img = Image.open(BytesIO(response.content)).convert("RGB").resize(grid_settings.COVER_SIZE)

        row = idx // grid_settings.COVERS_PER_ROW
        col = idx % grid_settings.COVERS_PER_ROW

        image.paste(
            img,
            (
                grid_settings.PADDING + col * (grid_settings.COVER_SIZE[0] + grid_settings.PADDING),
                grid_settings.PADDING + row * (grid_settings.COVER_SIZE[1] + grid_settings.PADDING),
            ),
        )

        label_x = (
            grid_settings.COVERS_PER_ROW * (grid_settings.COVER_SIZE[0] + grid_settings.PADDING)
            + grid_settings.PADDING * 2
        )
        label_y = (
            grid_settings.PADDING
            + row * (grid_settings.COVER_SIZE[1] + grid_settings.PADDING)
            + col * (grid_settings.FONT_SIZE + 5)
        )
        draw.text(
            (label_x, label_y),
            f"{idx+1:2}. {template.title}",
            fill=grid_settings.FG_COLOR,
            font=font,
        )

    return image
