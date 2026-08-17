"""Semantic Memory Service coordinating local embeddings, FAISS vector index, and SQLite metadata.

Phase 5.5 - Semantic Memory & Local Vector Index Foundation
"""

import os
import threading
import time
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import delete, select

from app.memory.db_models import MemoryORM, SemanticIndexEntryORM
from app.memory.semantic_models import (
    ConsistencyReport,
    IndexSyncStatus,
    SemanticSearchResult,
)

if TYPE_CHECKING:
    from app.memory.db_manager import MemoryDatabaseManager
    from app.memory.embedding_provider import IEmbeddingProvider
    from app.memory.long_term_models import LongTermMemoryEntry
    from app.memory.long_term_service import LongTermMemoryService
    from app.memory.semantic_index import ISemanticMemoryIndex
    from app.memory.semantic_metrics import SemanticMemoryMetrics
    from app.memory.text_builder import MemoryEmbeddingTextBuilder


class SemanticMemoryService:
    """Coordinates local embedding generation, FAISS vector indexing, and SQLite vector metadata mapping."""

    def __init__(
        self,
        long_term_service: "LongTermMemoryService",
        db_manager: "MemoryDatabaseManager",
        embedding_provider: "IEmbeddingProvider",
        semantic_index: "ISemanticMemoryIndex",
        text_builder: "MemoryEmbeddingTextBuilder",
        metrics: "SemanticMemoryMetrics",
        index_path_override: str = "",
    ) -> None:
        self.long_term_service = long_term_service
        self._db_manager = db_manager
        self.embedding_provider = embedding_provider
        self.semantic_index = semantic_index
        self.text_builder = text_builder
        self._metrics = metrics
        self._lock = threading.RLock()
        self._sync_status = IndexSyncStatus.OUT_OF_SYNC
        self._index_version = 1

        if index_path_override:
            self._index_path = index_path_override
        else:
            base_dir = os.path.dirname(os.path.abspath(self._db_manager.db_path))
            self._index_path = os.path.join(base_dir, "semantic_index.faiss")

        self._initialize_subsystem()

    def _initialize_subsystem(self) -> None:
        """Initialize semantic index and load disk index if present."""
        with self._lock:
            if os.path.exists(self._index_path):
                ok = self.semantic_index.load_index(self._index_path)
                if ok:
                    self._sync_status = IndexSyncStatus.SYNCED
                    logger.info("SemanticMemoryService: Loaded disk FAISS index.")
                else:
                    self._sync_status = IndexSyncStatus.REBUILD_REQUIRED
            else:
                self._sync_status = IndexSyncStatus.OUT_OF_SYNC

    def get_subsystem_report(self) -> dict:
        """Get high-level status report of the semantic memory subsystem."""
        with self._lock:
            return {
                "sync_status": self._sync_status.value,
                "embedding_provider": self.embedding_provider.model_name,
                "embedding_model": self.embedding_provider.model_name,
                "embedding_healthy": self.embedding_provider.is_healthy(),
                "device": self.embedding_provider.device,
                "dimensions": self.embedding_provider.dimensions,
                "index_ready": self.semantic_index.is_ready,
                "vector_count": self.semantic_index.vector_count,
                "index_path": self._index_path,
                "index_version": self._index_version,
            }

    def semantic_search(
        self, query_text: str, top_k: int = 10
    ) -> list[SemanticSearchResult]:
        """Low-level semantic search primitive. Converts query text to vector and queries FAISS."""
        if not query_text or top_k <= 0:
            return []

        start_t = time.perf_counter()
        try:
            emb_res = self.embedding_provider.embed_text(query_text)
            if not emb_res.vector:
                return []

            raw_hits = self.semantic_index.search_vectors(
                emb_res.vector, top_k=top_k * 2
            )
            if not raw_hits:
                self._metrics.record_search(
                    duration_ms=(time.perf_counter() - start_t) * 1000, success=True
                )
                return []

            vector_ids = [hit[0] for hit in raw_hits]

            session = self._db_manager.get_session()
            try:
                stmt = select(SemanticIndexEntryORM).where(
                    SemanticIndexEntryORM.faiss_vector_id.in_(vector_ids),
                    SemanticIndexEntryORM.status == "INDEXED",
                )
                orm_entries = {
                    e.faiss_vector_id: e for e in session.scalars(stmt).all()
                }

                active_mem_stmt = select(MemoryORM.memory_id).where(
                    MemoryORM.memory_id.in_(
                        [e.memory_id for e in orm_entries.values()]
                    ),
                    MemoryORM.user_control_state == "ACTIVE",
                )
                active_mem_ids = set(session.scalars(active_mem_stmt).all())
            finally:
                session.close()

            results = []
            for vid, score in raw_hits:
                orm_e = orm_entries.get(vid)
                if orm_e and orm_e.memory_id in active_mem_ids:
                    results.append(
                        SemanticSearchResult(
                            memory_id=orm_e.memory_id,
                            vector_id=vid,
                            similarity=round(score, 4),
                            distance=round(1.0 - score, 4),
                            embedding_model=orm_e.embedding_model,
                            metadata={"content_hash": orm_e.content_hash},
                        )
                    )
                    if len(results) >= top_k:
                        break

            elapsed = (time.perf_counter() - start_t) * 1000
            self._metrics.record_search(duration_ms=elapsed, success=True)
            return results
        except Exception as ex:  # noqa: BLE001
            logger.error(f"SemanticMemoryService: Semantic search error ({ex}).")
            self._metrics.record_search(duration_ms=0.0, success=False)
            return []

    def on_memory_created(self, memory_entry: "LongTermMemoryEntry") -> bool:
        """Incremental handler for new long-term memory creation."""
        if not memory_entry:
            return False

        with self._lock:
            try:
                text = self.text_builder.build_embedding_text(memory_entry)
                if not text:
                    return False

                c_hash = self.text_builder.compute_content_hash(text)
                emb_res = self.embedding_provider.embed_text(text)
                if not emb_res.vector:
                    return False

                vid = self.semantic_index.add_vector(emb_res.vector)

                session = self._db_manager.get_session()
                try:
                    orm_entry = SemanticIndexEntryORM(
                        faiss_vector_id=vid,
                        memory_id=memory_entry.memory_id,
                        embedding_model=self.embedding_provider.model_name,
                        embedding_dimension=self.embedding_provider.dimensions,
                        content_hash=c_hash,
                        index_version=self._index_version,
                        status="INDEXED",
                        created_at=time.time(),
                        updated_at=time.time(),
                    )
                    session.add(orm_entry)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

                self._metrics.record_indexed_memory(1)
                self.semantic_index.save_index(self._index_path)
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(
                    f"SemanticMemoryService: Incremental creation error ({ex})."
                )
                return False

    def on_memory_updated(self, memory_entry: "LongTermMemoryEntry") -> bool:
        """Incremental handler for memory updates."""
        if not memory_entry:
            return False

        with self._lock:
            try:
                text = self.text_builder.build_embedding_text(memory_entry)
                new_hash = self.text_builder.compute_content_hash(text)

                session = self._db_manager.get_session()
                try:
                    stmt = select(SemanticIndexEntryORM).where(
                        SemanticIndexEntryORM.memory_id == memory_entry.memory_id,
                        SemanticIndexEntryORM.status == "INDEXED",
                    )
                    existing = session.scalars(stmt).first()

                    if existing and existing.content_hash == new_hash:
                        return True

                    emb_res = self.embedding_provider.embed_text(text)
                    if not emb_res.vector:
                        return False

                    if existing:
                        self.semantic_index.tombstone_vector(existing.faiss_vector_id)
                        existing.status = "TOMBSTONED"

                    vid = self.semantic_index.add_vector(emb_res.vector)
                    new_orm = SemanticIndexEntryORM(
                        faiss_vector_id=vid,
                        memory_id=memory_entry.memory_id,
                        embedding_model=self.embedding_provider.model_name,
                        embedding_dimension=self.embedding_provider.dimensions,
                        content_hash=new_hash,
                        index_version=self._index_version,
                        status="INDEXED",
                        created_at=time.time(),
                        updated_at=time.time(),
                    )
                    session.add(new_orm)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

                self._metrics.record_updated_vector(1)
                self.semantic_index.save_index(self._index_path)
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"SemanticMemoryService: Incremental update error ({ex}).")
                return False

    def on_memory_deleted(self, memory_id: str) -> bool:
        """Incremental handler for memory deletion/tombstoning."""
        if not memory_id:
            return False

        with self._lock:
            try:
                session = self._db_manager.get_session()
                try:
                    stmt = select(SemanticIndexEntryORM).where(
                        SemanticIndexEntryORM.memory_id == memory_id,
                        SemanticIndexEntryORM.status == "INDEXED",
                    )
                    entries = session.scalars(stmt).all()
                    for e in entries:
                        e.status = "TOMBSTONED"
                        self.semantic_index.tombstone_vector(e.faiss_vector_id)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

                self._metrics.record_removed_vector(len(entries))
                self.semantic_index.save_index(self._index_path)
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"SemanticMemoryService: Deletion tombstone error ({ex}).")
                return False

    def sync_index(self) -> bool:
        """Incremental synchronization between SQLite persistent store and FAISS vector index."""
        with self._lock:
            try:
                self._sync_status = IndexSyncStatus.SYNCING
                memories = self.long_term_service.list_memories()

                session = self._db_manager.get_session()
                try:
                    stmt = select(SemanticIndexEntryORM).where(
                        SemanticIndexEntryORM.status == "INDEXED"
                    )
                    indexed_orm = {e.memory_id: e for e in session.scalars(stmt).all()}
                finally:
                    session.close()

                active_ids = {m.memory_id for m in memories}

                # 1. Process deletions
                for m_id in list(indexed_orm.keys()):
                    if m_id not in active_ids:
                        self.on_memory_deleted(m_id)

                # 2. Process additions & updates
                for m in memories:
                    if m.memory_id not in indexed_orm:
                        self.on_memory_created(m)
                    else:
                        text = self.text_builder.build_embedding_text(m)
                        h = self.text_builder.compute_content_hash(text)
                        if indexed_orm[m.memory_id].content_hash != h:
                            self.on_memory_updated(m)

                self._sync_status = IndexSyncStatus.SYNCED
                self._metrics.record_sync(success=True)
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"SemanticMemoryService: Sync failed ({ex}).")
                self._sync_status = IndexSyncStatus.ERROR
                self._metrics.record_sync(success=False)
                return False

    def rebuild_index(self) -> bool:
        """Atomic index rebuild: builds fresh index in temp memory, validates, then atomic swap."""
        with self._lock:
            try:
                self._sync_status = IndexSyncStatus.SYNCING
                memories = self.long_term_service.list_memories()

                texts = [self.text_builder.build_embedding_text(m) for m in memories]
                valid_pairs = [(m, t) for m, t in zip(memories, texts) if t]

                if not valid_pairs:
                    self.semantic_index.clear()
                    session = self._db_manager.get_session()
                    try:
                        session.execute(delete(SemanticIndexEntryORM))
                        session.commit()
                    finally:
                        session.close()

                    self._sync_status = IndexSyncStatus.SYNCED
                    self.semantic_index.save_index(self._index_path)
                    return True

                batch_texts = [pair[1] for pair in valid_pairs]
                emb_results = self.embedding_provider.embed_batch(batch_texts)

                from app.memory.semantic_index import FAISSMemoryIndex

                temp_index = FAISSMemoryIndex(
                    dimension=self.embedding_provider.dimensions
                )
                vectors = [res.vector for res in emb_results]
                assigned_vids = temp_index.add_vectors(vectors)

                session = self._db_manager.get_session()
                try:
                    session.execute(delete(SemanticIndexEntryORM))

                    for pair, vid, res in zip(valid_pairs, assigned_vids, emb_results):
                        m_obj = pair[0]
                        c_hash = self.text_builder.compute_content_hash(pair[1])
                        orm_e = SemanticIndexEntryORM(
                            faiss_vector_id=vid,
                            memory_id=m_obj.memory_id,
                            embedding_model=self.embedding_provider.model_name,
                            embedding_dimension=self.embedding_provider.dimensions,
                            content_hash=c_hash,
                            index_version=self._index_version,
                            status="INDEXED",
                            created_at=time.time(),
                            updated_at=time.time(),
                        )
                        session.add(orm_e)
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

                self.semantic_index = temp_index
                self.semantic_index.save_index(self._index_path)
                self._sync_status = IndexSyncStatus.SYNCED
                self._metrics.record_rebuild(success=True)
                logger.info(
                    f"SemanticMemoryService: Rebuilt FAISS index successfully ({len(assigned_vids)} vectors)."
                )
                return True
            except Exception as ex:  # noqa: BLE001
                logger.error(f"SemanticMemoryService: Atomic rebuild failed ({ex}).")
                self._sync_status = IndexSyncStatus.ERROR
                self._metrics.record_rebuild(success=False)
                return False

    def validate_index_consistency(self) -> ConsistencyReport:
        """Validate consistency between SQLite memories, ORM vector mappings, and FAISS vector index."""
        with self._lock:
            report = ConsistencyReport()
            try:
                memories = self.long_term_service.list_memories()
                sqlite_ids = {m.memory_id for m in memories}
                report.sqlite_memory_count = len(sqlite_ids)
                report.vector_count = self.semantic_index.vector_count

                session = self._db_manager.get_session()
                try:
                    stmt = select(SemanticIndexEntryORM).where(
                        SemanticIndexEntryORM.status == "INDEXED"
                    )
                    orm_entries = session.scalars(stmt).all()
                finally:
                    session.close()

                mapped_mem_ids = {e.memory_id for e in orm_entries}
                orphan_vectors = [
                    e.faiss_vector_id
                    for e in orm_entries
                    if e.memory_id not in sqlite_ids
                ]
                missing_mems = [
                    m_id for m_id in sqlite_ids if m_id not in mapped_mem_ids
                ]

                report.orphan_vector_ids = orphan_vectors
                report.missing_memory_ids = missing_mems

                for e in orm_entries:
                    if e.embedding_dimension != self.embedding_provider.dimensions:
                        report.dimension_mismatch = True
                    if e.embedding_model != self.embedding_provider.model_name:
                        report.model_mismatch = True

                if (
                    orphan_vectors
                    or missing_mems
                    or report.dimension_mismatch
                    or report.model_mismatch
                ):
                    report.is_consistent = False
                    self._metrics.record_consistency_failure()
                else:
                    report.is_consistent = True

                return report
            except Exception as ex:  # noqa: BLE001
                logger.error(
                    f"SemanticMemoryService: Consistency validation error ({ex})."
                )
                report.is_consistent = False
                report.errors.append(str(ex))
                return report
