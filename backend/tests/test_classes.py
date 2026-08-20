from datetime import datetime

import pytest

from classes import (
    DEFAULT_MAX_CARRY_WEIGHT_KG,
    MAX_HIT_POINTS,
    MIN_HIT_POINTS,
    InventoryItem,
    PlayerAttributes,
    Quest,
    Sender,
    State,
    StoryMoment,
    WorldState,
)


def test_state_defaults_are_valid():
    state = State()

    assert state.hit_points == MAX_HIT_POINTS
    assert state.chat_history == []
    assert state.game_over is False
    assert state.world_state == WorldState()
    assert state.story_summary == ""
    assert state.unresolved_threads == []
    assert state.summary_through_turn == 0
    assert isinstance(state.created_at, datetime)


@pytest.mark.parametrize("hit_points", [MIN_HIT_POINTS, MAX_HIT_POINTS, 3])
def test_state_accepts_hit_points_inside_bounds(hit_points):
    assert State(hit_points=hit_points).hit_points == hit_points


@pytest.mark.parametrize("hit_points", [MIN_HIT_POINTS - 1, MAX_HIT_POINTS + 1])
def test_state_rejects_hit_points_outside_bounds(hit_points):
    with pytest.raises(ValueError, match="hit_points must be between"):
        State(hit_points=hit_points)


def test_serialize_omits_missing_game_id():
    serialized_state = State(player_name="Ada").serialize()

    assert "_id" not in serialized_state
    assert serialized_state["player_name"] == "Ada"


def test_serialize_preserves_existing_game_id():
    game_id = "saved-game"
    serialized_state = State(_id=game_id).serialize()

    assert serialized_state["_id"] == game_id


def test_deserialize_round_trips_serialized_state():
    game_id = "saved-game"
    state = State(
        _id=game_id,
        player_name="Morgan",
        player_description="careful scout",
        world_theme="salt flats",
        chat_history=[{"role": "system", "content": "begin"}],
        hit_points=2,
        story_summary="Morgan crossed the causeway.",
        unresolved_threads=["open the gate"],
        summary_through_turn=1,
        world_state=WorldState(
            current_location="glass market",
            inventory=[InventoryItem(id="item-1", name="brass key", weight_kg=0.2)],
            conditions=["tired"],
            known_npcs={"Iris": "glassmaker"},
            relationships={"Iris": "ally"},
            quests=[
                Quest(id="quest-1", title="find the lantern", status="active", current_step="check the cellar"),
                Quest(id="quest-2", title="cross the causeway", status="resolved", outcome="Made it across safely."),
            ],
            world_flags={"gate_open": True},
        ),
        player_attributes=PlayerAttributes(age_years=29, height_cm=170.0, body_weight_kg=65.0),
    )

    deserialized_state = State.deserialize(state.serialize())

    assert deserialized_state == state


def test_deserialize_old_state_without_world_state_uses_defaults():
    serialized_state = State(player_name="Ada").serialize()
    serialized_state.pop("world_state")

    deserialized_state = State.deserialize(serialized_state)

    assert deserialized_state.world_state == WorldState()


def test_deserialize_old_state_without_player_attributes_uses_defaults():
    serialized_state = State(player_name="Ada").serialize()
    serialized_state.pop("player_attributes")

    deserialized_state = State.deserialize(serialized_state)

    assert deserialized_state.player_attributes == PlayerAttributes()


def test_inventory_item_rejects_negative_weight():
    with pytest.raises(ValueError, match="weight_kg"):
        InventoryItem(name="rock", weight_kg=-1)


def test_inventory_item_rejects_non_positive_quantity():
    with pytest.raises(ValueError, match="quantity"):
        InventoryItem(name="rock", quantity=0)


def test_inventory_item_deserialize_generates_id_when_missing():
    item = InventoryItem.deserialize({"name": "torch", "weight_kg": 1.0})

    assert item.name == "torch"
    assert item.id


def test_world_state_deserialize_converts_legacy_string_inventory():
    ws = WorldState.deserialize({"inventory": ["brass key", "coin purse"]})

    assert [item.name for item in ws.inventory] == ["brass key", "coin purse"]
    assert all(item.weight_kg > 0 for item in ws.inventory)


def test_world_state_deserialize_round_trips_inventory_items():
    original = WorldState(inventory=[InventoryItem(id="item-1", name="torch", weight_kg=1.5, quantity=2)])

    deserialized = WorldState.deserialize(
        {"inventory": [{"id": "item-1", "name": "torch", "description": "", "weight_kg": 1.5, "quantity": 2}]}
    )

    assert deserialized.inventory == original.inventory


