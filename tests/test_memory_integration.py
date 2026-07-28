"""
Tests: Memory Integration

Integration tests verifying:
  1. DeterministicEmbeddingProvider produces stable, unit-norm vectors.
  2. DefaultKnowledgeRepository correctly tags records with collection labels.
  3. DI wiring produces a properly configured MemoryService.
  4. SupervisorOrchestrator (with MemoryService) persists execution and reflection
     records without disrupting the execution result.
"""

import math

import pytest

from core.ai.embeddings.deterministic import DeterministicEmbeddingProvider
from core.memory.providers.in_memory import InMemoryProvider
from core.memory.repository import (
    COLLECTION_EXECUTIONS,
    COLLECTION_REFLECTIONS,
    DefaultKnowledgeRepository,
)
from core.memory.service import MemoryService
from core.models.memory import MemoryQuery

# =========================================================================
# DeterministicEmbeddingProvider
# =========================================================================


class TestDeterministicEmbeddingProvider:
    def setup_method(self) -> None:
        self.provider = DeterministicEmbeddingProvider()

    def test_output_dimension(self) -> None:
        vec = self.provider.embed_text("hello world")
        assert len(vec) == 128

    def test_deterministic_same_input(self) -> None:
        v1 = self.provider.embed_text("AgentOS reflection")
        v2 = self.provider.embed_text("AgentOS reflection")
        assert v1 == v2

    def test_different_inputs_different_vectors(self) -> None:
        v1 = self.provider.embed_text("python programming")
        v2 = self.provider.embed_text("finance report")
        assert v1 != v2

    def test_unit_norm(self) -> None:
        vec = self.provider.embed_text("test content for norm check")
        magnitude = math.sqrt(sum(v * v for v in vec))
        assert math.isclose(magnitude, 1.0, abs_tol=1e-6)

    def test_empty_text_does_not_crash(self) -> None:
        vec = self.provider.embed_text("")
        assert len(vec) == 128

    def test_embed_batch(self) -> None:
        texts = ["first sentence", "second sentence", "third sentence"]
        vecs = self.provider.embed_batch(texts)
        assert len(vecs) == 3
        for vec in vecs:
            assert len(vec) == 128


# =========================================================================
# DefaultKnowledgeRepository
# =========================================================================


class TestDefaultKnowledgeRepository:
    def setup_method(self) -> None:
        self.provider = InMemoryProvider()
        self.repo = DefaultKnowledgeRepository(provider=self.provider)
        self.embedder = DeterministicEmbeddingProvider()

    def _svc(self) -> MemoryService:
        return MemoryService(repository=self.repo, embedding_provider=self.embedder)

    def test_add_tags_collection(self) -> None:
        svc = self._svc()
        record = svc.store_reflection(goal_id="g-1", content="test reflection")
        assert record.metadata.attributes["_collection"] == COLLECTION_REFLECTIONS

    def test_list_collection_isolation(self) -> None:
        svc = self._svc()
        svc.store_reflection(goal_id="g-1", content="rfl")
        svc.store_execution(goal_id="g-1", summary="exec", status="success")
        reflections = self.repo.list_collection(COLLECTION_REFLECTIONS)
        executions = self.repo.list_collection(COLLECTION_EXECUTIONS)
        assert len(reflections) == 1
        assert len(executions) == 1

    def test_find_with_collection_filter(self) -> None:
        svc = self._svc()
        svc.store_reflection(goal_id="g-A", content="reflection A")
        svc.store_execution(goal_id="g-A", summary="exec A", status="success")
        results = self.repo.find(
            MemoryQuery(goal_id="g-A", top_k=10),
            collection=COLLECTION_REFLECTIONS,
        )
        assert all(
            r.record.metadata.attributes.get("_collection") == COLLECTION_REFLECTIONS
            for r in results
        )

    def test_semantic_search_with_collection(self) -> None:
        svc = self._svc()
        svc.store_reflection(goal_id="g-B", content="deep learning reflection")
        svc.store_execution(goal_id="g-B", summary="some execution", status="success")

        query_emb = self.embedder.embed_text("deep learning")
        from core.models.memory import MemoryQuery

        q = MemoryQuery(
            text="deep learning",
            top_k=5,
            attributes={"_embedding": query_emb},
        )
        results = self.repo.semantic_search(q, collection=COLLECTION_REFLECTIONS)
        assert all(
            r.record.metadata.attributes.get("_collection") == COLLECTION_REFLECTIONS
            for r in results
        )

    def test_latency_log_populated(self) -> None:
        svc = self._svc()
        svc.store_reflection(goal_id="g-C", content="content")
        log = self.repo.get_latency_log()
        assert len(log) > 0
        assert all("ms" in entry for entry in log)


