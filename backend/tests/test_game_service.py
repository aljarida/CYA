import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest

from classes import InventoryItem, PlayerAttributes, Quest, Sender, State, StoryMoment, WorldState
from database import RevisionConflictError
from game_service import GameService
from images import Image
from llm import LLMResponseError, LLMTransientError
from llm_results import ActionAssessment, MomentPackage, NarrationResult, StateDelta, StorySummaryResult
from observability import InMemoryTraceRecorder


class FakeRepository:
    def __init__(
        self,
        states: dict[str, State] | None = None,
        conflict_on_save: bool = False,
        conflict_on_save_number: int | None = None,
    ) -> None:
        self.states = states or {}
        self.conflict_on_save = conflict_on_save
        self.conflict_on_save_number = conflict_on_save_number
        self.saved_states: list[State] = []
        self.get_game_calls: list[str] = []
        self.added_moments: list[tuple[str, str, bytes]] = []

    def save_game(self, state: State) -> None:
        if self.conflict_on_save or self.conflict_on_save_number == len(self.saved_states) + 1:
            raise RevisionConflictError("conflict")
        self.saved_states.append(state)
        if state._id is not None:
            self.states[state._id] = state

    def save_game_and_images(self, state: State, images: Any) -> None:
        self.save_game(state)

    def delete_game(self, game_id: str) -> bool:
        return self.states.pop(game_id, None) is not None

    def get_image_bytes(self, game_id: str) -> tuple[bytes, bytes] | None:
        return None

    def all_games(self) -> list[State]:
        return list(self.states.values())

    def get_game(self, game_id: str) -> State | None:
        self.get_game_calls.append(game_id)
        return self.states.get(game_id)

    def add_moment(self, game_id: str, caption: str, image_bytes: bytes) -> StoryMoment:
        self.added_moments.append((game_id, caption, image_bytes))
        return StoryMoment(game_id=game_id, caption=caption)

    def list_moments(self, game_id: str) -> list[tuple[StoryMoment, bytes]]:
        return [
            (StoryMoment(game_id=stored_game_id, caption=caption), image_bytes)
            for stored_game_id, caption, image_bytes in self.added_moments
            if stored_game_id == game_id
        ]


