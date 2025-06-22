from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any
from datetime import datetime

import requests
import base64

from bson.objectid import ObjectId

MAX_HIT_POINTS: int = 5
MIN_HIT_POINTS: int = 0

@dataclass
class State:
    _id: ObjectId | None = None
    player_name: str = ""
    player_description: str = ""
    world_theme: str = "" 
    initialization_prompt: str = ""
    chat_history: list[Any] = field(default_factory=list)
    hit_points: int = MAX_HIT_POINTS
    game_over: bool = False
    game_over_summary: str = ""
    created_at: datetime = datetime.today()
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        assert MIN_HIT_POINTS <= self.hit_points <= MAX_HIT_POINTS

    def serialize(self) -> dict[str, Any]:
        data: dict[str, Any] = asdict(self)
        if data["_id"] is None:
            del data["_id"]
        return data

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "State":
        return cls(**data)

class Sender(Enum):
    GAMEMASTER = auto()
    ERROR = auto()
    SYSTEM = auto()
    USER = auto()

    def __str__(self) -> str:
        return self.name.lower()

class ImageType(Enum):
    PORTRAIT = auto()
    LANDSCAPE = auto()

class Image:
    def __init__(self, bs: bytes, filename: str) -> None:
        self.filename: str = filename
        self.bytes: bytes = bs
    
    def json_content(self) -> str:
        """Encodes bytes for transfer to front-end in Base64."""
        return "data:image/png;base64," + base64.b64encode(self.bytes).decode("utf-8")


    @staticmethod
    def json_content_from_bytes(bs: bytes):
        return "data:image/png;base64," + base64.b64encode(bs).decode("utf-8")


    @staticmethod
    def bytes_from_url(url: str) -> bytes:
        is_wikipedia: bool = "wikipedia" in url
        if is_wikipedia:
            response: requests.Response = requests.get(url, headers={'User-Agent': '...'})
        else:
            response: requests.Response = requests.get(url)
        
        response.raise_for_status()
        bs: bytes | None = response.content
        assert(bs is not None)
        return bs

class Images:
    def __init__(self, _id: ObjectId, portrait_bytes: bytes, landscape_bytes: bytes) -> None:
        self.portrait: Image = Image(portrait_bytes, self.name_for(_id, ImageType.PORTRAIT))
        self.landscape: Image = Image(landscape_bytes, self.name_for(_id, ImageType.LANDSCAPE))

    @staticmethod
    def name_for(_id: ObjectId, it: ImageType) -> str:
        match it:
            case ImageType.PORTRAIT:
                return f"{_id}_portrait"
            case ImageType.LANDSCAPE:
                return f"{_id}_landscape"

