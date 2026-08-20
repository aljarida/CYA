from typing import Literal

from pydantic import BaseModel, Field


class BooleanDecision(BaseModel):
    value: bool
    reason: str = ""


class DamageDecision(BaseModel):
    damage: int = Field(ge=0, le=5)
    reason: str = ""


class ActionAssessment(BaseModel):
    relevant: bool
    realistic: bool
    damage: int = Field(ge=0, le=5)
    reason: str = ""


StateDeltaOperationName = Literal[
    "set_location",
    "add_condition",
    "remove_condition",
    "upsert_npc",
    "set_relationship",
    "set_world_flag",
]


class StateDeltaOperation(BaseModel):
    operation: StateDeltaOperationName
    key: str
    value: str | bool | int | float | None = None
    reason: str = ""


class StateDelta(BaseModel):
    operations: list[StateDeltaOperation] = Field(default_factory=list)


InventoryOperationName = Literal["add_item", "remove_item"]


class InventoryOperation(BaseModel):
    operation: InventoryOperationName
    name: str
    description: str = ""
    weight_kg: float = Field(ge=0, default=0.0)
    quantity: int = Field(ge=1, default=1)
    reason: str = ""


QuestOperationName = Literal["start_quest", "advance_quest", "resolve_quest"]


class QuestOperation(BaseModel):
    operation: QuestOperationName
    title: str
    description: str = ""
    next_step: str = ""
    outcome: str = ""
    reason: str = ""


class NarrationResult(BaseModel):
    content: str
    state_delta: StateDelta = Field(default_factory=StateDelta)
    inventory_operations: list[InventoryOperation] = Field(default_factory=list)
    quest_operations: list[QuestOperation] = Field(default_factory=list)
    possible_moment: bool = False


class MomentPackage(BaseModel):
    is_moment: bool
    caption: str = ""
    image_prompt: str = ""
    reason: str = ""


class StorySummaryResult(BaseModel):
    story_summary: str
    unresolved_threads: list[str] = Field(default_factory=list)


class StartingInventoryItem(BaseModel):
    name: str
    description: str = ""
    weight_kg: float = Field(ge=0, default=0.0)
    quantity: int = Field(ge=1, default=1)


class StartingStateResult(BaseModel):
    starting_location: str
    starting_inventory: list[StartingInventoryItem] = Field(default_factory=list)
    starting_conditions: list[str] = Field(default_factory=list)
    age_years: int = Field(ge=0, le=150)
    height_cm: float = Field(gt=0)
    body_weight_kg: float = Field(gt=0)
    max_carry_weight_kg: float = Field(gt=0)
    reason: str = ""