def test_world_state_total_inventory_weight_kg_sums_quantity():
    ws = WorldState(
        inventory=[
            InventoryItem(name="arrow", weight_kg=0.1, quantity=10),
            InventoryItem(name="sword", weight_kg=3.0, quantity=1),
        ]
    )

    assert ws.total_inventory_weight_kg() == pytest.approx(4.0)


def test_world_state_to_api_dict_serializes_inventory_items_camel_case():
    ws = WorldState(inventory=[InventoryItem(id="item-1", name="torch", description="lit", weight_kg=1.0, quantity=2)])

    result = ws.to_api_dict()

    assert result["inventory"] == [
        {"id": "item-1", "name": "torch", "description": "lit", "weightKg": 1.0, "quantity": 2}
    ]
    assert result["totalInventoryWeightKg"] == pytest.approx(2.0)


def test_player_attributes_deserialize_defaults_max_carry_weight():
    attributes = PlayerAttributes.deserialize({"age_years": 30})

    assert attributes.max_carry_weight_kg == DEFAULT_MAX_CARRY_WEIGHT_KG
    assert attributes.age_years == 30


def test_state_rejects_negative_summary_through_turn():
    with pytest.raises(ValueError, match="summary_through_turn"):
        State(summary_through_turn=-1)


def test_world_state_to_api_dict_maps_to_camel_case():
    ws = WorldState(
        current_location="glass market",
        inventory=[InventoryItem(id="item-1", name="brass key", weight_kg=0.1)],
        conditions=["tired"],
        known_npcs={"Iris": "glassmaker"},
        relationships={"Iris": "ally"},
        quests=[Quest(id="quest-1", title="find the lantern", status="active", current_step="check the cellar")],
        world_flags={"gate_open": True},
    )

    result = ws.to_api_dict()

    assert result["currentLocation"] == "glass market"
    assert result["inventory"] == [
        {"id": "item-1", "name": "brass key", "description": "", "weightKg": 0.1, "quantity": 1}
    ]
    assert result["conditions"] == ["tired"]
    assert result["knownNpcs"] == {"Iris": "glassmaker"}
    assert result["relationships"] == {"Iris": "ally"}
    assert result["quests"] == [
        {
            "id": "quest-1",
            "title": "find the lantern",
            "description": "",
            "status": "active",
            "currentStep": "check the cellar",
            "stepHistory": [],
            "outcome": "",
        }
    ]
    assert result["worldFlags"] == {"gate_open": True}


def test_quest_rejects_invalid_status():
    with pytest.raises(ValueError, match="status"):
        Quest(title="find the lantern", status="failed")


def test_quest_deserialize_generates_id_when_missing():
    quest = Quest.deserialize({"title": "find the lantern"})

    assert quest.title == "find the lantern"
    assert quest.status == "active"
    assert quest.id


def test_world_state_deserialize_converts_legacy_active_and_completed_quest_lists():
    ws = WorldState.deserialize(
        {"active_quests": ["find the lantern"], "completed_quests": ["cross the causeway"]}
    )

    statuses = {quest.title: quest.status for quest in ws.quests}
    assert statuses == {"find the lantern": "active", "cross the causeway": "resolved"}


def test_world_state_deserialize_round_trips_quests():
    original = WorldState(
        quests=[
            Quest(
                id="quest-1",
                title="find the lantern",
                description="Iris needs it back.",
                status="active",
                current_step="check the cellar",
                step_history=["ask around town"],
            )
        ]
    )

    deserialized = WorldState.deserialize(
        {
            "quests": [
                {
                    "id": "quest-1",
                    "title": "find the lantern",
                    "description": "Iris needs it back.",
                    "status": "active",
                    "current_step": "check the cellar",
                    "step_history": ["ask around town"],
                    "outcome": "",
                }
            ]
        }
    )

    assert deserialized.quests == original.quests


def test_world_state_to_api_dict_returns_copies():
    ws = WorldState(inventory=[InventoryItem(name="brass key")])
    result = ws.to_api_dict()
    result["inventory"].append({"id": "x", "name": "coin", "description": "", "weightKg": 0, "quantity": 1})

    assert ws.inventory == [InventoryItem(id=ws.inventory[0].id, name="brass key")]


def test_story_moment_generates_id_by_default():
    moment = StoryMoment(game_id="game-1", caption="Iris drives back the tide-wraith.")

    assert moment.id
    assert moment.to_api_dict() == {"id": moment.id, "caption": "Iris drives back the tide-wraith."}


def test_sender_string_values_match_api_contract():
    assert str(Sender.GAMEMASTER) == "gamemaster"
    assert str(Sender.ERROR) == "error"
    assert str(Sender.SYSTEM) == "system"
    assert str(Sender.USER) == "user"
