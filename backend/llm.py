import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, TypeVar

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, OpenAI, RateLimitError
from openai.types.chat import ChatCompletion

TextModel = "gpt-4.1"
ImageModel = "gpt-image-1"
DefaultTemperature = 0.0
DefaultTimeoutSeconds = 30.0
DefaultRetryLimit = 2
DefaultRetryBaseDelaySeconds = 0.25

StructuredResult = TypeVar("StructuredResult")
RetryResult = TypeVar("RetryResult")


class LLMError(RuntimeError):
    """Base class for user-safe LLM boundary failures."""


class LLMTransientError(LLMError):
    """Raised when retryable provider failures are exhausted."""


class LLMResponseError(LLMError):
    """Raised when the provider returns malformed or empty structured output."""


@dataclass(frozen=True)
class RetryConfig:
    retry_limit: int = DefaultRetryLimit
    base_delay_seconds: float = DefaultRetryBaseDelaySeconds


class LLMClient(Protocol):
    def text(self, system: str, user: str, temperature: float = DefaultTemperature) -> str: ...

    def structured(
        self,
        system: str,
        user: str,
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult: ...

    async def async_text(self, system: str, user: str, temperature: float = DefaultTemperature) -> str: ...

    async def async_structured(
        self,
        system: str,
        user: str,
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult: ...

    async def async_messages(self, messages: list[dict[str, str]], temperature: float = DefaultTemperature) -> str: ...

    async def async_structured_messages(
        self,
        messages: list[dict[str, str]],
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult: ...

    async def generate_image_bytes(self, prompt: str, size: str) -> bytes: ...


def _empty_str_if_none(reply: str | None) -> str:
    return reply if reply is not None else ""


def _parsed_or_raise(value: StructuredResult | None) -> StructuredResult:
    if value is None:
        raise LLMResponseError("Structured model response was empty.")
    return value


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _retry_delay(config: RetryConfig, attempt: int) -> float:
    if config.base_delay_seconds <= 0:
        return 0
    return config.base_delay_seconds * (2 ** attempt)


def _run_with_retries(
    operation: Callable[[], RetryResult],
    config: RetryConfig,
    retry_observer: Callable[[int], None] | None = None,
) -> RetryResult:
    last_exception: Exception | None = None
    retry_count = 0
    for attempt in range(config.retry_limit + 1):
        try:
            result = operation()
            if retry_observer is not None:
                retry_observer(retry_count)
            return result
        except Exception as exc:
            if not _is_retryable_exception(exc):
                raise
            last_exception = exc
            if attempt >= config.retry_limit:
                break
            retry_count += 1
            time.sleep(_retry_delay(config, attempt))
    if retry_observer is not None:
        retry_observer(retry_count)
    raise LLMTransientError("LLM request failed after retries.") from last_exception


async def _async_run_with_retries(
    operation: Callable[[], Awaitable[RetryResult]],
    config: RetryConfig,
    retry_observer: Callable[[int], None] | None = None,
) -> RetryResult:
    last_exception: Exception | None = None
    retry_count = 0
    for attempt in range(config.retry_limit + 1):
        try:
            result = await operation()
            if retry_observer is not None:
                retry_observer(retry_count)
            return result
        except Exception as exc:
            if not _is_retryable_exception(exc):
                raise
            last_exception = exc
            if attempt >= config.retry_limit:
                break
            retry_count += 1
            await asyncio.sleep(_retry_delay(config, attempt))
    if retry_observer is not None:
        retry_observer(retry_count)
    raise LLMTransientError("LLM request failed after retries.") from last_exception


def _token_usage_from_response(response: Any) -> dict[str, int] | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    token_usage: dict[str, int] = {}
    for response_name, trace_name in (
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = getattr(usage, response_name, None)
        if isinstance(value, int):
            token_usage[trace_name] = value
    return token_usage or None


class OpenAILLMClient:
    def __init__(
        self,
        api_key: str,
        text_model: str = TextModel,
        image_model: str = ImageModel,
        timeout_seconds: float = DefaultTimeoutSeconds,
        retry_limit: int = DefaultRetryLimit,
        retry_base_delay_seconds: float = DefaultRetryBaseDelaySeconds,
    ) -> None:
        self.text_model = text_model
        self.image_model = image_model
        self.retry_config = RetryConfig(
            retry_limit=retry_limit,
            base_delay_seconds=retry_base_delay_seconds,
        )
        self.last_retry_count: int | None = None
        self.last_token_usage: dict[str, int] | None = None
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self._async_client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)

    def _record_response_metadata(self, response: Any) -> None:
        self.last_token_usage = _token_usage_from_response(response)

    def text(self, system: str, user: str, temperature: float = DefaultTemperature) -> str:
        response: ChatCompletion = _run_with_retries(
            lambda: self._client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _empty_str_if_none(response.choices[0].message.content)

    def structured(
        self,
        system: str,
        user: str,
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult:
        response: ChatCompletion = _run_with_retries(
            lambda: self._client.beta.chat.completions.parse(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=response_model,
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _parsed_or_raise(response.choices[0].message.parsed)

    async def async_text(self, system: str, user: str, temperature: float = DefaultTemperature) -> str:
        response = await _async_run_with_retries(
            lambda: self._async_client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _empty_str_if_none(response.choices[0].message.content)

    async def async_structured(
        self,
        system: str,
        user: str,
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult:
        response = await _async_run_with_retries(
            lambda: self._async_client.beta.chat.completions.parse(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format=response_model,
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _parsed_or_raise(response.choices[0].message.parsed)

    async def async_messages(self, messages: list[dict[str, str]], temperature: float = DefaultTemperature) -> str:
        response = await _async_run_with_retries(
            lambda: self._async_client.chat.completions.create(
                model=self.text_model,
                messages=messages,
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _empty_str_if_none(response.choices[0].message.content)

    async def async_structured_messages(
        self,
        messages: list[dict[str, str]],
        response_model: type[StructuredResult],
        temperature: float = DefaultTemperature,
    ) -> StructuredResult:
        response = await _async_run_with_retries(
            lambda: self._async_client.beta.chat.completions.parse(
                model=self.text_model,
                messages=messages,
                response_format=response_model,
                temperature=temperature,
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        self._record_response_metadata(response)
        return _parsed_or_raise(response.choices[0].message.parsed)

    async def generate_image_bytes(self, prompt: str, size: str) -> bytes:
        import base64
        result = await _async_run_with_retries(
            lambda: self._async_client.images.generate(
                model=self.image_model,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json",
            ),
            self.retry_config,
            self._set_last_retry_count,
        )
        return base64.b64decode(result.data[0].b64_json)

    def _set_last_retry_count(self, retry_count: int) -> None:
        self.last_retry_count = retry_count
