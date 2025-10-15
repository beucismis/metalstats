import os
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SPOTIFY_SCOPE: str = "user-top-read"
    SPOTIFY_CLIENT_ID: str = os.environ["SPOTIFY_CLIENT_ID"]
    SPOTIFY_CLIENT_SECRET: str = os.environ["SPOTIFY_CLIENT_SECRET"]
    SPOTIFY_REDIRECT_URI: str = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8000/callback")
    DATA_DIR: ClassVar[str] = os.environ.get("METALSTATS_DATA_DIR", "data/")
    DB_FILE: ClassVar[str] = os.path.join(DATA_DIR, "app.db")
    IMAGES_DIR: ClassVar[str] = os.path.join(DATA_DIR, "images/")


class CanvasSettings(BaseSettings):
    PADDING: int = 10
    COVERS_PER_ROW: int = 5
    COVER_SIZE: tuple = (200, 200)
    BG_COLOR: tuple = (0, 0, 0)
    FG_COLOR: tuple = (255, 255, 255)
    FONT_SIZE: int = 12
    FONT_FILENAME: str = "LiberationMono-Regular.ttf"


class CanvasItem(BaseSettings):
    title: str = Field()
    image_url: Optional[str] = Field()


class Track(BaseModel):
    artist_name: str = Field()
    song_name: str = Field()
    album_name: str = Field()
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
    def valid_type(cls, v) -> str:
        if v not in ["tracks", "artists", "albums"]:
            raise ValueError("type must be one of: tracks, artists, albums")
        return v

    @field_validator("time_range")
    def valid_time_range(cls, v) -> str:
        if v not in ["short_term", "medium_term", "long_term"]:
            raise ValueError("time_range must be one of: short_term, medium_term, long_term")
        return v


class HealthCheck(BaseModel):
    status: str = Field()
    version: str = Field()
    timestamp: datetime = Field()


class ShareRequest(BaseModel):
    type: str
    time_range: str
    limit: int
    share_anonymously: bool
