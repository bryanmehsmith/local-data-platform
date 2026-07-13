import json
from collections.abc import Generator

import requests

from app.config import settings


def _parse_sse_line(line: str) -> str | None:
    """Parse a single SSE line from the pipelines sidecar.

    Returns the delta content fragment for a `data: {...}` line, or None if
    the line should be skipped (blank, not a data line, or the `[DONE]`
    sentinel).
    """
    line = line.strip()
    if not line.startswith("data:"):
        return None
    payload = line[len("data:") :].strip()
    if payload == "[DONE]":
        return None
    chunk = json.loads(payload)
    delta = chunk["choices"][0].get("delta", {})
    return delta.get("content", "")


class PipelinesClient:
    def chat(self, model: str, message: str, history: list[dict] | None = None) -> str:
        messages = (history or []) + [{"role": "user", "content": message}]
        resp = requests.post(
            f"{settings.pipelines_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.pipelines_api_key}"},
            json={"model": model, "messages": messages},
            timeout=120,
        )
        resp.raise_for_status()
        return self._parse_content(resp.text)

    def chat_stream(
        self, model: str, message: str, history: list[dict] | None = None
    ) -> Generator[str, None, None]:
        messages = (history or []) + [{"role": "user", "content": message}]
        resp = requests.post(
            f"{settings.pipelines_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.pipelines_api_key}"},
            json={"model": model, "messages": messages, "stream": True},
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            fragment = _parse_sse_line(line)
            if fragment:
                yield fragment

    def list_models(self) -> list[dict]:
        resp = requests.get(
            f"{settings.pipelines_url}/v1/models",
            headers={"Authorization": f"Bearer {settings.pipelines_api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["data"]

    @staticmethod
    def _parse_content(text: str) -> str:
        # The pipelines sidecar returns Server-Sent Events chunks even for a
        # single non-streamed reply (see evals/run_rag_eval.py for the same
        # parsing need).
        if not text.lstrip().startswith("data:"):
            return json.loads(text)["choices"][0]["message"]["content"]

        parts = []
        for line in text.splitlines():
            fragment = _parse_sse_line(line)
            if fragment:
                parts.append(fragment)
        return "".join(parts)


pipelines_client = PipelinesClient()
