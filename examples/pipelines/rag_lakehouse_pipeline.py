"""
title: Lakehouse RAG (curated_events)
author: local-data-platform
description: Answers questions using facts embedded from iceberg.marts.curated_events in Qdrant.
requirements: qdrant-client, requests
"""

import os
from typing import Generator, Iterator, List, Union

import requests
from pydantic import BaseModel
from qdrant_client import QdrantClient


class Pipeline:
    class Valves(BaseModel):
        OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        OLLAMA_CHAT_MODEL: str = os.environ.get("OLLAMA_CHAT_MODEL", "llama3.2:3b")
        OLLAMA_EMBED_MODEL: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        QDRANT_URL: str = os.environ.get("QDRANT_URL", "http://qdrant:6333")
        QDRANT_COLLECTION: str = os.environ.get("QDRANT_COLLECTION", "curated_events")
        QDRANT_DOCS_COLLECTION: str = os.environ.get("QDRANT_DOCS_COLLECTION", "dbt_docs")
        TOP_K: int = int(os.environ.get("RAG_TOP_K", "5"))

    def __init__(self):
        # Deliberately no self.type here: the pipelines framework's model
        # listing (get_all_pipelines in its main.py) only special-cases
        # "manifold"/"filter" types and otherwise expects hasattr(pipeline,
        # "type") to be False for a plain pipe — setting "pipe" explicitly
        # makes the pipeline invisible in /models despite loading fine.
        self.id = "lakehouse_rag"
        self.name = "Lakehouse RAG (curated_events)"
        self.valves = self.Valves()
        self.qdrant: QdrantClient | None = None

    async def on_startup(self):
        self.qdrant = QdrantClient(url=self.valves.QDRANT_URL)

    async def on_shutdown(self):
        pass

    def _embed(self, text: str) -> list[float]:
        resp = requests.post(
            f"{self.valves.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": self.valves.OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def _retrieve_context(self, question: str) -> str:
        vector = self._embed(question)
        data_hits = self.qdrant.query_points(
            collection_name=self.valves.QDRANT_COLLECTION,
            query=vector,
            limit=self.valves.TOP_K,
        ).points

        doc_hits = []
        if self.qdrant.collection_exists(self.valves.QDRANT_DOCS_COLLECTION):
            doc_hits = self.qdrant.query_points(
                collection_name=self.valves.QDRANT_DOCS_COLLECTION,
                query=vector,
                limit=self.valves.TOP_K,
            ).points

        sections = []
        if data_hits:
            sections.append(
                "Data facts:\n"
                + "\n".join(f"- {h.payload['text']} (score={h.score:.3f})" for h in data_hits)
            )
        if doc_hits:
            sections.append(
                "Table documentation:\n"
                + "\n".join(f"- {h.payload['text']} (score={h.score:.3f})" for h in doc_hits)
            )
        return "\n\n".join(sections) if sections else "No matching data found in the lakehouse."

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        context_block = self._retrieve_context(user_message)
        augmented_prompt = (
            "You are a data analyst assistant. Answer the user's question using ONLY "
            "the information below, retrieved from the lakehouse's data facts and dbt "
            "table documentation. If it doesn't contain the answer, say so.\n\n"
            f"{context_block}\n\nQuestion: {user_message}"
        )
        chat_resp = requests.post(
            f"{self.valves.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": self.valves.OLLAMA_CHAT_MODEL,
                "messages": [{"role": "user", "content": augmented_prompt}],
                "stream": False,
            },
            timeout=120,
        )
        chat_resp.raise_for_status()
        return chat_resp.json()["message"]["content"]
