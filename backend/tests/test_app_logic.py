import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi.responses import JSONResponse

import app
from classes import Sender, State
from game_service import TurnResult
from images import Image
from llm_results import BooleanDecision, DamageDecision


def test_empty_str_if_none_normalizes_none_only():
    assert app.empty_str_if_none(None) == ""
    assert app.empty_str_if_none("") == ""
    assert app.empty_str_if_none("reply") == "reply"


def test_update_chat_history_appends_assistant_reply_when_present():
    state = State(chat_history=[{"role": "system", "content": "setup"}])

    app.update_chat_history(state, "Look around.", "You see a road.")

    assert state.chat_history == [
        {"role": "system", "content": "setup"},
        {"role": "user", "content": "Look around."},
        {"role": "assistant", "content": "You see a road."},
    ]


def test_update_chat_history_skips_missing_assistant_reply():
    state = State(chat_history=[])

    app.update_chat_history(state, "Wait.", None)

    assert state.chat_history == [{"role": "user", "content": "Wait."}]


@pytest.mark.parametrize("decision", [True, False])
def test_async_is_relevant_uses_structured_decision(monkeypatch, decision):
    async def fake_structured_response_with_sys_user(system_prompt, user_prompt, response_model):
        assert response_model is BooleanDecision
        return BooleanDecision(value=decision, reason="checked")

    monkeypatch.setattr(app, "async_structured_response_with_sys_user", fake_structured_response_with_sys_user)

    assert asyncio.run(app.async_is_relevant(State(), "Go north.")) is decision


@pytest.mark.parametrize("decision", [True, False])
def test_async_is_realistic_uses_structured_decision(monkeypatch, decision):
    async def fake_structured_response_with_sys_user(system_prompt, user_prompt, response_model):
        assert response_model is BooleanDecision
        return BooleanDecision(value=decision, reason="checked")

    monkeypatch.setattr(app, "async_structured_response_with_sys_user", fake_structured_response_with_sys_user)

    assert asyncio.run(app.async_is_realistic(State(), "Fly unaided.")) is decision


@pytest.mark.parametrize("expected_damage", [0, 1, 2, 3, 4, 5])
def test_assess_damage_uses_structured_damage(monkeypatch, expected_damage):
    def fake_structured_response_with_sys_user(system_prompt, user_prompt, response_model):
        assert response_model is DamageDecision
        return DamageDecision(damage=expected_damage, reason="checked")

    monkeypatch.setattr(app, "structured_response_with_sys_user", fake_structured_response_with_sys_user)

    assert app.assess_damage(State(), "Attack.", "The attack lands.") == expected_damage


@pytest.mark.parametrize(
    ("relevant", "realistic", "expected_content"),
    [
        (False, False, "Your message is not relevant or realistic."),
        (False, True, "Your message is not relevant to the game story."),
        (True, False, "Your message does not respect the realism of the game story."),
    ],
)
def test_validate_and_get_gamemaster_reply_rejects_invalid_messages(
    monkeypatch,
    relevant,
    realistic,
    expected_content,
):
    async def fake_is_relevant(state, user_message):
        return relevant

    async def fake_is_realistic(state, user_message):
        return realistic

    monkeypatch.setattr(app, "async_is_relevant", fake_is_relevant)
    monkeypatch.setattr(app, "async_is_realistic", fake_is_realistic)

    result = asyncio.run(app.validate_and_get_gamemaster_reply(State(), "I do impossible things."))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert expected_content.encode() in result.body


def test_validate_and_get_gamemaster_reply_returns_reply_when_valid(monkeypatch):
    async def fake_is_relevant(state, user_message):
        return True

    async def fake_is_realistic(state, user_message):
        return True

    async def fake_get_gamemaster_reply(state, user_message):
        return "A careful answer."

    monkeypatch.setattr(app, "async_is_relevant", fake_is_relevant)
    monkeypatch.setattr(app, "async_is_realistic", fake_is_realistic)
    monkeypatch.setattr(app, "async_get_gamemaster_reply", fake_get_gamemaster_reply)

    assert asyncio.run(app.validate_and_get_gamemaster_reply(State(), "Proceed.")) == "A careful answer."


