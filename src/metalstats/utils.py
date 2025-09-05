import math
from io import BytesIO
from pathlib import Path

import requests
import spotipy
from fastapi import Query
from PIL import Image, ImageDraw, ImageFont
from spotipy.oauth2 import SpotifyOAuth

from .models import GridSettings, GridTemplate, Settings, TopItemsRequest


settings = Settings()
grid_settings = GridSettings()


def get_spotify_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.SPOTIFY_CLIENT_ID,
        client_secret=settings.SPOTIFY_CLIENT_SECRET,
        scope=settings.SPOTIFY_SCOPE,
        redirect_uri=settings.SPOTIFY_REDIRECT_URI,
    )


def top_items_query(
    type: str = Query("tracks", regex="^(tracks|artists|albums)$"),
    time_range: str = Query("medium_term", regex="^(short_term|medium_term|long_term)$"),
    limit: int = Query(10, ge=1, le=50),
) -> TopItemsRequest:
    return TopItemsRequest(type=type, time_range=time_range, limit=limit)


def create_grid_image(grid_template: list[GridTemplate]):
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
