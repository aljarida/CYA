from __future__ import annotations

import json
import os
import sqlite3
from abc import abstractmethod
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

import gridfs
from bson.objectid import ObjectId
from pymongo import MongoClient

from classes import State, StoryMoment
from images import Images, ImageType


class RevisionConflictError(RuntimeError):
    """Raised when saving a state whose revision is no longer current."""


class GameRepository(Protocol):
    @abstractmethod
    def save_game(self, state: State) -> None: ...

    @abstractmethod
    def save_game_and_images(self, state: State, images: Images) -> None: ...

    @abstractmethod
    def delete_game(self, game_id: str) -> bool: ...

    @abstractmethod
    def get_image_bytes(self, game_id: str) -> tuple[bytes, bytes] | None: ...

    @abstractmethod
    def all_games(self) -> list[State]: ...

    @abstractmethod
    def get_game(self, game_id: str) -> State | None: ...

    @abstractmethod
    def add_moment(self, game_id: str, caption: str, image_bytes: bytes) -> StoryMoment: ...

    @abstractmethod
    def list_moments(self, game_id: str) -> list[tuple[StoryMoment, bytes]]: ...


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__} to JSON")


class SQLiteGameRepository:
    """Local, zero-configuration game storage backed by one SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._configure()
        self._create_schema()

    def _configure(self) -> None:
        with self._connection:
            self._connection.execute("PRAGMA busy_timeout = 5000")
            self._connection.execute("PRAGMA foreign_keys = ON")
            if self.path != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    portrait BLOB,
                    backdrop BLOB
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS moments (
                    id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    image BLOB NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games (id)
                )
                """
            )

    @staticmethod
    def _encode_state(state: State) -> str:
        return json.dumps(state.serialize(), default=_json_default)

    @staticmethod
    def _decode_state(raw_state: str) -> State:
        return State.deserialize(json.loads(raw_state))

    def save_game(self, state: State) -> None:
        self._save_state(state)

    def save_game_and_images(self, state: State, images: Images) -> None:
        self._save_state(state, images)

    def _save_state(self, state: State, images: Images | None = None) -> None:
        if state._id is None:
            state._id = str(uuid4())
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO games (id, state_json, portrait, backdrop)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        state._id,
                        self._encode_state(state),
                        None if images is None else images.portrait.bytes,
                        None if images is None else images.backdrop.bytes,
                    ),
                )
            return

        expected_revision = state.revision
        updated_state = replace(
            state,
            revision=expected_revision + 1,
            updated_at=datetime.now(),
        )
        assignments = "state_json = ?"
        parameters: list[Any] = [self._encode_state(updated_state)]
        if images is not None:
            assignments += ", portrait = ?, backdrop = ?"
            parameters.extend([images.portrait.bytes, images.backdrop.bytes])
        parameters.extend([state._id, expected_revision])

        with self._lock, self._connection:
            result = self._connection.execute(
                f"""
                UPDATE games
                SET {assignments}
                WHERE id = ?
                  AND json_extract(state_json, '$.revision') = ?
                """,
                parameters,
            )
            if result.rowcount != 1:
                raise RevisionConflictError("Game state was modified by another save.")

        state.revision = updated_state.revision
        state.updated_at = updated_state.updated_at

    def delete_game(self, game_id: str) -> bool:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM moments WHERE game_id = ?", (game_id,))
            result = self._connection.execute("DELETE FROM games WHERE id = ?", (game_id,))
        return result.rowcount == 1

    def get_image_bytes(self, game_id: str) -> tuple[bytes, bytes] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT portrait, backdrop FROM games WHERE id = ?", (game_id,)
            ).fetchone()
        if row is None or row["portrait"] is None or row["backdrop"] is None:
            return None
        return bytes(row["portrait"]), bytes(row["backdrop"])

    def all_games(self) -> list[State]:
        with self._lock:
            rows = self._connection.execute("SELECT state_json FROM games").fetchall()
        return [self._decode_state(row["state_json"]) for row in rows]

    def get_game(self, game_id: str) -> State | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT state_json FROM games WHERE id = ?", (game_id,)
            ).fetchone()
        return None if row is None else self._decode_state(row["state_json"])

    def add_moment(self, game_id: str, caption: str, image_bytes: bytes) -> StoryMoment:
        moment = StoryMoment(game_id=game_id, caption=caption)
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO moments (id, game_id, caption, image) VALUES (?, ?, ?, ?)",
                (moment.id, moment.game_id, moment.caption, image_bytes),
            )
        return moment

    def list_moments(self, game_id: str) -> list[tuple[StoryMoment, bytes]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, game_id, caption, image FROM moments WHERE game_id = ? ORDER BY rowid ASC",
                (game_id,),
            ).fetchall()
        return [
            (StoryMoment(id=row["id"], game_id=row["game_id"], caption=row["caption"]), bytes(row["image"]))
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class MongoGameRepository:
    """MongoDB implementation retained for deployed or shared environments."""

    def __init__(self) -> None:
        missing = [
            name
            for name in ("MONGODB_CONNECTION_STRING", "CLUSTER", "COLLECTION")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(f"MongoDB storage requires: {', '.join(missing)}")

        self._client: MongoClient = MongoClient(os.environ["MONGODB_CONNECTION_STRING"])
        self._database = self._client.get_database(os.environ["CLUSTER"])
        self._games = self._database.get_collection(os.environ["COLLECTION"])
        self._moments = self._database.get_collection("moments")
        self._fs = gridfs.GridFS(self._database)

    @staticmethod
    def _object_id(game_id: str) -> ObjectId | None:
        try:
            return ObjectId(game_id)
        except Exception:
            return None

    @staticmethod
    def _mongo_document(state: State) -> dict[str, Any]:
        document = state.serialize()
        document.pop("_id", None)
        return document

    def save_game(self, state: State) -> None:
        if state._id is None:
            result = self._games.insert_one(self._mongo_document(state))
            state._id = str(result.inserted_id)
            return

        object_id = self._object_id(state._id)
        if object_id is None:
            raise ValueError("MongoDB game IDs must be valid ObjectIds")
        expected_revision = state.revision
        updated_at = datetime.now()
        updates = self._mongo_document(replace(state, updated_at=updated_at))
        updates.pop("revision", None)
        result = self._games.update_one(
            {"_id": object_id, "revision": expected_revision},
            {"$set": updates, "$inc": {"revision": 1}},
            upsert=False,
        )
        if result.modified_count != 1:
            raise RevisionConflictError("Game state was modified by another save.")
        state.revision = expected_revision + 1
        state.updated_at = updated_at

    def save_game_and_images(self, state: State, images: Images) -> None:
        self.save_game(state)
        self._save_images(images)

    def _save_images(self, images: Images) -> None:
        self._fs.put(images.portrait.bytes, filename=images.portrait.filename)
        self._fs.put(images.backdrop.bytes, filename=images.backdrop.filename)

    def delete_game(self, game_id: str) -> bool:
        object_id = self._object_id(game_id)
        if object_id is None:
            return False
        result = self._games.delete_one({"_id": object_id})
        if result.deleted_count != 1:
            return False
        self._delete_images(game_id)
        self._delete_moments(game_id)
        return True

    def _delete_images(self, game_id: str) -> None:
        for image_type in (ImageType.PORTRAIT, ImageType.BACKDROP):
            stored = self._fs.find_one({"filename": Images.name_for(game_id, image_type)})
            if stored is not None:
                self._fs.delete(stored._id)

    def _delete_moments(self, game_id: str) -> None:
        for document in self._moments.find({"game_id": game_id}):
            stored = self._fs.find_one({"filename": f"moment_{document['_id']}"})
            if stored is not None:
                self._fs.delete(stored._id)
        self._moments.delete_many({"game_id": game_id})

    def get_image_bytes(self, game_id: str) -> tuple[bytes, bytes] | None:
        files = [
            self._fs.find_one({"filename": Images.name_for(game_id, ImageType.PORTRAIT)}),
            self._fs.find_one({"filename": Images.name_for(game_id, ImageType.BACKDROP)}),
        ]
        if any(file is None for file in files):
            return None
        return files[0].read(), files[1].read()

    def all_games(self) -> list[State]:
        return [self._state_from_document(document) for document in self._games.find({})]

    def get_game(self, game_id: str) -> State | None:
        object_id = self._object_id(game_id)
        if object_id is None:
            return None
        document = self._games.find_one({"_id": object_id})
        return None if document is None else self._state_from_document(document)

    @staticmethod
    def _state_from_document(document: dict[str, Any]) -> State:
        data = dict(document)
        data["_id"] = str(data["_id"])
        return State.deserialize(data)

    def add_moment(self, game_id: str, caption: str, image_bytes: bytes) -> StoryMoment:
        moment = StoryMoment(game_id=game_id, caption=caption)
        self._moments.insert_one({"_id": moment.id, "game_id": game_id, "caption": caption})
        self._fs.put(image_bytes, filename=f"moment_{moment.id}")
        return moment

    def list_moments(self, game_id: str) -> list[tuple[StoryMoment, bytes]]:
        results: list[tuple[StoryMoment, bytes]] = []
        for document in self._moments.find({"game_id": game_id}):
            moment = StoryMoment(id=str(document["_id"]), game_id=game_id, caption=document.get("caption", ""))
            stored = self._fs.find_one({"filename": f"moment_{moment.id}"})
            if stored is None:
                continue
            results.append((moment, stored.read()))
        return results


def create_game_repository() -> GameRepository:
    backend = os.getenv("CYA_STORAGE_BACKEND", "sqlite").strip().lower()
    if backend == "sqlite":
        default_path = Path(__file__).resolve().parent / "data" / "cya.db"
        sqlite_path = os.getenv("CYA_SQLITE_PATH", str(default_path))
        print(f"Using SQLite game storage: {sqlite_path}")
        return SQLiteGameRepository(sqlite_path)
    if backend == "mongodb":
        print("Using MongoDB game storage.")
        return MongoGameRepository()
    raise RuntimeError("CYA_STORAGE_BACKEND must be either 'sqlite' or 'mongodb'")
