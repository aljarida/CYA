from typing import Any
from dotenv import load_dotenv
from datetime import datetime
import os

import gridfs
from pymongo import MongoClient
from bson.objectid import ObjectId

from classes import State, Images, ImageType

CLUSTER: str = "cya"
COLLECTION: str = "games"

class Database():
    def __init__(self):
        load_dotenv()
        key: str | None = os.getenv("MONGODB_CONNECTION_STRING")
        assert(key is not None)
        self._client: MongoClient = MongoClient(key)
        self._database  = self._client.get_database(CLUSTER)
        self._games = self._database.get_collection(COLLECTION)
        self._fs = gridfs.GridFS(self._database)

    def save_game(self, s: State) -> None:
        if s._id is not None:
            self._update_game_save(s)
        else:
            result = self._games.insert_one(State.serialize(s))
            assert(type(result.inserted_id) == ObjectId)
            s._id = result.inserted_id

    # TODO: Define following function.
    def save_game_and_images(self, s: State, images: Images) -> None:
        # TODO: Save the game.
        # TODO: Save the images.
        pass

    def _save_images(self, images: Images) -> None:
        existing = self._fs.find_one({
            '$or': [
                { 'filename': images.portrait.filename },
                { 'filename': images.landscape.filename },
            ],
        })
        assert(existing is not None)
        self._fs.put(images.portrait.bytes, filename=images.portrait.filename)
        self._fs.put(images.landscape.bytes, filename=images.landscape.filename)

    def get_images(self, _id: ObjectId) -> dict[ImageType, bytes]:
        """Given a state's unique ID, returns the relevant game images."""
        res: dict[ImageType, bytes] = {}
        images: list[tuple[str, ImageType]] = [
            (
                Images.name_for(_id, it),
                it,
            )
            for it in ImageType
        ]

        for img_name, img_type in images:
            file = self._fs.find_one({ 'filename': img_name })
            assert(file is not None)
            res[img_type] = file.read()

        return res

    def all_games(self) -> list[State]:
        games = self._games.find({})
        return [State.deserialize(g) for g in games]
    
    def get_game_data(self, _id: ObjectId) -> tuple[dict[str, Any] | None, bool]:
        game_data: dict[str, Any] | None = self._games.find_one({ "_id": _id })
        if game_data is None:
            return None, False
        return game_data, True

    def _update_game_save(self, s: State) -> None:
        assert(s._id is not None)

        current_save_state: dict[str, Any] = State.serialize(s)
        last_save_state, ok = self.get_game_data(s._id)
        assert(ok and last_save_state is not None and len(current_save_state) == len(last_save_state))

        variables_to_update: dict[str, Any]  = {}
        for cur in current_save_state.keys():
            assert(cur in last_save_state)
            if current_save_state[cur] != last_save_state[cur]:
                variables_to_update[cur] = current_save_state[cur]

        variables_to_update["updated_at"] = datetime.today()

        filter_: dict[str, ObjectId] = { "_id": s._id }
        update: dict[str, dict[str, Any]] = { "$set": variables_to_update }

        self._games.update_one(filter_, update)
