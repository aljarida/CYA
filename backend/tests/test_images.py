import pytest

from images import Image, Images, ImageType


def test_image_json_content_base64_encodes_bytes():
    image = Image(b"hello", "portrait")

    assert image.json_content() == "data:image/png;base64,aGVsbG8="
    assert Image.json_content_from_bytes(b"\x00\xff") == "data:image/png;base64,AP8="


def test_debug_placeholder_images_are_local_pngs():
    png_signature = b"\x89PNG\r\n\x1a\n"

    assert Image.debug_portrait_bytes().startswith(png_signature)
    assert Image.debug_backdrop_bytes().startswith(png_signature)


def test_images_use_stable_filenames_for_game_id():
    game_id = "saved-game"
    images = Images(game_id, b"portrait-bytes", b"backdrop-bytes")

    assert images.portrait.filename == f"{game_id}_portrait"
    assert images.backdrop.filename == f"{game_id}_backdrop"
    assert Images.name_for(game_id, ImageType.PORTRAIT) == f"{game_id}_portrait"
    assert Images.name_for(game_id, ImageType.BACKDROP) == f"{game_id}_backdrop"


def test_bytes_from_url_uses_user_agent_for_wikipedia(monkeypatch):
    calls = []

    class FakeResponse:
        content = b"wiki-bytes"

        def raise_for_status(self):
            calls.append(("raise_for_status",))

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("images.requests.get", fake_get)

    assert Image.bytes_from_url("https://en.wikipedia.org/example.png") == b"wiki-bytes"
    assert calls[0] == (
        "https://en.wikipedia.org/example.png",
        {"headers": {"User-Agent": "..."}},
    )
    assert calls[1] == ("raise_for_status",)


def test_bytes_from_url_raises_for_http_errors(monkeypatch):
    class FakeResponse:
        content = b""

        def raise_for_status(self):
            raise RuntimeError("bad status")

    monkeypatch.setattr("images.requests.get", lambda url: FakeResponse())

    with pytest.raises(RuntimeError, match="bad status"):
        Image.bytes_from_url("https://example.com/not-found.png")


def test_async_bytes_from_url_uses_timeout_and_user_agent_for_wikipedia(monkeypatch):
    calls = []

    class FakeResponse:
        content = b"async-wiki-bytes"

        def raise_for_status(self):
            calls.append(("raise_for_status",))

    class FakeClient:
        def __init__(self, timeout):
            calls.append(("timeout", timeout))

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def get(self, url, headers=None):
            calls.append((url, headers))
            return FakeResponse()

    monkeypatch.setattr("images.httpx.AsyncClient", FakeClient)

    import asyncio

    result = asyncio.run(Image.async_bytes_from_url("https://en.wikipedia.org/example.png", timeout=3.5))

    assert result == b"async-wiki-bytes"
    assert calls == [
        ("timeout", 3.5),
        ("https://en.wikipedia.org/example.png", {"User-Agent": "..."}),
        ("raise_for_status",),
    ]
