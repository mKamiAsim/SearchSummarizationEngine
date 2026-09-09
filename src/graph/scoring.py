"""Semantic relevance scoring (embeddings + LLM component coverage)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import numpy as np

from ..config.settings import Settings, get_settings
from ..core.llm_factory import create_llm
from ..utils.parsers import extract_json_from_response
from .prompts import QUERY_DECOMPOSITION_PROMPT, RELEVANCE_ASSESSMENT_PROMPT

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str) -> Any:
    """Load and cache a sentence-transformers embedding model."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def get_embedding_model(settings: Settings | None = None) -> Any:
    """Return the configured Hugging Face sentence embedding model."""
    settings = settings or get_settings()
    return _load_embedding_model(settings.embedding_model_name)


def embed_texts(texts: list[str], settings: Settings | None = None) -> np.ndarray:
    """Embed a list of texts into L2-normalized vectors."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model = get_embedding_model(settings)
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for already-normalized vectors (or raw)."""
    if a.size == 0 or b.size == 0:
        return 0.0
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def decompose_query_components(
    user_question: str,
    settings: Settings | None = None,
) -> list[str]:
    """Ask the LLM to split a (possibly multi-part) question into components."""
    settings = settings or get_settings()
    llm = create_llm(settings=settings, temperature=0.1)
    prompt = QUERY_DECOMPOSITION_PROMPT.format(user_question=user_question)
    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        payload = extract_json_from_response(str(text)) or {}
        components = payload.get("components") or []
        cleaned = [str(c).strip() for c in components if str(c).strip()]
        if cleaned:
            return cleaned
    except Exception as exc:
        logger.warning("Query decomposition failed: %s", exc)
    return [user_question.strip()]


