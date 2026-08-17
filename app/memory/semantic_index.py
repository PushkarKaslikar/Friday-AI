"""FAISS vector index wrapper and abstraction.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import os
import threading
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class ISemanticMemoryIndex(ABC):
    """Abstract interface for local vector index."""

    @abstractmethod
    def add_vector(self, vector: list[float]) -> int:
        """Add a vector to the index and return its vector_id."""

    @abstractmethod
    def add_vectors(self, vectors: list[list[float]]) -> list[int]:
        """Add a batch of vectors to the index and return vector_ids."""

    @abstractmethod
    def search_vectors(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[tuple[int, float]]:
        """Search top_k nearest vectors and return list of (vector_id, similarity)."""

    @abstractmethod
    def tombstone_vector(self, vector_id: int) -> bool:
        """Mark a vector as tombstoned/deleted from active search."""

    @abstractmethod
    def save_index(self, file_path: str) -> bool:
        """Persist index to local disk file."""

    @abstractmethod
    def load_index(self, file_path: str) -> bool:
        """Load index from local disk file."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all vectors from the index."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension size."""

    @property
    @abstractmethod
    def vector_count(self) -> int:
        """Total number of active vectors in the index."""

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Check whether the vector index is initialized and ready."""


class FAISSMemoryIndex(ISemanticMemoryIndex):
    """Local FAISS vector index implementation.

    Uses FAISS IndexFlatIP (Inner Product) with L2-normalized vectors for exact
    cosine similarity calculations. Includes fallback vector engine if FAISS C++
    bindings are unavailable.
    """

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension
        self._lock = threading.Lock()
        self._faiss_index: Any = None
        self._vectors: dict[int, list[float]] = {}
        self._next_id = 0
        self._tombstones: set[int] = set()
        self._use_fallback = False
        self._is_ready = False
        self._initialize_index()

    def _initialize_index(self) -> None:
        try:
            import faiss

            self._faiss_index = faiss.IndexFlatIP(self._dimension)
            self._is_ready = True
            self._use_fallback = False
            logger.info(
                f"FAISSMemoryIndex: Initialized FAISS IndexFlatIP (dimension={self._dimension})."
            )
        except Exception as ex:  # noqa: BLE001
            logger.warning(
                f"FAISSMemoryIndex: FAISS initialization unavailable ({ex}). Using fallback vector engine."
            )
            self._faiss_index = None
            self._use_fallback = True
            self._is_ready = True

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def vector_count(self) -> int:
        with self._lock:
            return len(self._vectors) - len(self._tombstones)

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def add_vector(self, vector: list[float]) -> int:
        res = self.add_vectors([vector])
        return res[0]

    def add_vectors(self, vectors: list[list[float]]) -> list[int]:
        if not vectors:
            return []

        with self._lock:
            if len(vectors[0]) != self._dimension:
                raise ValueError(
                    f"Dimension mismatch: expected {self._dimension}, got {len(vectors[0])}"
                )

            assigned_ids = []
            for vec in vectors:
                vid = self._next_id
                self._next_id += 1
                self._vectors[vid] = vec
                assigned_ids.append(vid)

            if self._faiss_index is not None and not self._use_fallback:
                import numpy as np

                arr = np.array(vectors, dtype=np.float32)
                self._faiss_index.add(arr)

            return assigned_ids

    def search_vectors(
        self, query_vector: list[float], top_k: int = 10
    ) -> list[tuple[int, float]]:
        if not self._vectors or top_k <= 0:
            return []

        with self._lock:
            if len(query_vector) != self._dimension:
                raise ValueError(
                    f"Dimension mismatch: expected {self._dimension}, got {len(query_vector)}"
                )

            if (
                self._faiss_index is not None
                and not self._use_fallback
                and self._faiss_index.ntotal > 0
            ):
                import numpy as np

                arr = np.array([query_vector], dtype=np.float32)
                k_search = min(top_k + len(self._tombstones), self._faiss_index.ntotal)
                distances, indices = self._faiss_index.search(arr, k_search)

                results = []
                for idx, dist in zip(indices[0], distances[0]):
                    vid = int(idx)
                    if (
                        vid >= 0
                        and vid not in self._tombstones
                        and vid in self._vectors
                    ):
                        results.append((vid, float(dist)))
                        if len(results) >= top_k:
                            break
                return results

            # Fallback cosine similarity search
            scores = []
            for vid, vec in self._vectors.items():
                if vid in self._tombstones:
                    continue
                # Inner product for normalized vectors
                sim = sum(q * v for q, v in zip(query_vector, vec))
                scores.append((vid, sim))

            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:top_k]

    def tombstone_vector(self, vector_id: int) -> bool:
        with self._lock:
            if vector_id in self._vectors:
                self._tombstones.add(vector_id)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._vectors.clear()
            self._tombstones.clear()
            self._next_id = 0
            if self._faiss_index is not None:
                self._faiss_index.reset()

    def save_index(self, file_path: str) -> bool:
        if not file_path:
            return False

        with self._lock:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                if self._faiss_index is not None and not self._use_fallback:
                    import faiss

                    faiss.write_index(self._faiss_index, file_path)
                    logger.info(
                        f"FAISSMemoryIndex: Saved FAISS index to '{file_path}'."
                    )
                    return True

                # Fallback: Save text marker file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"FALLBACK_INDEX;dim={self._dimension};count={len(self._vectors)}\n"
                    )
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"FAISSMemoryIndex: Save failed ({ex}).")
                return False

    def load_index(self, file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False

        with self._lock:
            try:
                if self._faiss_index is not None and not self._use_fallback:
                    import faiss

                    loaded = faiss.read_index(file_path)
                    if loaded.d != self._dimension:
                        logger.error(
                            f"FAISSMemoryIndex: Loaded index dimension mismatch ({loaded.d} vs {self._dimension})."
                        )
                        return False

                    self._faiss_index = loaded
                    self._is_ready = True
                    logger.info(
                        f"FAISSMemoryIndex: Loaded FAISS index from '{file_path}' (ntotal={self._faiss_index.ntotal})."
                    )
                    return True
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"FAISSMemoryIndex: Load failed ({ex}).")
                return False