class FakeLLMClient:
    def __init__(
        self,
        *,
        relevant: bool = True,
        realistic: bool = True,
        narration: str = "A path opens ahead.",
        damage: int = 0,
        state_delta_operations: list[dict[str, Any]] | None = None,
        inventory_operations: list[dict[str, Any]] | None = None,
        quest_operations: list[dict[str, Any]] | None = None,
        game_over_summary: str = "The story ended.",
        story_summary: str = "Updated summary.",
        unresolved_threads: list[str] | None = None,
        fail_summary: bool = False,
        assessment_error: Exception | None = None,
        narration_error: Exception | None = None,
        possible_moment: bool = False,
        moment_is_moment: bool = False,
        moment_caption: str = "A grand battle is won.",
        moment_image_prompt: str = "a dramatic, painterly battle scene",
        moment_error: Exception | None = None,
        image_bytes: bytes = b"fake-image-bytes",
    ) -> None:
        self.relevant = relevant
        self.realistic = realistic
        self.narration = narration
        self.damage = damage
        self.state_delta_operations = state_delta_operations or []
        self.inventory_operations = inventory_operations or []
        self.quest_operations = quest_operations or []
        self.game_over_summary = game_over_summary
        self.story_summary = story_summary
        self.unresolved_threads = unresolved_threads or []
        self.fail_summary = fail_summary
        self.assessment_error = assessment_error
        self.narration_error = narration_error
        self.possible_moment = possible_moment
        self.moment_is_moment = moment_is_moment
        self.moment_caption = moment_caption
        self.moment_image_prompt = moment_image_prompt
        self.moment_error = moment_error
        self.image_bytes = image_bytes
        self.text_model = "fake-text-model"
        self.retry_config = SimpleNamespace(retry_limit=2)
        self.last_retry_count = 0
        self.last_token_usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        self.structured_models: list[type[Any]] = []
        self.structured_message_models: list[type[Any]] = []
        self.structured_prompts: list[tuple[str, str, type[Any]]] = []
        self.messages_calls: list[list[dict[str, str]]] = []
        self.text_calls: list[tuple[str, str]] = []
        self.image_calls: list[tuple[str, str]] = []

    def text(self, system: str, user: str, temperature: float = 0.0) -> str:
        self.text_calls.append((system, user))
        return self.game_over_summary

    def structured(
        self,
        system: str,
        user: str,
        response_model: type[Any],
        temperature: float = 0.0,
    ) -> Any:
        raise AssertionError("play_turn should not use sync structured model calls")

    async def async_text(self, system: str, user: str, temperature: float = 0.0) -> str:
        return ""

    async def async_structured(
        self,
        system: str,
        user: str,
        response_model: type[Any],
        temperature: float = 0.0,
    ) -> Any:
        self.structured_models.append(response_model)
        self.structured_prompts.append((system, user, response_model))
        if response_model is ActionAssessment:
            if self.assessment_error is not None:
                raise self.assessment_error
            return ActionAssessment(
                relevant=self.relevant,
                realistic=self.realistic,
                damage=self.damage,
                reason="fake",
            )
        if response_model is StorySummaryResult:
            if self.fail_summary:
                raise RuntimeError("summary failed")
            return StorySummaryResult(
                story_summary=self.story_summary,
                unresolved_threads=self.unresolved_threads,
            )
        if response_model is MomentPackage:
            if self.moment_error is not None:
                raise self.moment_error
            return MomentPackage(
                is_moment=self.moment_is_moment,
                caption=self.moment_caption if self.moment_is_moment else "",
                image_prompt=self.moment_image_prompt if self.moment_is_moment else "",
            )
        raise AssertionError(f"unexpected structured response model: {response_model!r}")

    async def async_messages(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        raise AssertionError("play_turn should use structured narration calls")

    async def async_structured_messages(
        self,
        messages: list[dict[str, str]],
        response_model: type[Any],
        temperature: float = 0.0,
    ) -> Any:
        self.structured_message_models.append(response_model)
        self.messages_calls.append(deepcopy(messages))
        if response_model is NarrationResult:
            if self.narration_error is not None:
                raise self.narration_error
            return NarrationResult(
                content=self.narration,
                state_delta=StateDelta(operations=self.state_delta_operations),
                inventory_operations=self.inventory_operations,
                quest_operations=self.quest_operations,
                possible_moment=self.possible_moment,
            )
        raise AssertionError(f"unexpected structured message response model: {response_model!r}")

    async def generate_image_url(self, prompt: str, size: str) -> str:
        return ""

    async def generate_image_bytes(self, prompt: str, size: str) -> bytes:
        self.image_calls.append((prompt, size))
        return self.image_bytes


def run_turn(service: GameService, game_id: str | None, content: str):
    return asyncio.run(service.play_turn(game_id, content))


def turn_history(count: int) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": "setup"}]
    for index in range(count):
        messages.append({"role": "user", "content": f"user turn {index}"})
        messages.append({"role": "assistant", "content": f"assistant turn {index}"})
    return messages


def test_play_turn_success_updates_history_applies_damage_and_saves():
    state = State(_id="game-1", hit_points=5, chat_history=[{"role": "system", "content": "setup"}])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="A bridge appears.", damage=2)

    result = run_turn(GameService(repository, llm_client), "game-1", "Look around.")

    assert result.status_code == 200
    assert result.sender is Sender.GAMEMASTER
    assert result.content == "A bridge appears."
    assert result.hit_points == 3
    response = result.to_response()
    assert response["sender"] == str(Sender.GAMEMASTER)
    assert response["content"] == "A bridge appears."
    assert response["hitPoints"] == 3
    assert "worldState" in response
    assert state.chat_history == [
        {"role": "system", "content": "setup"},
        {"role": "user", "content": "Look around."},
        {"role": "assistant", "content": "A bridge appears."},
    ]
    assert repository.saved_states == [state]
    assert llm_client.structured_models == [ActionAssessment]
    assert llm_client.structured_message_models == [NarrationResult]
    assert len(llm_client.messages_calls) == 1


def test_play_turn_records_correlated_stage_traces_without_raw_player_text():
    state = State(_id="game-1", hit_points=5, chat_history=[{"role": "system", "content": "setup"}])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="A bridge appears.", damage=1)
    trace_recorder = InMemoryTraceRecorder()

    result = run_turn(
        GameService(repository, llm_client, trace_recorder=trace_recorder),
        "game-1",
        "secret player text",
    )

    assert result.status_code == 200
    assert [trace.stage for trace in trace_recorder.traces] == [
        "action_assessment",
        "narration",
        "persist_turn",
    ]
    correlation_ids = {trace.correlation_id for trace in trace_recorder.traces}
    assert len(correlation_ids) == 1
    for trace in trace_recorder.traces:
        assert trace.game_id == "game-1"
        assert trace.turn_id == 0
        assert trace.duration_ms >= 0
        assert trace.status == "success"
        assert trace.prompt_version == "v1"
        assert "secret player text" not in str(trace)
    for trace in trace_recorder.traces[:2]:
        assert trace.model == "fake-text-model"
        assert trace.retry_count == 0
        assert trace.token_usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert trace_recorder.traces[2].model is None
    assert trace_recorder.traces[2].retry_count is None
    assert trace_recorder.traces[2].token_usage is None
    assert trace_recorder.traces[0].accepted is True
    assert trace_recorder.traces[1].accepted is True
    assert trace_recorder.traces[2].accepted is None
    assert len(trace_recorder.turn_traces) == 1
    assert trace_recorder.turn_traces[0].correlation_id == trace_recorder.traces[0].correlation_id
    assert trace_recorder.turn_traces[0].game_id == "game-1"
    assert trace_recorder.turn_traces[0].turn_id == 0
    assert trace_recorder.turn_traces[0].duration_ms >= 0
    assert trace_recorder.turn_traces[0].status == "success"


