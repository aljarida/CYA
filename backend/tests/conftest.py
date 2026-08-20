import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("CYA_STORAGE_BACKEND", "sqlite")
os.environ.setdefault("CYA_SQLITE_PATH", ":memory:")
os.environ.setdefault("SKIP_IMAGE_GENERATION", "true")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--llm", action="store_true", default=False, help="Run tests that call the real LLM API")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--llm"):
        skip = pytest.mark.skip(reason="pass --llm to run LLM integration tests")
        for item in items:
            if "llm" in item.keywords:
                item.add_marker(skip)
