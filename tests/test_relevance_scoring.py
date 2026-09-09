"""Unit tests for hybrid relevance pass/fail rules."""

import numpy as np

from src.graph.scoring import cosine_similarity, summary_passes_relevance


def test_cosine_similarity_identical():
    vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert cosine_similarity(vec, vec) == 1.0


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_summary_passes_standard_threshold():
    assert summary_passes_relevance(
        llm_score=3.8,
        embedding_similarity=0.55,
        component_coverage_ratio=1.0,
        num_components=1,
    )


def test_summary_fails_low_embedding():
    assert not summary_passes_relevance(
        llm_score=3.8,
        embedding_similarity=0.2,
        component_coverage_ratio=1.0,
        num_components=1,
    )


def test_multipart_requires_coverage():
    # Meets llm+embedding but weak component coverage on multi-part query.
    assert not summary_passes_relevance(
        llm_score=3.8,
        embedding_similarity=0.55,
        component_coverage_ratio=0.3,
        num_components=3,
    )


def test_strong_score_can_pass_multipart():
    assert summary_passes_relevance(
        llm_score=4.2,
        embedding_similarity=0.4,
        component_coverage_ratio=0.3,
        num_components=3,
    )
