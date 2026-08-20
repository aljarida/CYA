from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4

MAX_HIT_POINTS: int = 5
MIN_HIT_POINTS: int = 0
DEFAULT_MAX_CARRY_WEIGHT_KG: float = 40.0
LEGACY_INVENTORY_ITEM_WEIGHT_KG: float = 0.5


@dataclass
class InventoryItem:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    weight_kg: float = 0.0
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.weight_kg < 0:
            raise ValueError("weight_kg must be non-negative.")
        if self.quantity < 1:
            raise ValueError("quantity must be at least 1.")

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "weightKg": self.weight_kg,
            "quantity": self.quantity,
        }

    @classmethod
    def deserialize(cls, data: Any) -> "InventoryItem":
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            return cls(name=data, weight_kg=LEGACY_INVENTORY_ITEM_WEIGHT_KG, quantity=1)
        if not isinstance(data, dict):
            return cls()

        return cls(
            id=str(data.get("id") or uuid4()),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            weight_kg=float(data.get("weight_kg") or 0.0),
            quantity=int(data.get("quantity") or 1),
        )


@dataclass
class PlayerAttributes:
    age_years: int | None = None
    height_cm: float | None = None
    body_weight_kg: float | None = None
    max_carry_weight_kg: float = DEFAULT_MAX_CARRY_WEIGHT_KG

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "ageYears": self.age_years,
            "heightCm": self.height_cm,
            "bodyWeightKg": self.body_weight_kg,
            "maxCarryWeightKg": self.max_carry_weight_kg,
        }

    @classmethod
    def deserialize(cls, data: Any) -> "PlayerAttributes":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            return cls()

        max_carry_weight_kg = data.get("max_carry_weight_kg")
        return cls(
            age_years=data.get("age_years"),
            height_cm=data.get("height_cm"),
            body_weight_kg=data.get("body_weight_kg"),
            max_carry_weight_kg=float(max_carry_weight_kg) if max_carry_weight_kg else DEFAULT_MAX_CARRY_WEIGHT_KG,
        )


QUEST_STATUSES = ("active", "resolved")


@dataclass
class Quest:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    status: str = "active"
    current_step: str = ""
    step_history: list[str] = field(default_factory=list)
    outcome: str = ""

    def __post_init__(self) -> None:
        if self.status not in QUEST_STATUSES:
            raise ValueError(f"status must be one of {QUEST_STATUSES}.")

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "currentStep": self.current_step,
            "stepHistory": list(self.step_history),
            "outcome": self.outcome,
        }

    @classmethod
    def deserialize(cls, data: Any) -> "Quest":
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            return cls(title=data, status="active")
        if not isinstance(data, dict):
            return cls()

        status = str(data.get("status") or "active")
        return cls(
            id=str(data.get("id") or uuid4()),
            title=str(data.get("title") or ""),
            description=str(data.get("description") or ""),
            status=status if status in QUEST_STATUSES else "active",
            current_step=str(data.get("current_step") or ""),
            step_history=list(data.get("step_history") or []),
            outcome=str(data.get("outcome") or ""),
        )


@dataclass
class WorldState:
    version: int = 1
    current_location: str = ""
    inventory: list[InventoryItem] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    known_npcs: dict[str, str] = field(default_factory=dict)
    relationships: dict[str, str] = field(default_factory=dict)
    quests: list[Quest] = field(default_factory=list)
    world_flags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("world state version must be positive.")

    def total_inventory_weight_kg(self) -> float:
        return sum(item.weight_kg * item.quantity for item in self.inventory)

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "currentLocation": self.current_location,
            "inventory": [item.to_api_dict() for item in self.inventory],
            "totalInventoryWeightKg": self.total_inventory_weight_kg(),
            "conditions": list(self.conditions),
            "knownNpcs": dict(self.known_npcs),
            "relationships": dict(self.relationships),
            "quests": [quest.to_api_dict() for quest in self.quests],
            "worldFlags": dict(self.world_flags),
        }

    @classmethod
    def deserialize(cls, data: Any) -> "WorldState":
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            return cls()

        quests = [Quest.deserialize(quest) for quest in (data.get("quests") or [])]
        quests.extend(
            Quest.deserialize({"title": title, "status": "active"}) for title in (data.get("active_quests") or [])
        )
        quests.extend(
            Quest.deserialize({"title": title, "status": "resolved"})
            for title in (data.get("completed_quests") or [])
        )

        return cls(
            version=int(data.get("version") or 1),
            current_location=str(data.get("current_location") or ""),
            inventory=[InventoryItem.deserialize(item) for item in (data.get("inventory") or [])],
            conditions=list(data.get("conditions") or []),
            known_npcs=dict(data.get("known_npcs") or {}),
            relationships=dict(data.get("relationships") or {}),
            quests=quests,
            world_flags=dict(data.get("world_flags") or {}),
        )


@dataclass
class StoryMoment:
    id: str = field(default_factory=lambda: str(uuid4()))
    game_id: str = ""
    caption: str = ""

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "caption": self.caption,
        }


@dataclass
class State:
    _id: str | None = None
    player_name: str = ""
    player_description: str = ""
    world_theme: str = "" 
    initialization_prompt: str = ""
    chat_history: list[Any] = field(default_factory=list)
    hit_points: int = MAX_HIT_POINTS
    game_over: bool = False
    game_over_summary: str = ""
    story_summary: str = ""
    unresolved_threads: list[str] = field(default_factory=list)
    summary_through_turn: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime | None = None
    revision: int = 0
    world_state: WorldState = field(default_factory=WorldState)
    player_attributes: PlayerAttributes = field(default_factory=PlayerAttributes)

    def __post_init__(self) -> None:
        if not MIN_HIT_POINTS <= self.hit_points <= MAX_HIT_POINTS:
            raise ValueError(f"hit_points must be between {MIN_HIT_POINTS} and {MAX_HIT_POINTS}.")
        if self.revision < 0:
            raise ValueError("revision must be non-negative.")
        if self.summary_through_turn < 0:
            raise ValueError("summary_through_turn must be non-negative.")

    def serialize(self) -> dict[str, Any]:
        data: dict[str, Any] = asdict(self)
        if data["_id"] is None:
            del data["_id"]
        return data

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "State":
        values = dict(data)
        for field_name in ("created_at", "updated_at"):
            value = values.get(field_name)
            if isinstance(value, str) and value:
                values[field_name] = datetime.fromisoformat(value)
        if values.get("_id") is not None:
            values["_id"] = str(values["_id"])
        values["world_state"] = WorldState.deserialize(values.get("world_state"))
        values["player_attributes"] = PlayerAttributes.deserialize(values.get("player_attributes"))
        return cls(**values)

class Sender(Enum):
    GAMEMASTER = auto()
    ERROR = auto()
    SYSTEM = auto()
    USER = auto()

    def __str__(self) -> str:
        return self.name.lower()
