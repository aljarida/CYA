import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai import RateLimitError

from llm import (
    LLMResponseError,
    LLMTransientError,
    RetryConfig,
    _async_run_with_retries,
    _is_retryable_exception,
    _parsed_or_raise,
    _run_with_retries,
    _token_usage_from_response,
)


def rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.test/responses")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def test_retry_classification_includes_timeout_and_rate_limit_errors():
    assert _is_retryable_exception(TimeoutError("timed out")) is True
    assert _is_retryable_exception(httpx.TimeoutException("timed out")) is True
    assert _is_retryable_exception(rate_limit_error()) is True


def test_run_with_retries_returns_after_retryable_failure_then_success():
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("timed out")
        return "ok"

    observed_retry_counts = []

    result = _run_with_retries(
        operation,
        RetryConfig(retry_limit=2, base_delay_seconds=0),
        observed_retry_counts.append,
    )

    assert result == "ok"
    assert attempts == 2
    assert observed_retry_counts == [1]


def test_run_with_retries_exhausts_retryable_failures():
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise rate_limit_error()

    with pytest.raises(LLMTransientError):
        _run_with_retries(operation, RetryConfig(retry_limit=2, base_delay_seconds=0))

    assert attempts == 3


def test_run_with_retries_does_not_retry_validation_failures():
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise ValueError("bad schema")

    with pytest.raises(ValueError):
        _run_with_retries(operation, RetryConfig(retry_limit=2, base_delay_seconds=0))

    assert attempts == 1


def test_parsed_or_raise_maps_empty_structured_output_to_response_error():
    with pytest.raises(LLMResponseError):
        _parsed_or_raise(None)


def test_token_usage_from_response_extracts_available_counts():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=7,
            total_tokens=18,
        )
    )

    assert _token_usage_from_response(response) == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }


def test_async_run_with_retries_returns_after_retryable_failure_then_success():
    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("timed out")
        return "ok"

    result = asyncio.run(_async_run_with_retries(operation, RetryConfig(retry_limit=2, base_delay_seconds=0)))

    assert result == "ok"
    assert attempts == 2
