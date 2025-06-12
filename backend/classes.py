from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

MAX_HIT_POINTS: int = 5
MIN_HIT_POINTS: int = 0

@dataclass
class State:
    playerName: str = ""
    playerDescription: str = ""
    worldTheme: str = "" 
    initializationPrompt: str = ""
    chatHistory: list[Any] = field(default_factory=list)
    hitPoints: int = MAX_HIT_POINTS

    def __post_init__(self) -> None:
        assert MIN_HIT_POINTS <= self.hitPoints <= MAX_HIT_POINTS

# TODO: Complete database for maintaining story states.
class DBState(declarative_base()):
    __tablename__ = "states"

    id = Column(String, primary_key=True)
    player_name = Column(String)
    player_description = Column(String)
    world_theme = Column(String)
    initialization_prompt = Column(String) # TODO: I think this can be removed.
    chat_history = Column(JSON)
    hit_points = Column(Integer)
    game_over = Column(Boolean) # ~== (hit_points == 0)
    summary = Column(String, nullable=True)
    created_at = Column(DateTime) # UX information, sorting
    updated_at = Column(DateTime) # UX information, sorting

class Sender(Enum):
    GAMEMASTER = auto()
    ERROR = auto()
    SYSTEM = auto()
    USER = auto()

    def __str__(self) -> str:
        return self.name.lower()