def llm_relevance_score(
    *,
    user_question: str,
    query_components: list[str],
    source_url: str,
    summary_text: str,
    key_points: list[str],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Score one summary against the original query with structured LLM output."""
    settings = settings or get_settings()
    llm = create_llm(settings=settings, temperature=0.1)
    prompt = RELEVANCE_ASSESSMENT_PROMPT.format(
        user_question=user_question,
        query_components="\n".join(f"- {c}" for c in query_components) or "- (full question)",
        source_url=source_url,
        summary_text=summary_text,
        key_points="; ".join(key_points) if key_points else "(none)",
    )
    default: dict[str, Any] = {
        "llm_score": 1.0,
        "components_covered": [],
        "components_missing": list(query_components),
        "component_coverage_ratio": 0.0,
        "explanation": "Relevance scoring failed; treated as low relevance.",
    }
    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        payload = extract_json_from_response(str(text)) or {}
        score = float(payload.get("llm_score", 1.0))
        score = max(1.0, min(5.0, score))
        covered = [str(x) for x in (payload.get("components_covered") or [])]
        missing = [str(x) for x in (payload.get("components_missing") or [])]
        ratio = payload.get("component_coverage_ratio")
        if ratio is None and query_components:
            ratio = len(covered) / max(len(query_components), 1)
        ratio = float(ratio or 0.0)
        return {
            "llm_score": score,
            "components_covered": covered,
            "components_missing": missing,
            "component_coverage_ratio": max(0.0, min(1.0, ratio)),
            "explanation": str(payload.get("explanation") or ""),
        }
    except Exception as exc:
        logger.warning("LLM relevance scoring failed for %s: %s", source_url, exc)
        return default


def summary_passes_relevance(
    *,
    llm_score: float,
    embedding_similarity: float,
    component_coverage_ratio: float,
    num_components: int,
    settings: Settings | None = None,
) -> bool:
    """Apply hybrid pass/fail rules for a single summary."""
    settings = settings or get_settings()
    min_llm = settings.relevance_llm_min_score
    min_emb = settings.relevance_embedding_min

    # Multi-part queries require broader component coverage.
    required_coverage = (2.0 / 3.0) if num_components >= 2 else 0.0

    strong = llm_score >= 4.0 and embedding_similarity >= (min_emb * 0.85)
    standard = (
        llm_score >= min_llm
        and embedding_similarity >= min_emb
        and component_coverage_ratio >= required_coverage
    )
    return strong or standard


def score_summaries(
    *,
    user_question: str,
    summaries: list[dict[str, Any]],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Score all summaries and return evaluation payload + passed subset.

    Combines embedding cosine similarity with LLM 1–5 component-aware scoring.
    """
    settings = settings or get_settings()
    if not summaries:
        return {
            "relevance_percentage": 0.0,
            "relevant_count": 0,
            "total_count": 0,
            "query_components": [user_question],
            "per_summary": [],
            "explanation": "No summaries available to evaluate.",
            "passed_summaries": [],
            "coverage_gaps": [user_question],
        }

    components = decompose_query_components(user_question, settings=settings)
    texts = [user_question] + [str(s.get("summary") or "") for s in summaries]
    for component in components:
        texts.append(component)

    vectors = embed_texts(texts, settings=settings)
    query_vec = vectors[0]
    summary_vecs = vectors[1 : 1 + len(summaries)]
    component_vecs = vectors[1 + len(summaries) :]

    per_summary: list[dict[str, Any]] = []
    passed: list[dict[str, Any]] = []

    for idx, summary in enumerate(summaries):
        summary_text = str(summary.get("summary") or "")
        emb_full = cosine_similarity(query_vec, summary_vecs[idx])
        component_sims = [
            cosine_similarity(component_vecs[c_idx], summary_vecs[idx])
            for c_idx in range(len(components))
        ]
        emb_component_avg = (
            float(np.mean(component_sims)) if component_sims else emb_full
        )
        embedding_similarity = float(0.6 * emb_full + 0.4 * emb_component_avg)

        llm_result = llm_relevance_score(
            user_question=user_question,
            query_components=components,
            source_url=str(summary.get("url") or ""),
            summary_text=summary_text,
            key_points=list(summary.get("key_points") or []),
            settings=settings,
        )

        passed_flag = summary_passes_relevance(
            llm_score=float(llm_result["llm_score"]),
            embedding_similarity=embedding_similarity,
            component_coverage_ratio=float(llm_result["component_coverage_ratio"]),
            num_components=len(components),
            settings=settings,
        )

        enriched = {
            **summary,
            "embedding_similarity": round(embedding_similarity, 4),
            "llm_relevance_score": float(llm_result["llm_score"]),
            "component_coverage_ratio": float(llm_result["component_coverage_ratio"]),
            "components_covered": llm_result["components_covered"],
            "components_missing": llm_result["components_missing"],
            "relevance_explanation": llm_result["explanation"],
            "passed_relevance": passed_flag,
        }
        per_summary.append(
            {
                "url": enriched.get("url"),
                "passed": passed_flag,
                "embedding_similarity": enriched["embedding_similarity"],
                "llm_score": enriched["llm_relevance_score"],
                "component_coverage_ratio": enriched["component_coverage_ratio"],
                "explanation": enriched["relevance_explanation"],
            }
        )
        if passed_flag:
            passed.append(enriched)

    total = len(summaries)
    relevant_count = len(passed)
    relevance_percentage = (relevant_count / total) * 100.0 if total else 0.0

    covered_by_any: set[str] = set()
    for item in passed:
        covered_by_any.update(str(c) for c in (item.get("components_covered") or []))
    coverage_gaps = [c for c in components if c not in covered_by_any]
    if not passed:
        coverage_gaps = list(components)

    explanation = (
        f"{relevant_count}/{total} summaries passed hybrid relevance "
        f"({relevance_percentage:.1f}%)."
    )

    return {
        "relevance_percentage": relevance_percentage,
        "relevant_count": relevant_count,
        "total_count": total,
        "query_components": components,
        "per_summary": per_summary,
        "explanation": explanation,
        "passed_summaries": passed,
        "coverage_gaps": coverage_gaps,
    }