def test_response_requires_game_id():
    result = asyncio.run(app.response(app.ResponseRequest(content="Hello")))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Game ID is required" in result.body


def test_response_rejects_blank_game_id():
    result = asyncio.run(app.response(app.ResponseRequest(content="Hello", gameId="  ")))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Game ID is required" in result.body


def test_response_rejects_long_message(monkeypatch):
    monkeypatch.setattr(app, "load_state_from_db", lambda game_id: State(_id=game_id))

    result = asyncio.run(
        app.response(app.ResponseRequest(content="x" * (app.MAX_MESSAGE_LENGTH + 1), gameId="active-game"))
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Message must be" in result.body


def test_response_rejects_unknown_game(monkeypatch):
    monkeypatch.setattr(app, "load_state_from_db", lambda game_id: None)

    result = asyncio.run(app.response(app.ResponseRequest(content="Hello", gameId="unknown-game")))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Invalid game ID" in result.body


def test_response_does_not_mutate_game_over_state(monkeypatch):
    class FakeService:
        async def play_turn(self, game_id, content):
            return TurnResult(
                sender=Sender.SYSTEM,
                content="You are dead. Please refresh the browser to play again.",
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = asyncio.run(app.response(app.ResponseRequest(content="Hello", gameId="finished-game")))

    assert result == {
        "sender": str(Sender.SYSTEM),
        "content": "You are dead. Please refresh the browser to play again.",
    }


def test_response_returns_successful_turn_result(monkeypatch):
    calls = []

    class FakeService:
        async def play_turn(self, game_id, content):
            calls.append((game_id, content))
            return TurnResult(
                sender=Sender.GAMEMASTER,
                content="A bridge appears.",
                hit_points=3,
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = asyncio.run(app.response(app.ResponseRequest(content="Look around.", gameId="active-game")))

    assert result == {
        "sender": str(Sender.GAMEMASTER),
        "content": "A bridge appears.",
        "hitPoints": 3,
    }
    assert calls == [("active-game", "Look around.")]


def test_response_allows_override_as_testing_mechanism(monkeypatch):
    calls = []

    class FakeService:
        async def play_turn(self, game_id, content):
            calls.append((game_id, content))
            return TurnResult(
                sender=Sender.GAMEMASTER,
                content="Debug reply.",
                hit_points=5,
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = asyncio.run(app.response(app.ResponseRequest(content="@override steal the crown", gameId="active-game")))

    assert result["content"] == "Debug reply."
    assert calls == [("active-game", "@override steal the crown")]


def test_response_returns_game_over_turn_result(monkeypatch):
    class FakeService:
        async def play_turn(self, game_id, content):
            return TurnResult(
                sender=Sender.SYSTEM,
                content="Oh, no! Unfortunately, you have died!",
                game_over_summary="Morgan fell in the ravine.",
                hit_points=0,
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = asyncio.run(app.response(app.ResponseRequest(content="Step forward.", gameId="active-game")))

    assert result == {
        "sender": str(Sender.SYSTEM),
        "content": "Oh, no! Unfortunately, you have died!",
        "gameOverSummary": "Morgan fell in the ravine.",
        "hitPoints": 0,
    }


def test_get_suggested_responses_rejects_blank_game_id():
    result = asyncio.run(app.get_suggested_responses(gameId=" ", n=3))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Invalid game ID" in result.body


@pytest.mark.parametrize("suggestion_count", [0, app.MAX_SUGGESTED_RESPONSES + 1])
def test_get_suggested_responses_bounds_count(suggestion_count):
    result = asyncio.run(app.get_suggested_responses(gameId="active-game", n=suggestion_count))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Suggestion count must be" in result.body


def test_get_suggested_responses_handles_empty_history(monkeypatch):
    monkeypatch.setattr(app, "load_state_from_db", lambda game_id: State(_id=game_id, chat_history=[]))

    result = asyncio.run(app.get_suggested_responses(gameId="active-game", n=3))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"No gamemaster response found" in result.body


def test_initialize_rejects_long_setup_fields():
    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(
                playerName="x" * (app.MAX_SETUP_FIELD_LENGTH + 1),
                playerDescription="careful scout",
                worldTheme="salt flats",
            )
        )
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Player name must be" in result.body


def test_initialize_reports_image_download_failure(monkeypatch):
    async def fail_get_new_images_for(state):
        raise httpx.ConnectError("could not download generated image")

    monkeypatch.setattr(app, "get_new_images_for", fail_get_new_images_for)

    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(
                playerName="Morgan",
                playerDescription="a scout",
                worldTheme="misty ruins",
            )
        )
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 502
    assert b"image download" in result.body
    assert b"could not download generated image" in result.body


def test_initialize_reports_storage_failure(monkeypatch):
    async def fake_get_new_images_for(state):
        state._id = "new-game"
        return SimpleNamespace(
            portrait=SimpleNamespace(json_content=lambda: "portrait-data"),
            backdrop=SimpleNamespace(json_content=lambda: "backdrop-data"),
        )

    def fail_save_game_and_images(state, images):
        raise RuntimeError("sqlite file is not writable")

    monkeypatch.setattr(app, "get_new_images_for", fake_get_new_images_for)
    monkeypatch.setattr(app, "db", SimpleNamespace(save_game_and_images=fail_save_game_and_images))

    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(
                playerName="Morgan",
                playerDescription="a scout",
                worldTheme="misty ruins",
            )
        )
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 502
    assert b"local storage" in result.body
    assert b"sqlite file is not writable" in result.body


@pytest.mark.parametrize("request_cls, handler, message", [
    (app.DeleteGameRequest, app.delete_game, b"delete a game"),
    (app.LoadGameRequest, app.load_game, b"load a game"),
])
def test_game_id_endpoints_reject_blank_ids(request_cls, handler, message):
    result = handler(request_cls(objectIDString=" "))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert message in result.body


def test_delete_game_rejects_unknown_game(monkeypatch):
    monkeypatch.setattr(app, "db", SimpleNamespace(delete_game=lambda game_id: False))

    result = app.delete_game(app.DeleteGameRequest(objectIDString="unknown-game"))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"unknown-game" in result.body


def test_delete_game_accepts_storage_neutral_id(monkeypatch):
    deleted_ids = []
    monkeypatch.setattr(
        app,
        "db",
        SimpleNamespace(delete_game=lambda game_id: deleted_ids.append(game_id) or True),
    )

    result = app.delete_game(app.DeleteGameRequest(objectIDString="local-uuid"))

    assert result["sender"] == str(Sender.SYSTEM)
    assert deleted_ids == ["local-uuid"]


def test_initialize_awaits_async_image_generation(monkeypatch):
    saved = []
    images = SimpleNamespace(
        portrait=SimpleNamespace(json_content=lambda: "portrait-data"),
        backdrop=SimpleNamespace(json_content=lambda: "backdrop-data"),
    )

    async def fake_get_new_images_for(state):
        state._id = "new-game"
        return images

    monkeypatch.setattr(app, "get_new_images_for", fake_get_new_images_for)
    monkeypatch.setattr(app, "db", SimpleNamespace(save_game_and_images=lambda state, images: saved.append((state, images))))

    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(
                playerName="Morgan",
                playerDescription="a scout",
                worldTheme="misty ruins",
            )
        )
    )

    assert result["gameId"] == "new-game"
    assert result["portraitSrc"] == "portrait-data"
    assert result["worldBackdropSrc"] == "backdrop-data"
    assert saved[0][1] is images
    assert saved[0][0].player_name == "Morgan"


