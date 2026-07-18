"""Model routing against a local llama.cpp OpenAI-compatible server."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib import error, request


class ModelError(RuntimeError):
    """Raised when the local model server returns an unusable response."""


@dataclass(slots=True)
class ModelRoute:
    name: str
    base_url: str = "http://127.0.0.1:8080"
    timeout_seconds: int = 120

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 900,
        extra_payload: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra_payload:
            payload.update(extra_payload)

        try:
            req = request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, json.JSONDecodeError) as exc:
            raise ModelError(
                f"Failed to reach llama.cpp model route '{self.name}' at {self.base_url}"
            ) from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError(
                f"Model route '{self.name}' returned an unexpected response shape"
            ) from exc
