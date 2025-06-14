from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any
from datetime import datetime

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

    def serialize(self) -> dict:
        data: dict = asdict(self)
        if data["_id"] is None:
            del data["_id"]
        return data

    @classmethod
    def deserialize(cls, data: dict) -> "State":
        return cls(**data)

class Sender(Enum):
    GAMEMASTER = auto()
    ERROR = auto()
    SYSTEM = auto()
    USER = auto()

    def __str__(self) -> str:
        return self.name.lower()
