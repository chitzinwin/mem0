"""
Patched MemoryClient for mem0 self-hosted OSS server.

The stock MemoryClient targets api.mem0.ai with /v1/ and /v3/ paths.
This module provides OSSMemoryClient that works with the OSS server's
path layout (no version prefix) and X-API-Key auth.
"""

import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OSSMemoryClient:
    """HTTP client for the mem0 self-hosted OSS REST API.

    Mimics the interface of mem0.client.main.MemoryClient but targets
    the OSS server which uses different paths and auth headers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        self.host = host or os.getenv("MEM0_API_URL", "http://localhost:8888")

        if not self.api_key:
            raise ValueError("MEM0_API_KEY not provided.")

        self.client = httpx.Client(
            base_url=self.host,
            headers={"X-API-Key": self.api_key},
            timeout=120,
        )
        logger.info(f"OSSMemoryClient initialized: {self.host}")

    def add(self, messages, *, user_id: Optional[str] = None, metadata: Optional[Dict] = None, infer: bool = True, **kwargs) -> Dict[str, Any]:
        """Add memories via POST /memories."""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        elif isinstance(messages, dict):
            messages = [messages]

        payload: Dict[str, Any] = {"messages": messages}
        if user_id:
            payload["user_id"] = user_id
        if metadata:
            payload["metadata"] = metadata
        if not infer:
            payload["infer"] = False

        response = self.client.post("/memories", json=payload)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, *, filters: Optional[Dict] = None, top_k: int = 10, **kwargs) -> Dict[str, Any]:
        """Search memories via POST /search."""
        payload: Dict[str, Any] = {"query": query}
        if filters:
            # OSS server accepts user_id at top level
            if "user_id" in filters:
                payload["user_id"] = filters["user_id"]
        if top_k != 10:
            payload["top_k"] = top_k

        response = self.client.post("/search", json=payload)
        response.raise_for_status()
        return response.json()

    def get_all(self, *, filters: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Get all memories via GET /memories."""
        params: Dict[str, Any] = {}
        if filters:
            if "user_id" in filters:
                params["user_id"] = filters["user_id"]

        response = self.client.get("/memories", params=params)
        response.raise_for_status()
        return response.json()

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory via GET /memories/{id}."""
        response = self.client.get(f"/memories/{memory_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def delete(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory via DELETE /memories/{id}."""
        response = self.client.delete(f"/memories/{memory_id}")
        response.raise_for_status()
        return response.json()

    def delete_all(self, *, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Delete all memories via DELETE /memories."""
        params: Dict[str, Any] = {}
        if user_id:
            params["user_id"] = user_id
        response = self.client.delete("/memories", params=params)
        response.raise_for_status()
        return response.json()