# =========================================================================
# DI Wiring
# =========================================================================


class TestDIWiring:
    def test_build_orchestrator_includes_memory_service(self) -> None:
        """
        Verify build_orchestrator wires a MemoryService into the orchestrator.
        """
        from unittest.mock import patch

        # Patch LLM-dependent pieces to avoid network calls
        with (
            patch("core.di.container.build_llm_provider") as mock_llm,
            patch("core.di.container._register_agents"),
        ):
            from unittest.mock import MagicMock

            mock_llm.return_value = MagicMock()

            from core.di.container import build_orchestrator

            orchestrator = build_orchestrator()

        assert orchestrator._memory_service is not None
        assert isinstance(orchestrator._memory_service, MemoryService)


# =========================================================================
# Orchestrator Integration (memory persistence)
# =========================================================================


class TestOrchestratorMemoryPersistence:
    @pytest.mark.asyncio
    async def test_persist_to_memory_stores_execution(self) -> None:
        """_persist_to_memory should store an execution record without raising."""
        from unittest.mock import MagicMock

        provider = InMemoryProvider()
        repo = DefaultKnowledgeRepository(provider=provider)
        svc = MemoryService(
            repository=repo,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        from supervisor.orchestrator import SupervisorOrchestrator

        # Build a minimal orchestrator with memory service
        orchestrator = SupervisorOrchestrator(
            agent_registry=MagicMock(),
            capability_registry=MagicMock(),
            planner=MagicMock(),
            router=MagicMock(),
            validator=MagicMock(),
            report_generator=MagicMock(),
            memory_service=svc,
        )

        from core.models.domain import ExecutionResult, Goal

        goal = Goal(description="test memory persistence goal")
        exec_result = ExecutionResult(
            goal_id=goal.id,
            status="success",
            response="Task done",
            tasks=[],
        )
        fake_metrics = MagicMock()
        fake_metrics.execution_time_ms = 100
        fake_metrics.total_tasks = 2
        fake_metrics.failed_tasks = 0

        orchestrator._persist_to_memory(goal, exec_result, fake_metrics)

        # Verify at least one execution record was stored
        executions = repo.list_collection(COLLECTION_EXECUTIONS)
        assert len(executions) == 1
        assert executions[0].metadata.goal_id == goal.id

    @pytest.mark.asyncio
    async def test_persist_to_memory_stores_reflection(self) -> None:
        """_persist_to_memory should store a reflection record if report has one."""
        from unittest.mock import MagicMock

        provider = InMemoryProvider()
        repo = DefaultKnowledgeRepository(provider=provider)
        svc = MemoryService(
            repository=repo,
            embedding_provider=DeterministicEmbeddingProvider(),
        )

        from core.models.domain import ExecutionResult, Goal
        from supervisor.orchestrator import SupervisorOrchestrator

        orchestrator = SupervisorOrchestrator(
            agent_registry=MagicMock(),
            capability_registry=MagicMock(),
            planner=MagicMock(),
            router=MagicMock(),
            validator=MagicMock(),
            report_generator=MagicMock(),
            memory_service=svc,
        )

        goal = Goal(description="test reflection persistence")

        # Mock a reflection report on the execution result
        mock_scores = MagicMock()
        mock_scores.overall_score = 90.0

        mock_rr = MagicMock()
        mock_rr.model_dump_json.return_value = '{"overall_score": 90}'
        mock_rr.scores = mock_scores
        mock_rr.reflection_version = "1.0"
        mock_rr.observations = [1, 2]
        mock_rr.recommendations = [1]

        mock_report = MagicMock()
        mock_report.reflection_report = mock_rr

        exec_result = ExecutionResult(
            goal_id=goal.id,
            status="success",
            response="All done",
            tasks=[],
        )
        exec_result.report = mock_report

        fake_metrics = MagicMock()
        fake_metrics.execution_time_ms = 200

        orchestrator._persist_to_memory(goal, exec_result, fake_metrics)

        reflections = repo.list_collection(COLLECTION_REFLECTIONS)
        assert len(reflections) == 1
        assert reflections[0].metadata.goal_id == goal.id
        assert reflections[0].metadata.attributes.get("score") == 90.0