def test_play_turn_records_rejected_assessment_trace_without_narration():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(relevant=False, realistic=True)
    trace_recorder = InMemoryTraceRecorder()

    result = run_turn(
        GameService(repository, llm_client, trace_recorder=trace_recorder),
        "game-1",
        "irrelevant secret text",
    )

    assert result.status_code == 400
    assert [trace.stage for trace in trace_recorder.traces] == ["action_assessment"]
    assert trace_recorder.traces[0].accepted is False
    assert "irrelevant secret text" not in str(trace_recorder.traces[0])
    assert repository.saved_states == []


def test_play_turn_builds_bounded_narration_context_without_truncating_stored_history():
    old_user_turn = "OLD_VERBATIM_USER_TURN " + ("x" * 6000)
    old_assistant_turn = "OLD_VERBATIM_ASSISTANT_TURN " + ("y" * 6000)
    recent_user_turn = "RECENT_USER_TURN inspect the glass compass"
    recent_assistant_turn = "RECENT_ASSISTANT_TURN the compass points north"
    original_history = [
        {"role": "system", "content": "You are the gamemaster. Keep the story grounded."},
        {"role": "user", "content": old_user_turn},
        {"role": "assistant", "content": old_assistant_turn},
        {"role": "user", "content": recent_user_turn},
        {"role": "assistant", "content": recent_assistant_turn},
    ]
    state = State(
        _id="game-1",
        chat_history=deepcopy(original_history),
        world_state=WorldState(
            current_location="glass observatory",
            inventory=[InventoryItem(name="glass compass", weight_kg=0.3)],
            quests=[Quest(title="find the north door", status="active")],
        ),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="The compass hums.")

    result = run_turn(GameService(repository, llm_client), "game-1", "Follow the compass.")

    assert result.status_code == 200
    assert len(llm_client.messages_calls) == 1
    narration_messages = llm_client.messages_calls[0]
    narration_text = "\n".join(message["content"] for message in narration_messages)
    assert "OLD_VERBATIM_USER_TURN" not in narration_text
    assert "OLD_VERBATIM_ASSISTANT_TURN" not in narration_text
    assert recent_user_turn in narration_text
    assert recent_assistant_turn in narration_text
    assert "Follow the compass." in narration_text
    assert state.chat_history == [
        *original_history,
        {"role": "user", "content": "Follow the compass."},
        {"role": "assistant", "content": "The compass hums."},
    ]


def test_play_turn_narration_context_keeps_canonical_state_and_valid_roles_under_budget_pressure():
    state = State(
        _id="game-1",
        chat_history=[
            {"role": "system", "content": "System rules for the adventure."},
            {"role": "user", "content": "OLD_VERBATIM_TURN " + ("x" * 12000)},
            {"role": "assistant", "content": "The old event resolves."},
        ],
        world_state=WorldState(
            current_location="silver archive",
            inventory=[InventoryItem(name="sun key", weight_kg=0.1), InventoryItem(name="map", weight_kg=0.05)],
            conditions=["tired"],
            known_npcs={"Iris": "glassmaker"},
            relationships={"Iris": "ally"},
            quests=[
                Quest(title="open the sun gate", status="active", current_step="ask the keeper"),
                Quest(title="cross the causeway", status="resolved", outcome="Made it across safely."),
            ],
            world_flags={"gate_open": False},
        ),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="The archive doors shake.")

    result = run_turn(GameService(repository, llm_client), "game-1", "Use the sun key.")

    assert result.status_code == 200
    narration_messages = llm_client.messages_calls[0]
    assert {message["role"] for message in narration_messages} <= {"system", "user", "assistant"}
    assert narration_messages[0]["role"] == "system"
    narration_text = "\n".join(message["content"] for message in narration_messages)
    assert "=== Canonical world state ===" in narration_text
    assert "Current location: silver archive" in narration_text
    assert "sun key" in narration_text
    assert "map" in narration_text
    assert "Conditions: tired" in narration_text
    assert "Known NPCs: Iris: glassmaker" in narration_text
    assert "Relationships: Iris: ally" in narration_text
    assert "open the sun gate (active — lead: ask the keeper)" in narration_text
    assert "cross the causeway (resolved — outcome: Made it across safely.)" in narration_text
    assert "World flags: gate_open: False" in narration_text
    assert "OLD_VERBATIM_TURN" not in narration_text