def test_get_new_images_for_debug_mode_uses_embedded_placeholders(monkeypatch):
    saved_states = []
    state = State()

    async def fail_generate_image_bytes(prompt, resolution):
        raise AssertionError("debug mode should not call image generation")

    monkeypatch.setenv("SKIP_IMAGE_GENERATION", "true")
    monkeypatch.setattr(app.llm_client, "generate_image_bytes", fail_generate_image_bytes)
    monkeypatch.setattr(app, "db", SimpleNamespace(save_game=lambda state: setattr(state, "_id", "debug-game") or saved_states.append(state)))

    images = asyncio.run(app.get_new_images_for(state))

    assert saved_states == [state]
    assert images.portrait.bytes == Image.debug_portrait_bytes()
    assert images.backdrop.bytes == Image.debug_backdrop_bytes()


def test_discard_item_endpoint_requires_game_and_item_id():
    result = app.discard_item(app.DiscardItemRequest())

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400


def test_discard_item_endpoint_returns_successful_result(monkeypatch):
    calls = []

    class FakeService:
        def discard_item(self, game_id, item_id):
            calls.append((game_id, item_id))
            return TurnResult(
                sender=Sender.SYSTEM,
                content="You discard the brass key.",
                world_state={"inventory": []},
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = app.discard_item(app.DiscardItemRequest(gameId="active-game", itemId="item-1"))

    assert result == {
        "sender": str(Sender.SYSTEM),
        "content": "You discard the brass key.",
        "worldState": {"inventory": []},
    }
    assert calls == [("active-game", "item-1")]


def test_discard_item_endpoint_propagates_service_error(monkeypatch):
    class FakeService:
        def discard_item(self, game_id, item_id):
            return TurnResult(sender=Sender.ERROR, content="Item not found in inventory.", status_code=400)

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = app.discard_item(app.DiscardItemRequest(gameId="active-game", itemId="missing"))

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400
    assert b"Item not found in inventory." in result.body


def test_generate_starting_state_rejects_overlong_fields():
    result = asyncio.run(
        app.generate_starting_state(
            app.GenerateStartingStateRequest(
                playerName="x" * (app.MAX_SETUP_FIELD_LENGTH + 1),
                playerDescription="careful scout",
                worldTheme="salt flats",
            )
        )
    )

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400


def test_generate_starting_state_endpoint_returns_camel_case_payload(monkeypatch):
    from llm_results import StartingInventoryItem, StartingStateResult

    class FakeService:
        async def generate_starting_state(self, player_name, world_theme, player_description):
            return StartingStateResult(
                starting_location="a quiet harbor",
                starting_inventory=[StartingInventoryItem(name="torch", weight_kg=1.0, quantity=1)],
                starting_conditions=[],
                age_years=30,
                height_cm=170.0,
                body_weight_kg=65.0,
                max_carry_weight_kg=25.0,
            )

    monkeypatch.setattr(app, "create_game_service", lambda: FakeService())

    result = asyncio.run(
        app.generate_starting_state(
            app.GenerateStartingStateRequest(
                playerName="Morgan", playerDescription="a scout", worldTheme="misty ruins"
            )
        )
    )

    assert result["startingLocation"] == "a quiet harbor"
    assert result["startingInventory"] == [
        {"name": "torch", "description": "", "weightKg": 1.0, "quantity": 1}
    ]
    assert result["attributes"] == {
        "ageYears": 30,
        "heightCm": 170.0,
        "bodyWeightKg": 65.0,
        "maxCarryWeightKg": 25.0,
    }


def test_initialize_without_confirmed_fields_uses_defaults(monkeypatch):
    async def fake_get_new_images_for(state):
        state._id = "new-game"
        return SimpleNamespace(
            portrait=SimpleNamespace(json_content=lambda: "portrait-data"),
            backdrop=SimpleNamespace(json_content=lambda: "backdrop-data"),
        )

    monkeypatch.setattr(app, "get_new_images_for", fake_get_new_images_for)
    monkeypatch.setattr(app, "db", SimpleNamespace(save_game_and_images=lambda state, images: None))

    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(playerName="Morgan", playerDescription="a scout", worldTheme="misty ruins")
        )
    )

    assert result["worldState"]["inventory"] == []
    assert result["storySummary"] == ""
    assert result["unresolvedThreads"] == []


