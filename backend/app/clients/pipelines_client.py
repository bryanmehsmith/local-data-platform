import requests

from app.config import settings


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
        import json

        if not text.lstrip().startswith("data:"):
            return json.loads(text)["choices"][0]["message"]["content"]

        parts = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                continue
            chunk = json.loads(payload)
            delta = chunk["choices"][0].get("delta", {})
            parts.append(delta.get("content", ""))
        return "".join(parts)


pipelines_client = PipelinesClient()
