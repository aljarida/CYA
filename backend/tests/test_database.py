from datetime import datetime

import pytest

from classes import InventoryItem, PlayerAttributes, State, WorldState
from database import (
    MongoGameRepository,
    RevisionConflictError,
    SQLiteGameRepository,
    create_game_repository,
)
from images import Images


def test_sqlite_repository_round_trips_game_and_images():
    repository = SQLiteGameRepository(":memory:")
    state = State(player_name="Iris", chat_history=[{"role": "user", "content": "Go."}])

    repository.save_game(state)
    assert state._id is not None
    assert state.revision == 0
    images = Images(state._id, b"portrait", b"backdrop")
    repository.save_game_and_images(state, images)

    loaded = repository.get_game(state._id)
    assert loaded is not None
    assert loaded.revision == 1
    assert loaded.player_name == "Iris"
    assert loaded.chat_history == state.chat_history
    assert isinstance(loaded.created_at, datetime)
    assert repository.get_image_bytes(state._id) == (b"portrait", b"backdrop")
    assert repository.all_games() == [loaded]


def test_sqlite_repository_round_trips_inventory_and_player_attributes():
    repository = SQLiteGameRepository(":memory:")
    state = State(
        player_name="Iris",
        world_state=WorldState(inventory=[InventoryItem(name="torch", weight_kg=1.0, quantity=2)]),
        player_attributes=PlayerAttributes(age_years=28, height_cm=165.0, body_weight_kg=60.0),
    )

    repository.save_game(state)
    loaded = repository.get_game(state._id)

    assert loaded is not None
    assert loaded.world_state.inventory == state.world_state.inventory
    assert loaded.player_attributes == state.player_attributes


def test_sqlite_repository_updates_existing_game():
    repository = SQLiteGameRepository(":memory:")
    state = State(player_name="Iris")
    repository.save_game(state)

    state.hit_points = 3
    repository.save_game(state)

    loaded = repository.get_game(state._id)
    assert loaded is not None
    assert loaded.hit_points == 3
    assert loaded.revision == 1
    assert loaded.updated_at is not None


def test_sqlite_repository_rejects_stale_base_update():
    repository = SQLiteGameRepository(":memory:")
    state = State(player_name="Iris")
    repository.save_game(state)

    first_copy = repository.get_game(state._id)
    second_copy = repository.get_game(state._id)
    first_copy.hit_points = 3
    second_copy.hit_points = 1

    repository.save_game(first_copy)
    with pytest.raises(RevisionConflictError):
        repository.save_game(second_copy)

    loaded = repository.get_game(state._id)
    assert loaded.hit_points == 3
    assert loaded.revision == 1
    assert second_copy.revision == 0


def test_sqlite_repository_delete_removes_game_and_images():
    repository = SQLiteGameRepository(":memory:")
    state = State()
    repository.save_game(state)
    repository.save_game_and_images(state, Images(state._id, b"portrait", b"backdrop"))

    assert repository.delete_game(state._id) is True
    assert repository.get_game(state._id) is None
    assert repository.get_image_bytes(state._id) is None
    assert repository.delete_game(state._id) is False


def test_sqlite_repository_add_and_list_moments():
    repository = SQLiteGameRepository(":memory:")
    state = State()
    repository.save_game(state)

    first = repository.add_moment(state._id, "Iris drives back the tide-wraith.", b"image-bytes-1")
    second = repository.add_moment(state._id, "The lantern is lit at last.", b"image-bytes-2")

    moments = repository.list_moments(state._id)

    assert [moment.id for moment, _ in moments] == [first.id, second.id]
    assert [moment.caption for moment, _ in moments] == [
        "Iris drives back the tide-wraith.",
        "The lantern is lit at last.",
    ]
    assert [image_bytes for _, image_bytes in moments] == [b"image-bytes-1", b"image-bytes-2"]
    assert all(moment.game_id == state._id for moment, _ in moments)


def test_sqlite_repository_list_moments_empty_for_unknown_game():
    repository = SQLiteGameRepository(":memory:")

    assert repository.list_moments("no-such-game") == []


def test_sqlite_repository_delete_removes_moments():
    repository = SQLiteGameRepository(":memory:")
    state = State()
    repository.save_game(state)
    repository.add_moment(state._id, "A moment.", b"image-bytes")

    assert repository.delete_game(state._id) is True
    assert repository.list_moments(state._id) == []


def test_sqlite_repository_persists_after_reopening(tmp_path):
    path = tmp_path / "cya.db"
    first = SQLiteGameRepository(path)
    state = State(player_name="Morgan")
    first.save_game(state)
    game_id = state._id
    first.close()

    second = SQLiteGameRepository(path)
    assert second.get_game(game_id).player_name == "Morgan"
    second.close()


def test_repository_factory_defaults_to_sqlite(monkeypatch, tmp_path):
    monkeypatch.delenv("CYA_STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("CYA_SQLITE_PATH", str(tmp_path / "default.db"))

    repository = create_game_repository()

    assert isinstance(repository, SQLiteGameRepository)
    repository.close()


def test_repository_factory_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("CYA_STORAGE_BACKEND", "unknown")

    with pytest.raises(RuntimeError, match="sqlite.*mongodb"):
        create_game_repository()


def test_mongodb_repository_reports_missing_configuration(monkeypatch):
    for name in ("MONGODB_CONNECTION_STRING", "CLUSTER", "COLLECTION"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="MONGODB_CONNECTION_STRING.*CLUSTER.*COLLECTION"):
        MongoGameRepository()