def test_initialize_with_confirmed_starting_inventory_persists_structured_items(monkeypatch):
    saved_states = []

    async def fake_get_new_images_for(state):
        state._id = "new-game"
        return SimpleNamespace(
            portrait=SimpleNamespace(json_content=lambda: "portrait-data"),
            backdrop=SimpleNamespace(json_content=lambda: "backdrop-data"),
        )

    monkeypatch.setattr(app, "get_new_images_for", fake_get_new_images_for)
    monkeypatch.setattr(
        app,
        "db",
        SimpleNamespace(save_game_and_images=lambda state, images: saved_states.append(state)),
    )

    result = asyncio.run(
        app.initialize(
            app.InitializeRequest(
                playerName="Morgan",
                playerDescription="a scout",
                worldTheme="misty ruins",
                startingLocation="a quiet harbor",
                startingInventory=[app.DraftInventoryItemDTO(name="torch", weightKg=1.0, quantity=1)],
                startingConditions=["hungry"],
                attributes=app.DraftAttributesDTO(
                    ageYears=30, heightCm=170.0, bodyWeightKg=65.0, maxCarryWeightKg=25.0
                ),
            )
        )
    )

    assert result["worldState"]["currentLocation"] == "a quiet harbor"
    assert result["worldState"]["inventory"][0]["name"] == "torch"
    assert result["worldState"]["conditions"] == ["hungry"]
    persisted_item = saved_states[0].world_state.inventory[0]
    assert persisted_item.id
    assert saved_states[0].player_attributes.age_years == 30


