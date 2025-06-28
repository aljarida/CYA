from enum import Enum, auto

import requests
import base64

from bson.objectid import ObjectId

class ImageType(Enum):
    PORTRAIT = auto()
    BACKDROP = auto()

class Image:
    def __init__(self, bs: bytes, filename: str) -> None:
        self.filename: str = filename
        self.bytes: bytes = bs
    
    def json_content(self) -> str:
        """Encodes bytes for transfer to front-end in Base64."""
        return "data:image/png;base64," + base64.b64encode(self.bytes).decode("utf-8")


    @staticmethod
    def json_content_from_bytes(bs: bytes):
        return "data:image/png;base64," + base64.b64encode(bs).decode("utf-8")


    @staticmethod
    def bytes_from_url(url: str) -> bytes:
        is_wikipedia: bool = "wikipedia" in url
        if is_wikipedia:
            response: requests.Response = requests.get(url, headers={'User-Agent': '...'})
        else:
            response: requests.Response = requests.get(url)
        
        response.raise_for_status()
        bs: bytes | None = response.content
        assert(bs is not None)
        return bs

class Images:
    def __init__(self, _id: ObjectId, portrait_bytes: bytes, backdrop_bytes: bytes) -> None:
        self.portrait: Image = Image(portrait_bytes, self.name_for(_id, ImageType.PORTRAIT))
        self.backdrop: Image = Image(backdrop_bytes, self.name_for(_id, ImageType.BACKDROP))

    @staticmethod
    def name_for(_id: ObjectId, it: ImageType) -> str:
        match it:
            case ImageType.PORTRAIT:
                return f"{_id}_portrait"
            case ImageType.BACKDROP:
                return f"{_id}_backdrop"

