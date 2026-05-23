"""FastEmbed semantic-router classification tier.

Primary classifier for VMs that the deterministic override rules did not match.
A query (normalized VM name + OS + description) is routed to the most similar
DRR category by embedding similarity. Below the score threshold, no verdict is
returned (caller falls back to Unknown).

Design notes:
- The FastEmbed encoder (model load) is cached module-level via lru_cache; it is
  the only expensive part. Each ``SemanticClassifier`` builds its own router
  reusing the cached encoder, so per-upload instances are cheap, concurrency-safe,
  and discardable.
- Self-learning (``add_learned``) adds same-file override-confident VM names as
  extra utterances under a parallel ``"<route>|learned"`` route that maps to the
  same (category, subcategory). In-memory only; never persisted.
- Route name convention: ``"{category}|{subcategory}"``.

API note (semantic-router==0.1.2):
  SemanticRouter.__init__ does not accept ``score_threshold`` as a constructor
  parameter. Instead, ``set_threshold(threshold)`` is called after construction to
  set the per-route and router-level threshold. The RouteChoice schema exposes
  ``similarity_score`` (Optional[float]) which is used directly.

Security: this module never logs VM names or query text — only counts/status.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter
from semantic_router.schema import RouteChoice

if TYPE_CHECKING:
    from semantic_router.encoders import DenseEncoder

    from store_predict.services.semantic_config import SemanticConfig

logger = logging.getLogger(__name__)

_DEFAULT_EXEMPLARS = Path(__file__).resolve().parent.parent / "data" / "classification_exemplars.yaml"
_ROUTE_SEP = "|"
_LEARNED_SUFFIX = _ROUTE_SEP + "learned"


@dataclass(frozen=True)
class SemanticVerdict:
    """A semantic classification result above the score threshold."""

    category: str
    subcategory: str
    route_name: str
    score: float


@lru_cache(maxsize=4)
def _get_encoder(model: str) -> DenseEncoder:
    """Return a cached FastEmbed encoder for *model* (model load is expensive)."""
    return FastEmbedEncoder(name=model)


def _route_name(category: str, subcategory: str) -> str:
    return f"{category}{_ROUTE_SEP}{subcategory}"


class SemanticClassifier:
    """Routes VM text to a DRR (category, subcategory) via embedding similarity."""

    def __init__(self, config: SemanticConfig, exemplars_path: Path | None = None) -> None:
        self._config = config
        self._encoder = _get_encoder(config.model)
        path = exemplars_path or _DEFAULT_EXEMPLARS
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        routes_data = data.get("routes") or []
        if not routes_data:
            raise ValueError(f"exemplars file has no 'routes': {path}")
        self._mapping: dict[str, tuple[str, str]] = {}
        routes: list[Route] = []
        for entry in routes_data:
            category = entry["category"]
            subcategory = entry["subcategory"]
            name = _route_name(category, subcategory)
            self._mapping[name] = (category, subcategory)
            routes.append(Route(name=name, utterances=list(entry["utterances"])))
        # Note: semantic-router==0.1.2 does not accept score_threshold in the
        # constructor. Use set_threshold() after construction instead.
        self._router = SemanticRouter(
            encoder=self._encoder,
            routes=routes,
            auto_sync="local",
        )
        self._router.set_threshold(config.score_threshold)
        logger.debug("SemanticClassifier ready with %d routes, threshold=%.2f", len(routes), config.score_threshold)

    def add_learned(self, utterances_by_pair: dict[tuple[str, str], list[str]]) -> None:
        """Add same-file override names as extra utterances (in-memory only).

        Each (category, subcategory) that has a base route gets a parallel
        ``"<route>|learned"`` route mapping to the same pair. Pairs without a
        base route (e.g. encryption variants) are skipped.
        """
        new_routes: list[Route] = []
        for (category, subcategory), utterances in utterances_by_pair.items():
            base = _route_name(category, subcategory)
            if base not in self._mapping or not utterances:
                continue
            learned = base + _LEARNED_SUFFIX
            if learned in self._mapping:
                continue
            self._mapping[learned] = (category, subcategory)
            new_routes.append(Route(name=learned, utterances=list(utterances)))
        if new_routes:
            self._router.add(new_routes)
            self._router.set_threshold(self._config.score_threshold)
            logger.debug("SemanticClassifier learned %d new routes", len(new_routes))

    def classify(self, text: str) -> SemanticVerdict | None:
        """Return a verdict for *text*, or None if empty / below threshold.

        ``SemanticRouter.__call__`` returns ``RouteChoice | list[RouteChoice]``.
        With the default ``limit=1`` we always get a single ``RouteChoice``, but
        we guard against the list branch defensively.
        """
        if not text or not text.strip():
            return None
        result = self._router(text)
        # result type is RouteChoice | list[RouteChoice] per the library's signature.
        # With limit=1 (default) it is always a single RouteChoice; guard for safety.
        choice = (result[0] if result else None) if isinstance(result, list) else result
        if choice is None or not isinstance(choice, RouteChoice) or choice.name is None:
            return None
        pair = self._mapping.get(choice.name)
        if pair is None:
            return None
        category, subcategory = pair
        if choice.similarity_score is None:
            return None  # matched but unscored: not defensible, treat as unclassified
        score = float(choice.similarity_score)
        return SemanticVerdict(category=category, subcategory=subcategory, route_name=choice.name, score=score)
