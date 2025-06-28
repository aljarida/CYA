from typing import Any
from datetime import datetime
import os

import gridfs
from pymongo import MongoClient
from bson.objectid import ObjectId

from classes import State
from images import Images, ImageType

class Database():
    def __init__(self):
        key: str = os.environ["MONGODB_CONNECTION_STRING"]
        assert(key is not None)
        self._client: MongoClient = MongoClient(key)
        self._database  = self._client.get_database(os.environ["CLUSTER"])
        self._games = self._database.get_collection(os.environ["COLLECTION"])
        self._fs = gridfs.GridFS(self._database)

    def save_game(self, s: State) -> None:
        if s._id is not None:
            self._update_game_save(s)
        else:
            result = self._games.insert_one(State.serialize(s))
            assert(type(result.inserted_id) == ObjectId)
            s._id = result.inserted_id

    def save_game_and_images(self, s: State, images: Images) -> None:
        self.save_game(s)
        self._save_images(images)
    
    def _save_images(self, images: Images) -> None:
        self._fs.put(images.portrait.bytes, filename=images.portrait.filename)
        self._fs.put(images.backdrop.bytes, filename=images.backdrop.filename)

    def delete_game(self, _id: ObjectId) -> None:
        def _delete_save() -> None:
            result = self._games.delete_many({ "_id": _id })
            assert(result.deleted_count == 1)

        _delete_save()
        self._delete_images(_id)

    def _delete_images(self, _id: ObjectId) -> None:
        def _image_id_of(filename: str) -> ObjectId:
            res = self._fs.find_one({ "filename": filename })
            assert(res is not None)
            return res._id

        def _delete_img(_image_id: ObjectId) -> None:
            self._fs.delete(_image_id)

        portrait_filename: str = Images.name_for(_id, ImageType.PORTRAIT)
        backdrop_filename: str = Images.name_for(_id, ImageType.BACKDROP)

        _delete_img(_image_id_of(portrait_filename))
        _delete_img(_image_id_of(backdrop_filename))

    def get_image_bytes(self, _id: ObjectId) -> tuple[bytes, bytes]:
        """Given a state's unique ID, returns the relevant game images."""
        image_filepaths: list[str] = [
            Images.name_for(_id, ImageType.PORTRAIT),
            Images.name_for(_id, ImageType.BACKDROP),
        ]

        def _get_bytes(filename: str) -> bytes:
            file = self._fs.find_one({ 'filename': filename })
            assert(file is not None)
            return file.read()

        portrait: bytes  = _get_bytes(image_filepaths[0])
        backdrop: bytes = _get_bytes(image_filepaths[1])

        return portrait, backdrop

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
