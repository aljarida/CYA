import base64
from enum import Enum, auto
from pathlib import Path

import httpx
import requests

IMAGE_DOWNLOAD_TIMEOUT_SECONDS = 10.0
ASSET_DIR = Path(__file__).resolve().parent / "assets"

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
    def debug_portrait_bytes() -> bytes:
        return (ASSET_DIR / "dev_portrait.png").read_bytes()

    @staticmethod
    def debug_backdrop_bytes() -> bytes:
        return (ASSET_DIR / "dev_backdrop.png").read_bytes()


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


    @staticmethod
    async def async_bytes_from_url(url: str, timeout: float = IMAGE_DOWNLOAD_TIMEOUT_SECONDS) -> bytes:
        headers = {"User-Agent": "..."} if "wikipedia" in url else None
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)

        response.raise_for_status()
        return response.content

class Images:
    def __init__(self, _id: str, portrait_bytes: bytes, backdrop_bytes: bytes) -> None:
        self.portrait: Image = Image(portrait_bytes, self.name_for(_id, ImageType.PORTRAIT))
        self.backdrop: Image = Image(backdrop_bytes, self.name_for(_id, ImageType.BACKDROP))

    @staticmethod
    def name_for(_id: str, it: ImageType) -> str:
        match it:
            case ImageType.PORTRAIT:
                return f"{_id}_portrait"
            case ImageType.BACKDROP:
                return f"{_id}_backdrop"
