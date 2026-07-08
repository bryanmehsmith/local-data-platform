import os

import requests
from dagster import ConfigurableResource


class OllamaResource(ConfigurableResource):
    base_url: str = "http://ollama:11434"
    embed_model: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    def embed(self, text: str) -> list[float]:
        resp = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
