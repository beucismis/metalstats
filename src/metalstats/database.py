import random
from datetime import datetime
from sqlmodel import SQLModel, Session, Field, create_engine

from . import models


sqlite_url = f"sqlite:///{models.Settings.DB_FILE}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def generate_random_creator_name():
    random_number = random.randint(100000, 999999)
    return f"Anon#{random_number}"


class ShowcaseItem(SQLModel, table=True):
    __tablename__ = "showcase_item"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    creator_name: str = Field(default_factory=generate_random_creator_name, index=True)
    creator_spotify_id: str | None = Field(default=None, index=True)
    image_filename: str = Field()
    top_type: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
