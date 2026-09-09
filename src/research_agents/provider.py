import json
import os
import urllib.request
from typing import Protocol


class TextProvider(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenAICompatibleProvider:
    """Minimal chat-completions client with no third-party dependency."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = os.environ["LLM_API_KEY"]
        self.model = os.environ.get("LLM_MODEL", "gpt-4.1-mini")

    def complete(self, system: str, user: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
        return body["choices"][0]["message"]["content"].strip()