def test_load_game_returns_story_summary_and_unresolved_threads(monkeypatch):
    state = State(
        _id="game-1",
        story_summary="Iris crossed the causeway.",
        unresolved_threads=["open the sun gate"],
    )
    monkeypatch.setattr(
        app,
        "db",
        SimpleNamespace(
            get_game=lambda game_id: state,
            get_image_bytes=lambda game_id: (b"portrait", b"backdrop"),
        ),
    )

    result = app.load_game(app.LoadGameRequest(objectIDString="game-1"))

    assert result["storySummary"] == "Iris crossed the causeway."
    assert result["unresolvedThreads"] == ["open the sun gate"]


def test_moments_endpoint_requires_game_id():
    result = app.moments(gameId=" ")

    assert isinstance(result, JSONResponse)
    assert result.status_code == 400


def test_moments_endpoint_returns_camel_case_results(monkeypatch):
    from classes import StoryMoment

    moment = StoryMoment(id="moment-1", game_id="game-1", caption="Iris drives back the tide-wraith.")
    monkeypatch.setattr(
        app,
        "db",
        SimpleNamespace(list_moments=lambda game_id: [(moment, b"image-bytes")] if game_id == "game-1" else []),
    )

    result = app.moments(gameId="game-1")

    assert result == {
        "results": [
            {
                "id": "moment-1",
                "caption": "Iris drives back the tide-wraith.",
                "imageSrc": Image.json_content_from_bytes(b"image-bytes"),
            }
        ]
    }


def test_moments_endpoint_returns_empty_results_for_game_with_no_moments(monkeypatch):
    monkeypatch.setattr(app, "db", SimpleNamespace(list_moments=lambda game_id: []))

    result = app.moments(gameId="game-1")

    assert result == {"results": []}
