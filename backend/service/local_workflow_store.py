# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""In-memory store for locally generated workflow templates."""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class LocalWorkflowStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._workflows: Dict[int, Dict[str, Any]] = {}
        self._next_id = 100000

    def add(
        self,
        workflow_api: Dict[str, Any],
        name: str,
        description: str,
        source: str = "AI Generated",
    ) -> int:
        with self._lock:
            workflow_id = self._next_id
            self._next_id += 1
            self._workflows[workflow_id] = {
                "id": workflow_id,
                "name": name,
                "description": description,
                "source": source,
                "workflow_api": workflow_api,
                "image": None,
            }
            return workflow_id

    def get(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._workflows.get(workflow_id)

    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        q = (query or "").lower().strip()
        if not q:
            return []
        with self._lock:
            matches: List[Dict[str, Any]] = []
            for item in self._workflows.values():
                haystack = f"{item.get('name', '')} {item.get('description', '')}".lower()
                if any(token in haystack for token in q.split() if len(token) > 2):
                    matches.append(self._public_metadata(item))
            return matches[:limit]

    @staticmethod
    def _public_metadata(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item["id"],
            "name": item.get("name"),
            "description": item.get("description"),
            "image": item.get("image"),
            "source": item.get("source"),
        }

    def list_metadata(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._public_metadata(item) for item in self._workflows.values()]


workflow_store = LocalWorkflowStore()
