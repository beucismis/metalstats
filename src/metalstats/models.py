from os import environ as env
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing_extensions import Optional


class Settings(BaseSettings):
    SPOTIFY_CLIENT_ID: str = env["SPOTIFY_CLIENT_ID"]
    SPOTIFY_CLIENT_SECRET: str = env["SPOTIFY_CLIENT_SECRET"]
    SPOTIFY_SCOPE: str = "user-top-read"
    SPOTIFY_REDIRECT_URI: str = env.get("SPOTIFY_REDIRECT_URI", "http://localhost:8000/callback")


class GridSettings(BaseSettings):
    PADDING: int = 10
    COVERS_PER_ROW: int = 5
    COVER_SIZE: tuple = (200, 200)
    BG_COLOR: tuple = (0, 0, 0)
    FG_COLOR: tuple = (255, 255, 255)
    FONT_SIZE: int = 12
    FONT_FILENAME: str = "LiberationMono-Regular.ttf"


class GridTemplate(BaseSettings):
    title: str = Field()
    image_url: Optional[str] = Field()


class Track(BaseModel):
    artist_name: str = Field()
    song_name: str = Field()
    album_cover_url: Optional[str] = Field()


class Artist(BaseModel):
    name: str = Field()
    image_url: Optional[str] = Field()


class Album(BaseModel):
    artist_name: str = Field()
    name: str = Field()
    cover_url: Optional[str] = Field()


class TopItemsRequest(BaseModel):
    type: str = Field("tracks")
    time_range: str = Field("medium_term")
    limit: int = Field(10, ge=1, le=50)

    @field_validator("type")
    def valid_type(cls, v):
        if v not in ["tracks", "artists", "albums"]:
            raise ValueError("type must be one of: tracks, artists, albums")
        return v

    @field_validator("time_range")
    def valid_time_range(cls, v):
        if v not in ["short_term", "medium_term", "long_term"]:
            raise ValueError("time_range must be one of: short_term, medium_term, long_term")
        return v


class HealthCheck(BaseModel):
    status: str = Field()
    version: str = Field()
    timestamp: datetime = Field()
