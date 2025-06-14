from typing import Any
from dotenv import load_dotenv
from datetime import datetime
import os

from pymongo import MongoClient
from bson.objectid import ObjectId

from classes import State

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

    def save_game(self, s: State) -> None:
        if s._id is not None:
            self._update_game_save(s)
        else:
            result = self._games.insert_one(State.serialize(s))
            assert(type(result.inserted_id) == ObjectId)
            s._id = result.inserted_id

    def all_games(self) -> list[State]:
        games = self._games.find({})
        return [State.deserialize(g) for g in games]
    
    def _get_game_data(self, _id: ObjectId) -> tuple[dict[str, Any] | None, bool]:
        game_data: dict[str, Any] | None = self._games.find_one({ "_id": _id })
        if game_data is None:
            return None, False
        return game_data, True

    def _update_game_save(self, s: State) -> None:
        assert(s._id is not None)

        current_save_state: dict[str, Any] = State.serialize(s)
        last_save_state, ok = self._get_game_data(s._id)
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