def test_play_turn_applies_state_delta_for_location_and_relationships():
    state = State(
        _id="game-1",
        chat_history=[{"role": "system", "content": "setup"}],
        world_state=WorldState(current_location="docks", relationships={"Iris": "wary"}),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You reach the glass market and Iris greets you warmly.",
        state_delta_operations=[
            {
                "operation": "set_location",
                "key": "current_location",
                "value": "glass market",
                "reason": "The player walks there.",
            },
            {"operation": "set_relationship", "key": "Iris", "value": "ally", "reason": "Iris now trusts the player."},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Go to Iris.")

    assert result.status_code == 200
    assert state.world_state.current_location == "glass market"
    assert state.world_state.relationships["Iris"] == "ally"
    assert repository.saved_states == [state]
    assert llm_client.structured_models == [ActionAssessment]
    assert llm_client.structured_message_models == [NarrationResult]


def test_play_turn_starts_a_new_quest():
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Iris asks you to find the lantern hidden beneath the old bridge.",
        quest_operations=[
            {
                "operation": "start_quest",
                "title": "find the lantern",
                "description": "Iris lost her lantern near the bridge.",
                "next_step": "search beneath the old bridge",
            },
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Talk to Iris.")

    assert result.status_code == 200
    assert len(state.world_state.quests) == 1
    quest = state.world_state.quests[0]
    assert quest.title == "find the lantern"
    assert quest.status == "active"
    assert quest.current_step == "search beneath the old bridge"


def test_play_turn_advances_a_quest_step():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(
            quests=[Quest(title="find the lantern", status="active", current_step="search beneath the old bridge")]
        ),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You find the lantern is broken; find the lantern smith to repair it.",
        quest_operations=[
            {
                "operation": "advance_quest",
                "title": "find the lantern",
                "next_step": "find the lantern smith to repair it",
            },
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Search under the bridge.")

    assert result.status_code == 200
    quest = state.world_state.quests[0]
    assert quest.status == "active"
    assert quest.current_step == "find the lantern smith to repair it"
    assert quest.step_history == ["search beneath the old bridge"]


def test_play_turn_resolves_a_quest_with_a_neutral_outcome_on_derailment():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(
            quests=[Quest(title="become the king's aide", status="active", current_step="earn his trust")]
        ),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You strike down the king in a fit of rage; the quest to become the king's aide is no longer possible.",
        quest_operations=[
            {
                "operation": "resolve_quest",
                "title": "become the king's aide",
                "outcome": "The king is dead; this path is closed.",
            },
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Attack the king.")

    assert result.status_code == 200
    quest = state.world_state.quests[0]
    assert quest.status == "resolved"
    assert quest.current_step == ""
    assert quest.outcome == "The king is dead; this path is closed."
    assert quest.step_history == ["earn his trust"]


def test_play_turn_matches_quest_titles_case_insensitively():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(quests=[Quest(title="Find The Lantern", status="active")]),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You finally find the lantern, safe and whole.",
        quest_operations=[
            {"operation": "resolve_quest", "title": "find the lantern", "outcome": "Recovered safe and whole."},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Grab the lantern.")

    assert result.status_code == 200
    assert state.world_state.quests[0].status == "resolved"


def test_play_turn_drops_ungrounded_quest_operation():
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Nothing of note happens.",
        quest_operations=[
            {"operation": "start_quest", "title": "slay the ancient dragon", "next_step": "find its lair"},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "I claim I've been sent to slay a dragon.")

    assert result.status_code == 200
    assert state.world_state.quests == []


def test_play_turn_starts_quest_with_formalized_title_not_quoted_verbatim():
    """The model authors a concise quest title rather than quoting the narration
    verbatim (e.g. 'Retrieve the Elder's Sword' vs narration that just says
    'retrieve the sword') - grounding must tolerate that via word overlap."""
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You agree to retrieve the sword from the old watchtower for the elder.",
        quest_operations=[
            {
                "operation": "start_quest",
                "title": "Retrieve the Elder's Sword",
                "description": "The elder asked for her late husband's sword back.",
                "next_step": "Travel to the old watchtower.",
            },
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "I agree to help the elder.")

    assert result.status_code == 200
    assert len(state.world_state.quests) == 1
    assert state.world_state.quests[0].title == "Retrieve the Elder's Sword"


def test_play_turn_drops_advance_quest_with_ungrounded_next_step():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(quests=[Quest(title="find the lantern", status="active", current_step="ask around")]),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Nothing of note happens.",
        quest_operations=[
            {"operation": "advance_quest", "title": "find the lantern", "next_step": "storm the castle gates"},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Wait.")

    assert result.status_code == 200
    quest = state.world_state.quests[0]
    assert quest.current_step == "ask around"


def test_play_turn_applies_grounded_inventory_operations():
    state = State(
        _id="game-1",
        chat_history=[{"role": "system", "content": "setup"}],
        world_state=WorldState(inventory=[InventoryItem(name="rusty key", weight_kg=0.1)]),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You trade the rusty key for a brass key and reach the glass market.",
        inventory_operations=[
            {"operation": "add_item", "name": "brass key", "weight_kg": 0.2, "reason": "Iris gives it to the player."},
            {"operation": "remove_item", "name": "rusty key", "reason": "The key is traded away."},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Trade keys with Iris.")

    assert result.status_code == 200
    assert [item.name for item in state.world_state.inventory] == ["brass key"]
    assert repository.saved_states == [state]


def test_play_turn_merges_repeated_add_item_operations_by_name():
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You pocket two coins.",
        inventory_operations=[
            {"operation": "add_item", "name": "coin", "weight_kg": 0.1},
            {"operation": "add_item", "name": "coin", "weight_kg": 0.1},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Pick up the coins.")

    assert result.status_code == 200
    assert len(state.world_state.inventory) == 1
    assert state.world_state.inventory[0].name == "coin"
    assert state.world_state.inventory[0].quantity == 2


def test_play_turn_repeated_remove_item_is_idempotent():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(inventory=[InventoryItem(name="brass key", weight_kg=0.2, quantity=1)]),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You toss aside the brass key.",
        inventory_operations=[
            {"operation": "remove_item", "name": "brass key"},
            {"operation": "remove_item", "name": "brass key"},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Discard the key.")

    assert result.status_code == 200
    assert state.world_state.inventory == []


def test_play_turn_blocks_add_item_that_would_exceed_carry_capacity():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(),
        player_attributes=PlayerAttributes(max_carry_weight_kg=1.0),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You try to heave the anvil into your pack.",
        inventory_operations=[
            {"operation": "add_item", "name": "anvil", "weight_kg": 50.0},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Take the anvil.")

    assert result.status_code == 200
    assert state.world_state.inventory == []
    assert "too heavy" in result.content.lower()


def test_play_turn_drops_ungrounded_inventory_operation():
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Nothing of note happens.",
        inventory_operations=[
            {"operation": "add_item", "name": "excalibur", "weight_kg": 2.0},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "I claim I already have a legendary sword.")

    assert result.status_code == 200
    assert state.world_state.inventory == []


def test_play_turn_ignores_blank_state_delta_keys_predictably():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You find a coin.",
        state_delta_operations=[
            {"operation": "set_relationship", "key": "", "value": "ally"},
        ],
        inventory_operations=[
            {"operation": "add_item", "name": "   ", "weight_kg": 0.1},
            {"operation": "add_item", "name": "coin", "weight_kg": 0.1},
        ],
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Search the fountain.")

    assert result.status_code == 200
    assert [item.name for item in state.world_state.inventory] == ["coin"]
    assert state.world_state.relationships == {}
    assert repository.saved_states == [state]


@pytest.mark.parametrize(
    ("relevant", "realistic", "expected_content"),
    [
        (False, False, "Your message is not relevant or realistic."),
        (False, True, "Your message is not relevant to the game story."),
        (True, False, "Your message does not respect the realism of the game story."),
    ],
)
def test_play_turn_rejects_irrelevant_or_unrealistic_actions(relevant, realistic, expected_content):
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(relevant=relevant, realistic=realistic)

    result = run_turn(GameService(repository, llm_client), "game-1", "Do impossible things.")

    assert result.status_code == 400
    assert result.sender is Sender.ERROR
    assert result.content == expected_content
    assert state.chat_history == []
    assert repository.saved_states == []
    assert llm_client.messages_calls == []
    assert llm_client.structured_models == [ActionAssessment]
    assert llm_client.structured_message_models == []


def test_play_turn_returns_existing_game_over_message_without_mutating_or_saving():
    state = State(_id="game-1", game_over=True, chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient()

    result = run_turn(GameService(repository, llm_client), "game-1", "Continue.")

    assert result.to_response() == {
        "sender": str(Sender.SYSTEM),
        "content": "You are dead. Please refresh the browser to play again.",
    }
    assert repository.saved_states == []
    assert llm_client.structured_models == []
    assert llm_client.structured_message_models == []


def test_play_turn_returns_error_for_empty_narration_without_saving():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="")

    result = run_turn(GameService(repository, llm_client), "game-1", "Look around.")

    assert result.status_code == 500
    assert result.sender is Sender.ERROR
    assert result.content == "Gamemaster failed to generate a response."
    assert state.chat_history == []
    assert repository.saved_states == []


def test_play_turn_maps_transient_assessment_failure_to_safe_error_without_saving():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(assessment_error=LLMTransientError("provider unavailable"))

    result = run_turn(GameService(repository, llm_client), "game-1", "Look around.")

    assert result.status_code == 502
    assert result.sender is Sender.ERROR
    assert result.content.startswith("The gamemaster is temporarily unavailable. Please try again. Reference: ")
    assert "provider unavailable" not in result.content
    assert state.chat_history == []
    assert repository.saved_states == []


def test_play_turn_maps_malformed_narration_failure_to_safe_error_without_saving():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration_error=LLMResponseError("bad structured output"))

    result = run_turn(GameService(repository, llm_client), "game-1", "Look around.")

    assert result.status_code == 502
    assert result.sender is Sender.ERROR
    assert result.content.startswith("The gamemaster is temporarily unavailable. Please try again. Reference: ")
    assert "bad structured output" not in result.content
    assert state.chat_history == []
    assert repository.saved_states == []


@pytest.mark.parametrize(
    ("game_id", "expected_content"),
    [
        (None, "Game ID is required. Please initialize or load a game first."),
        ("  ", "Game ID is required. Please initialize or load a game first."),
        ("missing-game", "Invalid game ID. Please initialize or load a game first."),
    ],
)
def test_play_turn_returns_error_for_missing_or_unknown_game(game_id, expected_content):
    repository = FakeRepository()
    llm_client = FakeLLMClient()

    result = run_turn(GameService(repository, llm_client), game_id, "Hello.")

    assert result.status_code == 400
    assert result.sender is Sender.ERROR
    assert result.content == expected_content
    assert repository.saved_states == []
    assert llm_client.structured_models == []


def test_play_turn_marks_game_over_and_omits_assistant_history_when_damage_is_fatal():
    state = State(_id="game-1", hit_points=1, chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="The cliff gives way.",
        damage=2,
        game_over_summary="Morgan fell in the ravine.",
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Step forward.")

    response = result.to_response()
    assert response["sender"] == str(Sender.SYSTEM)
    assert response["content"] == "Oh, no! Unfortunately, you have died!"
    assert response["gameOverSummary"] == "Morgan fell in the ravine."
    assert response["hitPoints"] == 0
    assert "worldState" in response
    assert state.hit_points == 0
    assert state.game_over is True
    assert state.game_over_summary == "Morgan fell in the ravine."
    assert state.chat_history == [{"role": "user", "content": "Step forward."}]
    assert repository.saved_states == [state]


def test_play_turn_refreshes_summary_after_threshold_without_recent_turn_duplication():
    state = State(
        _id="game-1",
        chat_history=turn_history(3),
        story_summary="Turn zero is already summarized.",
        unresolved_threads=["old thread"],
        summary_through_turn=1,
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Current turn reply.",
        story_summary="Updated summary through turn two.",
        unresolved_threads=["open gate"],
    )

    result = run_turn(
        GameService(
            repository,
            llm_client,
            summary_refresh_turn_threshold=2,
            recent_turns_to_keep_unsummarized=1,
        ),
        "game-1",
        "current turn",
    )

    assert result.status_code == 200
    assert state.story_summary == "Updated summary through turn two."
    assert state.unresolved_threads == ["open gate"]
    assert state.summary_through_turn == 3
    assert len(repository.saved_states) == 2
    summary_prompt = next(
        user_prompt
        for _, user_prompt, response_model in llm_client.structured_prompts
        if response_model is StorySummaryResult
    )
    assert "Turn zero is already summarized." in summary_prompt
    assert "old thread" in summary_prompt
    assert "user turn 0" not in summary_prompt
    assert "assistant turn 0" not in summary_prompt
    assert "user turn 1" in summary_prompt
    assert "assistant turn 1" in summary_prompt
    assert "user turn 2" in summary_prompt
    assert "assistant turn 2" in summary_prompt
    assert "current turn" not in summary_prompt
    assert "Current turn reply." not in summary_prompt


def test_play_turn_does_not_refresh_summary_before_threshold():
    state = State(_id="game-1", chat_history=turn_history(2), summary_through_turn=1)
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="Current turn reply.")

    result = run_turn(
        GameService(
            repository,
            llm_client,
            summary_refresh_turn_threshold=3,
            recent_turns_to_keep_unsummarized=1,
        ),
        "game-1",
        "current turn",
    )

    assert result.status_code == 200
    assert state.story_summary == ""
    assert state.unresolved_threads == []
    assert state.summary_through_turn == 1
    assert repository.saved_states == [state]
    assert StorySummaryResult not in llm_client.structured_models


def test_play_turn_summary_failure_does_not_lose_player_turn():
    state = State(_id="game-1", chat_history=turn_history(2), summary_through_turn=0)
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="Current turn reply.", fail_summary=True)

    result = run_turn(
        GameService(
            repository,
            llm_client,
            summary_refresh_turn_threshold=1,
            recent_turns_to_keep_unsummarized=1,
        ),
        "game-1",
        "current turn",
    )

    assert result.status_code == 200
    assert state.chat_history[-2:] == [
        {"role": "user", "content": "current turn"},
        {"role": "assistant", "content": "Current turn reply."},
    ]
    assert state.story_summary == ""
    assert state.summary_through_turn == 0
    assert repository.saved_states == [state]
    assert StorySummaryResult in llm_client.structured_models


def test_play_turn_summary_save_conflict_keeps_successful_turn_response_retryable():
    state = State(_id="game-1", chat_history=turn_history(2), summary_through_turn=0)
    repository = FakeRepository({"game-1": state}, conflict_on_save_number=2)
    llm_client = FakeLLMClient(
        narration="Current turn reply.",
        story_summary="Summary written locally but not persisted.",
        unresolved_threads=["retry later"],
    )

    result = run_turn(
        GameService(
            repository,
            llm_client,
            summary_refresh_turn_threshold=1,
            recent_turns_to_keep_unsummarized=1,
        ),
        "game-1",
        "current turn",
    )

    assert result.status_code == 200
    assert result.content == "Current turn reply."
    assert len(repository.saved_states) == 1
    assert state.chat_history[-2:] == [
        {"role": "user", "content": "current turn"},
        {"role": "assistant", "content": "Current turn reply."},
    ]


def test_play_turn_summary_refresh_is_idempotent_after_summary_through_turn_advances():
    state = State(_id="game-1", chat_history=turn_history(2), summary_through_turn=2)
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="Current turn reply.")

    result = run_turn(
        GameService(
            repository,
            llm_client,
            summary_refresh_turn_threshold=1,
            recent_turns_to_keep_unsummarized=1,
        ),
        "game-1",
        "current turn",
    )

    assert result.status_code == 200
    assert StorySummaryResult not in llm_client.structured_models
    assert state.summary_through_turn == 2
    assert repository.saved_states == [state]


def test_play_turn_returns_conflict_when_save_detects_stale_revision():
    state = State(_id="game-1", hit_points=5, chat_history=[], revision=2)
    repository = FakeRepository({"game-1": state}, conflict_on_save=True)
    llm_client = FakeLLMClient(narration="A door opens.", damage=0)

    result = run_turn(GameService(repository, llm_client), "game-1", "Open the door.")

    assert result.status_code == 409
    assert result.sender is Sender.ERROR
    assert result.content == "Game state was modified by another request. Please reload and try again."
    assert repository.saved_states == []


def test_play_turn_override_skips_relevance_and_realism_checks():
    state = State(_id="game-1", hit_points=5, chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(relevant=False, realistic=False, narration="Debug reply.")

    result = run_turn(GameService(repository, llm_client), "game-1", "@override steal the crown")

    assert result.status_code == 200
    assert result.content == "Debug reply."
    assert state.chat_history[0]["content"] == " steal the crown"
    assert llm_client.structured_models == []
    assert llm_client.structured_message_models == [NarrationResult]


def test_discard_item_removes_matching_item_by_id():
    item = InventoryItem(name="brass key", weight_kg=0.2)
    state = State(_id="game-1", chat_history=[], world_state=WorldState(inventory=[item]))
    repository = FakeRepository({"game-1": state})

    result = GameService(repository, FakeLLMClient()).discard_item("game-1", item.id)

    assert result.status_code == 200
    assert result.sender is Sender.SYSTEM
    assert state.world_state.inventory == []
    assert repository.saved_states == [state]


def test_discard_item_missing_item_id_returns_400():
    result = GameService(FakeRepository(), FakeLLMClient()).discard_item("game-1", None)

    assert result.status_code == 400


def test_discard_item_invalid_game_id_returns_400():
    result = GameService(FakeRepository(), FakeLLMClient()).discard_item(None, "item-1")

    assert result.status_code == 400


def test_discard_item_unknown_item_returns_400():
    state = State(_id="game-1", chat_history=[], world_state=WorldState())
    repository = FakeRepository({"game-1": state})

    result = GameService(repository, FakeLLMClient()).discard_item("game-1", "does-not-exist")

    assert result.status_code == 400
    assert repository.saved_states == []


def test_discard_item_conflict_returns_409():
    item = InventoryItem(name="brass key")
    state = State(_id="game-1", chat_history=[], world_state=WorldState(inventory=[item]))
    repository = FakeRepository({"game-1": state}, conflict_on_save=True)

    result = GameService(repository, FakeLLMClient()).discard_item("game-1", item.id)

    assert result.status_code == 409


def test_discard_item_does_not_mutate_chat_history():
    item = InventoryItem(name="brass key")
    state = State(_id="game-1", chat_history=[{"role": "system", "content": "setup"}], world_state=WorldState(inventory=[item]))
    repository = FakeRepository({"game-1": state})

    GameService(repository, FakeLLMClient()).discard_item("game-1", item.id)

    assert state.chat_history == [{"role": "system", "content": "setup"}]


def test_play_turn_captures_moment_on_near_fatal_damage():
    state = State(_id="game-1", hit_points=5, chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You barely survive the dragon's strike.",
        damage=4,
        moment_is_moment=True,
        moment_caption="Iris survives the dragon's strike.",
        moment_image_prompt="a warrior narrowly dodging a dragon's claws",
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Dodge the dragon.")

    assert result.status_code == 200
    assert MomentPackage in llm_client.structured_models
    assert llm_client.image_calls == [("a warrior narrowly dodging a dragon's claws", "1536x1024")]
    assert repository.added_moments == [
        ("game-1", "Iris survives the dragon's strike.", b"fake-image-bytes")
    ]
    response = result.to_response()
    assert response["moment"]["caption"] == "Iris survives the dragon's strike."
    assert response["moment"]["imageSrc"].startswith("data:image/png;base64,")
    assert response["moment"]["id"]


def test_play_turn_captures_moment_on_quest_resolution():
    state = State(
        _id="game-1",
        chat_history=[],
        world_state=WorldState(quests=[Quest(title="find the lantern", status="active")]),
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="You finally find the lantern, safe and whole.",
        quest_operations=[
            {"operation": "resolve_quest", "title": "find the lantern", "outcome": "Recovered safe and whole."},
        ],
        moment_is_moment=True,
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Grab the lantern.")

    assert result.status_code == 200
    assert MomentPackage in llm_client.structured_models
    assert len(repository.added_moments) == 1


def test_play_turn_captures_moment_when_narration_flags_possible_moment():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(
        narration="Iris pulls the sword from the stone.",
        possible_moment=True,
        moment_is_moment=True,
    )

    result = run_turn(GameService(repository, llm_client), "game-1", "Pull the sword.")

    assert result.status_code == 200
    assert MomentPackage in llm_client.structured_models
    assert len(repository.added_moments) == 1


def test_play_turn_does_not_capture_moment_on_ordinary_turn():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="You walk down the hall.", damage=1)

    result = run_turn(GameService(repository, llm_client), "game-1", "Walk.")

    assert result.status_code == 200
    assert MomentPackage not in llm_client.structured_models
    assert repository.added_moments == []
    assert result.to_response().get("moment") is None


def test_play_turn_omits_moment_when_model_declines_despite_trigger():
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="A quiet, unremarkable near-miss.", damage=4, moment_is_moment=False)

    result = run_turn(GameService(repository, llm_client), "game-1", "Dodge.")

    assert result.status_code == 200
    assert MomentPackage in llm_client.structured_models
    assert repository.added_moments == []
    assert result.to_response().get("moment") is None


def test_play_turn_moment_capture_failure_does_not_break_turn(monkeypatch):
    monkeypatch.delenv("SKIP_IMAGE_GENERATION", raising=False)
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="A tense standoff.", damage=4, moment_error=RuntimeError("model unavailable"))

    result = run_turn(GameService(repository, llm_client), "game-1", "Stand firm.")

    assert result.status_code == 200
    assert result.content == "A tense standoff."
    assert result.to_response().get("moment") is None
    assert repository.saved_states == [state]


def test_play_turn_moment_capture_uses_debug_image_when_skipping_generation(monkeypatch):
    monkeypatch.setenv("SKIP_IMAGE_GENERATION", "true")
    state = State(_id="game-1", chat_history=[])
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="A grand victory.", damage=4, moment_is_moment=True)

    result = run_turn(GameService(repository, llm_client), "game-1", "Fight.")

    assert result.status_code == 200
    assert llm_client.image_calls == []
    assert len(repository.added_moments) == 1
    assert repository.added_moments[0][2] == Image.debug_backdrop_bytes()


def test_play_turn_exposes_story_summary_and_unresolved_threads_in_response():
    state = State(
        _id="game-1",
        chat_history=[],
        story_summary="Iris crossed the causeway.",
        unresolved_threads=["open the sun gate"],
    )
    repository = FakeRepository({"game-1": state})
    llm_client = FakeLLMClient(narration="You continue on.")

    result = run_turn(GameService(repository, llm_client), "game-1", "Continue.")

    response = result.to_response()
    assert response["storySummary"] == "Iris crossed the causeway."
    assert response["unresolvedThreads"] == ["open the sun gate"]


def test_generate_starting_state_calls_structured_with_chargen_prompt():
    class ChargenFakeLLMClient(FakeLLMClient):
        async def async_structured(self, system, user, response_model, temperature: float = 0.0):
            self.structured_models.append(response_model)
            self.structured_prompts.append((system, user, response_model))
            from llm_results import StartingStateResult

            assert response_model is StartingStateResult
            return StartingStateResult(
                starting_location="a quiet harbor",
                age_years=30,
                height_cm=170.0,
                body_weight_kg=65.0,
                max_carry_weight_kg=25.0,
            )

    llm_client = ChargenFakeLLMClient()

    result = asyncio.run(
        GameService(FakeRepository(), llm_client).generate_starting_state(
            "Iris", "a city under the sea", "a cautious glassmaker"
        )
    )

    assert result.starting_location == "a quiet harbor"
    assert any("Iris" in prompt for _, prompt, _ in llm_client.structured_prompts)
