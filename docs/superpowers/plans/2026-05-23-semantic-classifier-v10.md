# Semantic Classifier v10.0.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the regex+LLM classifier with a local FastEmbed `semantic-router` primary tier plus deterministic rule overrides, keeping the LLM module dormant.

**Architecture:** Per VM: normalize → deterministic overrides (must-win) → FastEmbed semantic route (curated + same-file self-learned exemplars) → `Unknown` below threshold; then the ADR-080 numeric size-reroute post-pass. The encoder is cached once; a fresh router is built per upload for concurrency safety.

**Tech Stack:** Python 3.12, `semantic-router[fastembed]` (ONNX, `BAAI/bge-small-en-v1.5`), pandas, pydantic-settings, NiceGUI, pytest. Spec: `docs/superpowers/specs/2026-05-23-semantic-classifier-design.md`.

**Conventions (do not violate):**
- Prefix every shell command with `rtk` (e.g. `rtk pytest`, `rtk git commit`).
- In the Bash tool the venv is NOT auto-activated — invoke python tools as `.venv/bin/<tool>` (e.g. `.venv/bin/pytest`). In the interactive terminal `pytest` works directly.
- Never log VM names / DataFrame contents — counts and status only.
- Tests use real objects/fixtures/sample data — **never** `unittest.mock`.
- All user-facing strings go through `t()`; add keys to both `en.yaml` and `fr.yaml`. French (`fr`) is primary.
- Never name a loop variable `t` (shadows the `t()` import) — use `wt`.
- Commit message trailer: `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`.

---

## File Structure

**Create:**
- `src/store_predict/services/semantic_config.py` — `SemanticConfig` (pydantic-settings, `SEMANTIC_` env prefix) + `get_semantic_config()` singleton. One responsibility: configuration.
- `src/store_predict/data/classification_exemplars.yaml` — curated synthetic utterances per base category. Reference data.
- `src/store_predict/pipeline/semantic_classifier.py` — `SemanticVerdict`, `SemanticClassifier`, cached encoder. One responsibility: semantic routing.
- `scripts/tune_semantic_thresholds.py` — dev/CI threshold tuning harness (not imported at runtime).
- `tests/test_semantic_config.py`, `tests/test_semantic_classifier.py`, `tests/test_classification_cascade.py` — new tests.
- `tests/fixtures/exemplars_min.yaml` — tiny exemplars file for fast unit tests.
- `docs/adr/082-semantic-router-primary-classifier.md`, `083-fastembed-offline-encoder.md`, `084-retire-llm-fallback-dormant.md`, `085-curated-self-learning-exemplars.md`.
- `docs/research/semantic-classifier.md`.

**Modify:**
- `src/store_predict/pipeline/classification.py` — add `build_override_rules()`; rewire `classify_dataframe()` to the cascade.
- `src/store_predict/ui/pages/upload.py` — replace rules+LLM block with overrides → semantic → default.
- `src/store_predict/i18n/locales/en.yaml`, `fr.yaml` — add `semantic.*` keys.
- `pyproject.toml` — add dependency, bump version to `10.0.0`.
- `Dockerfile` — pre-bake the FastEmbed model.
- `tests/test_real_customer_baseline.py` — adapt to new confidence model.
- `CHANGELOG.md`, `docs/adr/index.md`.

**Keep dormant (do NOT modify behavior, do NOT delete):**
- `src/store_predict/pipeline/llm_classifier.py`, `tests/test_llm_classifier.py`, `src/store_predict/services/llm_config.py`.

---

## Phase 1 — Config, Exemplars, SemanticClassifier

### Task 1: Add the `semantic-router[fastembed]` dependency

**Files:**
- Modify: `pyproject.toml:10-22` (dependencies array)

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add to the `dependencies` array (after the `litellm` line):

```toml
    "litellm>=1.83.7",
    "semantic-router[fastembed]>=0.1.0,<0.2.0",
    "pydantic>=2.12.5",
```

- [ ] **Step 2: Install and lock**

Run: `rtk uv pip install -e ".[dev]" && rtk uv lock`
Expected: resolves and installs `semantic-router`, `fastembed`, `onnxruntime`; updates `uv.lock`.

- [ ] **Step 3: Verify the import and encoder class are available**

Run: `.venv/bin/python -c "from semantic_router.routers import SemanticRouter; from semantic_router.encoders import FastEmbedEncoder; from semantic_router import Route; print('ok')"`
Expected: prints `ok` (no ImportError).

- [ ] **Step 4: Commit**

```bash
rtk git add pyproject.toml uv.lock
rtk git commit -m "build: add semantic-router[fastembed] dependency

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: `SemanticConfig` settings

**Files:**
- Create: `src/store_predict/services/semantic_config.py`
- Test: `tests/test_semantic_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_semantic_config.py
"""Tests for SemanticConfig (env-driven, mirrors LLMConfig pattern)."""

from __future__ import annotations

from store_predict.services.semantic_config import SemanticConfig


def test_defaults() -> None:
    cfg = SemanticConfig()
    assert cfg.enabled is True
    assert cfg.model == "BAAI/bge-small-en-v1.5"
    assert 0.0 < cfg.score_threshold < 1.0
    assert cfg.self_learning is True


def test_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SEMANTIC_ENABLED", "false")
    monkeypatch.setenv("SEMANTIC_SCORE_THRESHOLD", "0.42")
    cfg = SemanticConfig()
    assert cfg.enabled is False
    assert cfg.score_threshold == 0.42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_semantic_config.py -v`
Expected: FAIL — `ModuleNotFoundError: store_predict.services.semantic_config`.

- [ ] **Step 3: Write the implementation**

```python
# src/store_predict/services/semantic_config.py
"""Configuration for the semantic-router classification tier.

Reads from environment variables with the ``SEMANTIC_`` prefix (case-insensitive),
mirroring the ``LLMConfig`` pattern. The ``get_semantic_config()`` singleton reads
env vars once at first call. Tests override by instantiating ``SemanticConfig()``
directly, which bypasses the singleton cache.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SemanticConfig(BaseSettings):
    """Settings for the FastEmbed semantic classifier.

    Fields:
        enabled: Whether the semantic tier runs. Default ``True``.
        model: FastEmbed ONNX model name. Default ``BAAI/bge-small-en-v1.5``.
        score_threshold: Global minimum similarity for a route to win. Default
            ``0.5``; tuned per-route via ``scripts/tune_semantic_thresholds.py``.
        self_learning: Whether same-file override hits seed extra utterances.
            Default ``True``.
    """

    model_config = SettingsConfigDict(env_prefix="SEMANTIC_", case_sensitive=False)

    enabled: bool = True
    model: str = "BAAI/bge-small-en-v1.5"
    score_threshold: float = 0.5
    self_learning: bool = True


@lru_cache(maxsize=1)
def get_semantic_config() -> SemanticConfig:
    """Lazy singleton — reads env vars once at first call."""
    return SemanticConfig()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_semantic_config.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
rtk git add src/store_predict/services/semantic_config.py tests/test_semantic_config.py
rtk git commit -m "feat(semantic): add SemanticConfig settings

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Curated exemplars data file + minimal test fixture

The exemplars file maps each base DRR category/subcategory to example "utterances" (synthetic VM names + short descriptions). Encryption/compression variants are intentionally absent (user toggles). Route name = `"{category}|{subcategory}"`.

**Files:**
- Create: `src/store_predict/data/classification_exemplars.yaml`
- Create: `tests/fixtures/exemplars_min.yaml`
- Modify: `pyproject.toml:53-54` (package-data — add `data/*.yaml`)

- [ ] **Step 1: Create the production exemplars file**

```yaml
# src/store_predict/data/classification_exemplars.yaml
# Curated, SYNTHETIC exemplars for the semantic classifier. No customer data.
# Each route maps to a DRR base category/subcategory (see data/DRR.csv).
# Encryption/compression variants are deliberately excluded — they are user toggles.
# Utterances are example VM names + short role phrases the encoder embeds.
routes:
  - category: Database
    subcategory: Oracle
    utterances:
      - "oracle database server"
      - "ora db production instance"
      - "oracle rac node"
      - "oradb listener host"
  - category: Database
    subcategory: Microsoft SQL
    utterances:
      - "microsoft sql server"
      - "mssql database node"
      - "sql server reporting services"
      - "ms sql always-on replica"
  - category: Database
    subcategory: My SQL / NoSQL
    utterances:
      - "mysql database server"
      - "mariadb cluster node"
      - "redis cache store"
      - "nosql document database"
  - category: Database
    subcategory: PostgreSQL
    utterances:
      - "postgresql database server"
      - "postgres primary node"
      - "pgsql analytics database"
  - category: Database
    subcategory: DB2
    utterances:
      - "ibm db2 database server"
      - "db2 mainframe gateway"
  - category: Database
    subcategory: MongoDB
    utterances:
      - "mongodb document store"
      - "mongo replica set member"
  - category: Database
    subcategory: SAP HANA(S4)
    utterances:
      - "sap hana in-memory database"
      - "s4 hana production"
      - "hana db scale-out node"
  - category: Database
    subcategory: SAP Traditional (R/3 / ECC)
    utterances:
      - "sap ecc application server"
      - "sap r/3 traditional system"
      - "sap netweaver host"
  - category: HealthCare
    subcategory: EMR/EHR (Epic, McKesson)
    utterances:
      - "epic electronic medical records"
      - "mckesson ehr server"
      - "hospital clinical records system"
  - category: File
    subcategory: General Purpose
    utterances:
      - "general purpose file server"
      - "shared documents fileserver"
      - "smb network file share"
  - category: File
    subcategory: Content Servers (Git, Sharepoint)
    utterances:
      - "git source control server"
      - "sharepoint content server"
      - "gitlab repository host"
  - category: File
    subcategory: Developer Workspaces (DevOps)
    utterances:
      - "devops build agent workspace"
      - "jenkins ci developer host"
      - "developer sandbox workstation"
  - category: VDI
    subcategory: Full Clone / MCS (Citrix)
    utterances:
      - "citrix mcs full clone desktop"
      - "persistent vdi virtual desktop"
  - category: VDI
    subcategory: Linked Clone / PVS (Citrix)
    utterances:
      - "citrix pvs linked clone"
      - "non-persistent vdi pool desktop"
  - category: VDI
    subcategory: VDI Profiles
    utterances:
      - "vdi user profile management"
      - "roaming profile share for desktops"
  - category: Logging - Analytics
    subcategory: FortiNet, Elastic Search, Splunk, ELK, etc
    utterances:
      - "splunk log indexer"
      - "elasticsearch search cluster node"
      - "elk logging stack"
      - "fortinet analyzer appliance"
  - category: Email
    subcategory: Domino/Notes, Exchange, Sendmail, Zimbra, etc
    utterances:
      - "microsoft exchange mailbox server"
      - "exchange transport hub"
      - "zimbra mail server"
      - "lotus domino notes server"
  - category: Containers
    subcategory: Kubernetes, OpenShift, Docker, Tanzu, etc
    utterances:
      - "kubernetes worker node"
      - "openshift container platform host"
      - "docker swarm node"
      - "tanzu kubernetes cluster"
  - category: Virtual Machines
    subcategory: VMware / Hyper-V / KVM - No Database, File nor Email
    utterances:
      - "generic windows application server"
      - "linux utility virtual machine"
      - "internal line-of-business app host"
  - category: VM Replication
    subcategory: Veeam, Zerto, RP4VM
    utterances:
      - "veeam backup proxy"
      - "zerto replication appliance"
      - "rp4vm recoverpoint host"
  - category: VM Replication
    subcategory: Commvault
    utterances:
      - "commvault media agent"
      - "commvault backup commserve"
  - category: Boot from SAN
    subcategory: Linux, VMware, Windows - OS Boot
    utterances:
      - "boot from san os volume"
      - "diskless esxi boot lun"
  - category: Web Servers
    subcategory: Content not included
    utterances:
      - "nginx reverse proxy web server"
      - "apache httpd front-end"
      - "iis web application server"
```

- [ ] **Step 2: Create the minimal test fixture**

```yaml
# tests/fixtures/exemplars_min.yaml
# Tiny exemplars set for fast, deterministic unit tests.
routes:
  - category: Database
    subcategory: Microsoft SQL
    utterances:
      - "microsoft sql server"
      - "mssql database node"
  - category: Email
    subcategory: Domino/Notes, Exchange, Sendmail, Zimbra, etc
    utterances:
      - "microsoft exchange mailbox server"
      - "zimbra mail server"
  - category: Containers
    subcategory: Kubernetes, OpenShift, Docker, Tanzu, etc
    utterances:
      - "kubernetes worker node"
      - "docker swarm host"
```

- [ ] **Step 3: Register YAML as package data**

In `pyproject.toml`, update the package-data line:

```toml
[tool.setuptools.package-data]
store_predict = ["data/*.csv", "data/*.png", "data/*.ttf", "data/*.yaml", "i18n/locales/*.yaml"]
```

- [ ] **Step 4: Verify the YAML parses and every subcategory exists in DRR.csv**

Run:
```bash
.venv/bin/python -c "
import yaml
from pathlib import Path
from store_predict.config import DRR_CSV_PATH
import csv
ex = yaml.safe_load(Path('src/store_predict/data/classification_exemplars.yaml').read_text())
pairs = {(r['category'], r['subcategory']) for r in ex['routes']}
with open(DRR_CSV_PATH, encoding='utf-8') as f:
    drr = {(row['Workload Category'], row['Application/Use case']) for row in csv.DictReader(f, delimiter=';')}
missing = pairs - drr
assert not missing, f'exemplar pairs not in DRR.csv: {missing}'
print('ok', len(pairs), 'routes')
"
```
Expected: prints `ok 23 routes` (no AssertionError). If any pair is missing, fix the YAML to match DRR.csv exactly.

- [ ] **Step 5: Commit**

```bash
rtk git add src/store_predict/data/classification_exemplars.yaml tests/fixtures/exemplars_min.yaml pyproject.toml
rtk git commit -m "feat(semantic): add curated classification exemplars

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: `SemanticClassifier` — load, classify, self-learn

The encoder (model load) is cached at module level. Each `SemanticClassifier` builds its own router (sharing the cached encoder), so per-upload instances are concurrency-safe and discardable. `add_learned()` adds same-file override names as extra utterances under a parallel `"…|learned"` route mapping to the same category/subcategory.

**Files:**
- Create: `src/store_predict/pipeline/semantic_classifier.py`
- Test: `tests/test_semantic_classifier.py`

- [ ] **Step 1: Write the failing test (real FastEmbed — no mocks)**

```python
# tests/test_semantic_classifier.py
"""Tests for SemanticClassifier using the real FastEmbed encoder.

These exercise real embeddings (no mocks, per project conventions). The model
is downloaded on first run and cached; tests are marked slow.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from store_predict.pipeline.semantic_classifier import (
    SemanticClassifier,
    SemanticVerdict,
)
from store_predict.services.semantic_config import SemanticConfig

_FIXTURE = Path(__file__).parent / "fixtures" / "exemplars_min.yaml"


@pytest.fixture(scope="module")
def classifier() -> SemanticClassifier:
    cfg = SemanticConfig(score_threshold=0.3)
    return SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)


@pytest.mark.slow
def test_classifies_obvious_sql(classifier: SemanticClassifier) -> None:
    verdict = classifier.classify("production microsoft sql server database")
    assert verdict is not None
    assert verdict.category == "Database"
    assert verdict.subcategory == "Microsoft SQL"
    assert 0.0 <= verdict.score <= 1.0


@pytest.mark.slow
def test_classifies_kubernetes(classifier: SemanticClassifier) -> None:
    verdict = classifier.classify("kubernetes container worker node")
    assert verdict is not None
    assert verdict.category == "Containers"


@pytest.mark.slow
def test_below_threshold_returns_none() -> None:
    cfg = SemanticConfig(score_threshold=0.99)  # nothing will clear this
    clf = SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)
    assert clf.classify("xyzzy completely unrelated gibberish 12345") is None


@pytest.mark.slow
def test_empty_text_returns_none(classifier: SemanticClassifier) -> None:
    assert classifier.classify("   ") is None


@pytest.mark.slow
def test_self_learning_shifts_ambiguous_match() -> None:
    cfg = SemanticConfig(score_threshold=0.3)
    clf = SemanticClassifier(config=cfg, exemplars_path=_FIXTURE)
    # Teach the SQL route a customer-specific naming token, then verify a
    # sibling host using that token routes to the learned category.
    clf.add_learned({("Database", "Microsoft SQL"): ["acme-dbx-01", "acme-dbx-02"]})
    verdict = clf.classify("acme-dbx-07")
    assert verdict is not None
    assert verdict.category == "Database"


def test_verdict_is_frozen() -> None:
    v = SemanticVerdict(category="Database", subcategory="Microsoft SQL", route_name="Database|Microsoft SQL", score=0.8)
    with pytest.raises((AttributeError, Exception)):
        v.score = 0.1  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_semantic_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: store_predict.pipeline.semantic_classifier`.

- [ ] **Step 3: Write the implementation**

```python
# src/store_predict/pipeline/semantic_classifier.py
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

if TYPE_CHECKING:
    from semantic_router.encoders import DenseEncoder

    from store_predict.services.semantic_config import SemanticConfig

logger = logging.getLogger(__name__)

_DEFAULT_EXEMPLARS = Path(__file__).resolve().parent.parent / "data" / "classification_exemplars.yaml"
_ROUTE_SEP = "|"
_LEARNED_SUFFIX = "|learned"


@dataclass(frozen=True)
class SemanticVerdict:
    """A semantic classification result above the score threshold."""

    category: str
    subcategory: str
    route_name: str
    score: float


@lru_cache(maxsize=4)
def _get_encoder(model: str) -> "DenseEncoder":
    """Return a cached FastEmbed encoder for *model* (model load is expensive)."""
    return FastEmbedEncoder(name=model)


def _route_name(category: str, subcategory: str) -> str:
    return f"{category}{_ROUTE_SEP}{subcategory}"


class SemanticClassifier:
    """Routes VM text to a DRR (category, subcategory) via embedding similarity."""

    def __init__(self, config: "SemanticConfig", exemplars_path: Path | None = None) -> None:
        self._config = config
        self._encoder = _get_encoder(config.model)
        path = exemplars_path or _DEFAULT_EXEMPLARS
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self._mapping: dict[str, tuple[str, str]] = {}
        routes: list[Route] = []
        for entry in data["routes"]:
            category = entry["category"]
            subcategory = entry["subcategory"]
            name = _route_name(category, subcategory)
            self._mapping[name] = (category, subcategory)
            routes.append(Route(name=name, utterances=list(entry["utterances"])))
        self._router = SemanticRouter(
            encoder=self._encoder,
            routes=routes,
            score_threshold=config.score_threshold,
            auto_sync="local",
        )

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

    def classify(self, text: str) -> SemanticVerdict | None:
        """Return a verdict for *text*, or None if empty / below threshold."""
        if not text or not text.strip():
            return None
        choice = self._router(text)
        if choice is None or choice.name is None:
            return None
        pair = self._mapping.get(choice.name)
        if pair is None:
            return None
        category, subcategory = pair
        score = float(choice.similarity_score) if choice.similarity_score is not None else 0.0
        return SemanticVerdict(category=category, subcategory=subcategory, route_name=choice.name, score=score)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_semantic_classifier.py -v`
Expected: PASS. First run downloads the ONNX model (network needed once). If `similarity_score` is not present on the result object, run `.venv/bin/python -c "from semantic_router.routers import SemanticRouter; print([a for a in dir(SemanticRouter) if 'retrieve' in a])"` and adapt `classify()` to use `retrieve_multiple_routes(text)[0]` whose items expose `.name` and `.similarity_score`.

- [ ] **Step 5: Register the `slow` marker**

In `pyproject.toml` under `[tool.pytest.ini_options]`, add:

```toml
markers = ["slow: tests that load the FastEmbed model (real embeddings)"]
```

- [ ] **Step 6: Commit**

```bash
rtk git add src/store_predict/pipeline/semantic_classifier.py tests/test_semantic_classifier.py pyproject.toml
rtk git commit -m "feat(semantic): add SemanticClassifier with FastEmbed + self-learning

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2 — Override Rules

### Task 5: `build_override_rules()`

**Files:**
- Modify: `src/store_predict/pipeline/classification.py` (add function after `build_default_rules`, near line 992)
- Test: `tests/test_classification.py` (add a class)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_classification.py`:

```python
class TestBuildOverrideRules:
    def test_excludes_os_fallback_and_default(self) -> None:
        from store_predict.pipeline.classification import (
            build_default_rules,
            build_override_rules,
        )

        overrides = build_override_rules()
        assert overrides, "override set must not be empty"
        assert all(r.priority < 900 for r in overrides)
        # every override is also present in the full default set
        default_names = {r.name for r in build_default_rules()}
        assert {r.name for r in overrides} <= default_names

    def test_high_precision_app_rules_are_overrides(self) -> None:
        from store_predict.pipeline.classification import (
            RuleRegistry,
            build_override_rules,
        )

        reg = RuleRegistry(build_override_rules())
        verdict = reg.classify("PRD-MSSQL-01", "Microsoft Windows Server 2019")
        assert verdict.category == "Database"
        assert verdict.confidence == "rule_match"

    def test_generic_windows_is_not_an_override(self) -> None:
        from store_predict.pipeline.classification import (
            RuleRegistry,
            build_override_rules,
        )

        reg = RuleRegistry(build_override_rules())
        # No app keyword in the name → no override → registry returns its default.
        verdict = reg.classify("APPSRV-GENERIC-01", "Microsoft Windows Server 2019")
        assert verdict.confidence == "default"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_classification.py::TestBuildOverrideRules -v`
Expected: FAIL — `ImportError: cannot import name 'build_override_rules'`.

- [ ] **Step 3: Add the implementation**

In `src/store_predict/pipeline/classification.py`, immediately after the end of `build_default_rules()` (after line 991), add:

```python
def build_override_rules() -> list[ClassificationRule]:
    """High-precision, must-win classification rules for the semantic cascade.

    These are exactly the named application/folder rules from
    :func:`build_default_rules` with ``priority < 900``. The OS-based fallback
    rules (900-998) and the catch-all default (999) are intentionally excluded:
    VMs that only those rules would have matched flow to the semantic tier
    instead, which makes a better category guess than a generic OS bucket.
    """
    return [rule for rule in build_default_rules() if rule.priority < 900]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_classification.py::TestBuildOverrideRules -v`
Expected: PASS (3 tests). If `test_generic_windows_is_not_an_override` fails because a `<900` rule matches generic Windows on `os_patterns`, inspect that rule; if it is genuinely an OS-only generic rule mis-tiered below 900, note it for follow-up but do not change `build_default_rules` here — adjust the test's example name/OS to one with no `<900` match.

- [ ] **Step 5: Commit**

```bash
rtk git add src/store_predict/pipeline/classification.py tests/test_classification.py
rtk git commit -m "feat(classifier): add build_override_rules (priority<900 subset)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 3 — Cascade Integration

### Task 6: Rewire `classify_dataframe()` to the cascade

`classify_dataframe` gains an optional `semantic` parameter. When `None`, behavior is overrides-only + default (used by simple unit tests). When a `SemanticClassifier` is passed, the full cascade runs with self-learning. The ADR-080 size-reroute post-pass is preserved unchanged.

**Files:**
- Modify: `src/store_predict/pipeline/classification.py:1017-1070` (`classify_dataframe`)
- Test: `tests/test_classification_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_classification_cascade.py
"""Tests for the override -> semantic -> default cascade in classify_dataframe."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

_FIXTURE = Path(__file__).parent / "fixtures" / "exemplars_min.yaml"


def _df(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_override_wins_and_is_labelled_override() -> None:
    df = _df([{"vm_name": "PRD-MSSQL-01", "os_name": "Windows Server 2019"}])
    reg = RuleRegistry(build_override_rules())
    out = classify_dataframe(df, reg)  # no semantic tier
    assert out.loc[0, "workload_category"] == "Database"
    assert out.loc[0, "classification_confidence"] == "override"
    assert out.loc[0, "classification_rule"].startswith("override:")


def test_unmatched_without_semantic_is_default() -> None:
    df = _df([{"vm_name": "GENERIC-APP-01", "os_name": "Windows Server 2019"}])
    reg = RuleRegistry(build_override_rules())
    out = classify_dataframe(df, reg)
    assert out.loc[0, "classification_confidence"] == "default"
    assert out.loc[0, "workload_subcategory"] == "Unknown (Reducible)"


@pytest.mark.slow
def test_semantic_classifies_unmatched() -> None:
    df = _df([{"vm_name": "mailbox exchange relay", "os_name": "Windows Server 2019"}])
    reg = RuleRegistry(build_override_rules())
    sem = SemanticClassifier(config=SemanticConfig(score_threshold=0.3), exemplars_path=_FIXTURE)
    out = classify_dataframe(df, reg, semantic=sem)
    assert out.loc[0, "workload_category"] == "Email"
    assert out.loc[0, "classification_confidence"] == "semantic"
    assert out.loc[0, "classification_rule"].startswith("semantic:")


@pytest.mark.slow
def test_below_threshold_falls_to_default_not_crash() -> None:
    df = _df([{"vm_name": "zzz unrelated gibberish", "os_name": ""}])
    reg = RuleRegistry(build_override_rules())
    sem = SemanticClassifier(config=SemanticConfig(score_threshold=0.99), exemplars_path=_FIXTURE)
    out = classify_dataframe(df, reg, semantic=sem)
    assert out.loc[0, "classification_confidence"] == "default"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_classification_cascade.py -v`
Expected: FAIL — `classify_dataframe()` got an unexpected keyword argument `semantic` (and `override` confidence not produced).

- [ ] **Step 3: Rewrite `classify_dataframe`**

Replace the entire body of `classify_dataframe` (lines 1017-1070) with:

```python
def classify_dataframe(
    df: pd.DataFrame,
    registry: RuleRegistry,
    semantic: SemanticClassifier | None = None,
) -> pd.DataFrame:
    """Classify all VMs in *df* via override -> semantic -> default cascade.

    Added columns: ``workload_category``, ``workload_subcategory``,
    ``classification_rule``, ``classification_confidence``.

    Pass 1 runs the deterministic override *registry* (priority<900 rules). A
    match is labelled ``confidence="override"`` and ``classification_rule
    ="override:<RuleName>"``. Override hits also seed the semantic tier's
    self-learning (same-file utterances) when *semantic* is provided and
    self-learning is enabled.

    Pass 2 runs the *semantic* classifier on rows that no override matched. A
    verdict at/above threshold is labelled ``confidence="semantic"`` and
    ``classification_rule="semantic:<route> (score 0.84)"``. Below threshold —
    or when *semantic* is None — the row is ``confidence="default"`` /
    ``Unknown (Reducible)``.

    A per-row semantic error never aborts the upload: it falls to ``default``.

    Size-aware reroute (ADR-080): rows with ``confidence in {"semantic",
    "default"}`` AND original subcategory in ``_UNKNOWN_SUBCATEGORIES`` AND
    ``provisioned_mib >= LARGE_VM_THRESHOLD_MIB`` are rerouted to "File /
    General Purpose" (DRR 2.0), tagged ``rule_name="Large generic (>=100 GiB)"``.
    """
    result = df.copy()

    has_description = "vm_description" in df.columns
    has_folder = "vm_folder" in df.columns
    has_provisioned = "provisioned_mib" in df.columns

    def _text(vm_name: str, os_name: str, description: str) -> str:
        return " ".join(part for part in (vm_name, os_name, description) if part).strip()

    rows: list[dict[str, str]] = []
    for _, row in df.iterrows():
        vm_name = str(row["vm_name"]) if pd.notna(row["vm_name"]) else ""
        os_name = str(row["os_name"]) if pd.notna(row["os_name"]) else ""
        description = str(row["vm_description"]) if has_description and pd.notna(row.get("vm_description")) else ""
        folder = str(row["vm_folder"]) if has_folder and pd.notna(row.get("vm_folder")) else ""
        rows.append({"vm_name": vm_name, "os_name": os_name, "description": description, "folder": folder})

    # Pass 1: deterministic overrides.
    verdicts: list[ClassificationResult | None] = []
    learned: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        rule_verdict = registry.classify(r["vm_name"], r["os_name"], r["description"], r["folder"])
        if rule_verdict.confidence == "rule_match":
            verdicts.append(
                ClassificationResult(
                    category=rule_verdict.category,
                    subcategory=rule_verdict.subcategory,
                    rule_name=f"override:{rule_verdict.rule_name}",
                    confidence="override",
                )
            )
            learned.setdefault((rule_verdict.category, rule_verdict.subcategory), []).append(r["vm_name"])
        else:
            verdicts.append(None)  # unmatched -> pass 2

    # Pass 2: semantic tier (with same-file self-learning).
    if semantic is not None:
        if semantic_self_learning_enabled(semantic) and learned:
            semantic.add_learned(learned)
        for i, verdict in enumerate(verdicts):
            if verdict is not None:
                continue
            r = rows[i]
            try:
                sv = semantic.classify(_text(r["vm_name"], r["os_name"], r["description"]))
            except Exception:  # noqa: BLE001 - never abort the upload on a model error
                logger.warning("Semantic classification error on one VM; falling back to default")
                sv = None
            if sv is not None:
                verdicts[i] = ClassificationResult(
                    category=sv.category,
                    subcategory=sv.subcategory,
                    rule_name=f"semantic:{sv.route_name} (score {sv.score:.2f})",
                    confidence="semantic",
                )

    # Fill remaining unmatched rows with the explicit default.
    classifications: list[ClassificationResult] = [
        v if v is not None else ClassificationResult("Unknown (Reducible)", "Unknown (Reducible)", "default", "default")
        for v in verdicts
    ]

    # Size-aware reroute post-pass (ADR-080).
    if has_provisioned:
        for i, verdict in enumerate(classifications):
            if verdict.confidence in ("semantic", "default") and verdict.subcategory in _UNKNOWN_SUBCATEGORIES:
                prov = df.iloc[i].get("provisioned_mib")
                if pd.notna(prov) and float(prov) >= LARGE_VM_THRESHOLD_MIB:
                    classifications[i] = ClassificationResult(
                        category="File",
                        subcategory="General Purpose",
                        rule_name="Large generic (>=100 GiB)",
                        confidence=verdict.confidence,
                    )

    result["workload_category"] = [c.category for c in classifications]
    result["workload_subcategory"] = [c.subcategory for c in classifications]
    result["classification_rule"] = [c.rule_name for c in classifications]
    result["classification_confidence"] = [c.confidence for c in classifications]
    return result
```

- [ ] **Step 4: Add the self-learning helper + imports**

At the top of `classification.py`, add to the imports (after `import re`):

```python
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from store_predict.pipeline.semantic_classifier import SemanticClassifier

logger = logging.getLogger(__name__)
```

And add this helper just above `classify_dataframe`:

```python
def semantic_self_learning_enabled(semantic: "SemanticClassifier") -> bool:
    """Return whether *semantic* has self-learning enabled in its config."""
    return bool(semantic._config.self_learning)  # noqa: SLF001 - internal config read
```

Note: if SLF001 (private member access) is undesirable, add a public `self_learning` property to `SemanticClassifier` returning `self._config.self_learning` and call that instead.

- [ ] **Step 5: Run the cascade tests + the existing classification tests**

Run: `.venv/bin/pytest tests/test_classification_cascade.py tests/test_classification.py -v`
Expected: cascade tests PASS. Some existing `tests/test_classification.py::TestClassifyDataFrame` tests assert old confidence values (`os_fallback`, `default`) on an unmatched generic VM — these now require an override registry. Fix them in Step 6.

- [ ] **Step 6: Update existing `classify_dataframe` tests for the new model**

In `tests/test_classification.py::TestClassifyDataFrame`, the tests construct a `RuleRegistry(build_default_rules())`. Change them to `RuleRegistry(build_override_rules())` and update any `classification_confidence` assertion that expects `os_fallback` to expect `default` (no semantic tier passed). Keep `rule_match`-based expectations updated to `override`. Re-run:

Run: `.venv/bin/pytest tests/test_classification.py -v`
Expected: PASS.

- [ ] **Step 7: Run ruff + mypy on the changed module**

Run: `rtk ruff check src/store_predict/pipeline/classification.py && rtk mypy src/store_predict/pipeline/classification.py`
Expected: clean (fix any reported issue).

- [ ] **Step 8: Commit**

```bash
rtk git add src/store_predict/pipeline/classification.py tests/test_classification_cascade.py tests/test_classification.py
rtk git commit -m "feat(classifier): override -> semantic -> default cascade

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 4 — Pipeline Wiring, i18n, Docker, LLM Dormant

### Task 7: i18n keys for the semantic tier

**Files:**
- Modify: `src/store_predict/i18n/locales/en.yaml` (after the `llm:` block, ~line 248)
- Modify: `src/store_predict/i18n/locales/fr.yaml` (same location)

- [ ] **Step 1: Add `semantic:` block to `en.yaml`**

After the `llm:` block (after line 248), add:

```yaml
semantic:
  classifying: "Classifying VMs by semantic similarity..."
  classifying_progress: "Semantic classification: %{done} / %{total} VMs"
  classified_notify: "Semantically classified %{count} VM(s)"
  error: "Semantic classification unavailable; rule-based results will be used."
```

- [ ] **Step 2: Add the French translation to `fr.yaml`**

Find the `llm:` block in `fr.yaml` and add after it:

```yaml
semantic:
  classifying: "Classification des VM par similarité sémantique..."
  classifying_progress: "Classification sémantique : %{done} / %{total} VM"
  classified_notify: "%{count} VM classée(s) sémantiquement"
  error: "Classification sémantique indisponible ; les résultats par règles seront utilisés."
```

- [ ] **Step 3: Verify both locales load and the keys resolve**

Run:
```bash
.venv/bin/python -c "
from store_predict.i18n import t
import i18n
for loc in ('en', 'fr'):
    i18n.set('locale', loc)
    assert 'semantic' not in t('semantic.classifying').lower() or loc=='en'
    print(loc, '->', t('semantic.classifying'))
"
```
Expected: prints an English and a French sentence (no `[missing translation]`).

- [ ] **Step 4: Commit**

```bash
rtk git add src/store_predict/i18n/locales/en.yaml src/store_predict/i18n/locales/fr.yaml
rtk git commit -m "i18n: add semantic classification strings (en, fr)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Wire the cascade into `_run_pipeline`, unwire the LLM

**Files:**
- Modify: `src/store_predict/ui/pages/upload.py:18-41` (imports) and `:232-270` (`_run_pipeline` body)

- [ ] **Step 1: Update imports**

In `upload.py`, change the classification import (lines 18-22) to add `build_override_rules` and the semantic classifier; leave the `llm_classifier` import in place but it becomes unused (dormant). Replace lines 18-30 region:

```python
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import ingest_file, ingest_two_files
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.pipeline.session_archive import is_session_zip, restore_session_zip
from store_predict.pipeline.validation import validate_upload
from store_predict.pipeline.zip_extraction import extract_liveoptics_from_zip
from store_predict.services.drr_table import DRRTable
from store_predict.services.semantic_config import get_semantic_config
```

(Remove the now-unused `build_default_rules`, `classify_unknown_vms_async`, and `LLMConfig` imports. Keep `save_rule_suggestions` import only if still referenced elsewhere; otherwise remove it. `llm_classifier.py` itself stays in the tree, dormant.)

- [ ] **Step 2: Replace the rules+LLM block in `_run_pipeline`**

Replace lines 232-270 (from `progress.value = 0.6` through the `# --- End LLM Classification Fallback ---` comment) with:

```python
            progress.value = 0.6
            registry = RuleRegistry(build_override_rules())
            sem_cfg = get_semantic_config()
            semantic = None
            if sem_cfg.enabled:
                with upload_widget:
                    sem_notif = ui.notification(t("semantic.classifying"), spinner=True, timeout=None, type="info")
                try:
                    semantic = await run.io_bound(SemanticClassifier, sem_cfg)
                except Exception:
                    logger.warning("Semantic classifier init failed; using overrides + default only")
                    semantic = None
                    with upload_widget:
                        sem_notif.message = t("semantic.error")
                        sem_notif.type = "warning"
                        sem_notif.spinner = False

            df = await run.io_bound(classify_dataframe, df, registry, semantic)

            if semantic is not None:
                sem_count = int((df["classification_confidence"] == "semantic").sum())
                with upload_widget:
                    if sem_count > 0:
                        sem_notif.message = t("semantic.classified_notify", count=sem_count)
                        sem_notif.type = "positive"
                    else:
                        sem_notif.dismiss()
                    sem_notif.spinner = False
```

- [ ] **Step 3: Type-check and lint the page**

Run: `rtk mypy src/store_predict/ui/pages/upload.py && rtk ruff check src/store_predict/ui/pages/upload.py`
Expected: clean. Fix unused-import (F401) errors by removing the dormant imports flagged.

- [ ] **Step 4: Smoke-run the import graph**

Run: `.venv/bin/python -c "import store_predict.ui.pages.upload; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
rtk git add src/store_predict/ui/pages/upload.py
rtk git commit -m "feat(ui): wire semantic cascade into upload pipeline; unwire LLM

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Pre-bake the FastEmbed model into the Docker image

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Inspect the current Dockerfile**

Run: `rtk read Dockerfile`
Identify the stage where the package is installed (after `uv pip install`/`pip install`) and the `FASTEMBED_CACHE_PATH` location used at runtime.

- [ ] **Step 2: Add a model pre-download layer**

After the dependency install step and before the `HEALTHCHECK`/`CMD`, add:

```dockerfile
# Pre-download the FastEmbed model so the container runs fully offline.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed_cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"
```

(If the runtime user is non-root, ensure `/opt/fastembed_cache` is writable by that user, or run the pre-download as that user. Match the model name to `SemanticConfig.model`.)

- [ ] **Step 3: Build the image and confirm offline model presence**

Run: `rtk docker compose build`
Then: `rtk docker compose run --rm <service> python -c "import os; print(os.listdir(os.environ.get('FASTEMBED_CACHE_PATH','/opt/fastembed_cache')))"`
Expected: lists the cached model files (non-empty).

- [ ] **Step 4: Commit**

```bash
rtk git add Dockerfile
rtk git commit -m "build(docker): pre-bake FastEmbed model for offline use

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 5 — Baseline, Tuning, Versioning, Docs

### Task 10: Adapt the real-customer baseline test

The baseline file is local-only (skips in CI). The folder-based assertions (SAP HANA, Email, DDVE, PowerFlex) must survive as overrides. The `os_fallback ≤ 940` assertion is replaced by an Unknown-rate gate, since `os_fallback` is no longer produced.

**Files:**
- Modify: `tests/test_real_customer_baseline.py`

- [ ] **Step 1: Update the fixture to use the cascade**

Replace the imports and `classified_customer_df` fixture:

```python
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_override_rules,
    classify_dataframe,
)
from store_predict.pipeline.parsers.rvtools import parse_rvtools
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

# ...

@pytest.fixture(scope="module")
def classified_customer_df():  # type: ignore[no-untyped-def]
    if not CUSTOMER_FILE.exists():
        pytest.skip(f"Customer baseline file not present: {CUSTOMER_FILE}")
    df = parse_rvtools(CUSTOMER_FILE)
    df = df[df["is_powered_on"]].reset_index(drop=True)
    registry = RuleRegistry(build_override_rules())
    semantic = SemanticClassifier(config=SemanticConfig())
    return classify_dataframe(df, registry, semantic=semantic)
```

- [ ] **Step 2: Replace the `os_fallback` assertion with an Unknown-rate gate**

Replace `test_os_fallback_reduced` with:

```python
def test_unknown_rate_not_regressed(classified_customer_df) -> None:  # type: ignore[no-untyped-def]
    """The semantic tier must classify the bulk of formerly-OS-fallback VMs.
    On the May 2026 file (~1373 VMs) at most 300 should remain 'default'
    (Unknown). The v9 ruleset put ~940 in os_fallback; semantic routing should
    pull most of those into real categories."""
    total = len(classified_customer_df)
    n_default = int((classified_customer_df["classification_confidence"] == "default").sum())
    assert n_default <= 300, (
        f"Unknown/default rate too high: {n_default}/{total}\n{_summary(classified_customer_df)}"
    )
```

Keep `test_default_confidence_low`, `test_sap_hana_bucket`, `test_email_bucket`, `test_ddve_bucket_nutanix`, `test_powerflex_routes_to_containers` as-is. In `test_v900_large_databearing_takes_unknown_volume`, the size-reroute still applies (now to `semantic`/`default` confidence) — leave assertions, they remain valid.

- [ ] **Step 3: Run the baseline locally (the merge gate)**

Run: `.venv/bin/pytest tests/test_real_customer_baseline.py -v`
Expected (on a machine with the customer file): all PASS. If `test_unknown_rate_not_regressed` fails, the semantic threshold is too high or exemplars too sparse — proceed to Task 11 (tuning) and/or expand exemplars, then re-run. The `300` ceiling is the tunable target; adjust only with a documented rationale in the test docstring.

- [ ] **Step 4: Commit**

```bash
rtk git add tests/test_real_customer_baseline.py
rtk git commit -m "test(baseline): adapt customer regression to semantic cascade

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Threshold tuning harness

**Files:**
- Create: `scripts/tune_semantic_thresholds.py`

- [ ] **Step 1: Write the harness**

```python
# scripts/tune_semantic_thresholds.py
"""Tune semantic-router per-route thresholds against the real-customer baseline.

Dev/CI only — NOT imported at runtime. Reads the customer RVTools file
(if present), labels each VM with the override registry as ground truth, fits
the SemanticRouter thresholds on the unmatched remainder, and prints the
resulting per-route thresholds to paste into SemanticConfig / exemplars.

Usage:  rtk python scripts/tune_semantic_thresholds.py
"""

from __future__ import annotations

from pathlib import Path

from store_predict.pipeline.classification import RuleRegistry, build_override_rules
from store_predict.pipeline.parsers.rvtools import parse_rvtools
from store_predict.pipeline.semantic_classifier import SemanticClassifier, _route_name
from store_predict.services.semantic_config import SemanticConfig

CUSTOMER_FILE = Path(
    "/Users/fjacquet/Library/CloudStorage/OneDrive-Home/20260430_1400_allvCenters.xlsx",
)


def main() -> None:
    if not CUSTOMER_FILE.exists():
        print(f"Customer file not present: {CUSTOMER_FILE} — cannot tune.")
        return
    df = parse_rvtools(CUSTOMER_FILE)
    df = df[df["is_powered_on"]].reset_index(drop=True)
    registry = RuleRegistry(build_override_rules())

    x: list[str] = []
    y: list[str | None] = []
    for _, row in df.iterrows():
        name = str(row.get("vm_name") or "")
        os_name = str(row.get("os_name") or "")
        verdict = registry.classify(name, os_name)
        text = f"{name} {os_name}".strip()
        if not text:
            continue
        if verdict.confidence == "rule_match":
            x.append(text)
            y.append(_route_name(verdict.category, verdict.subcategory))
        else:
            x.append(text)
            y.append(None)  # unmatched -> should not force any route

    sem = SemanticClassifier(config=SemanticConfig())
    print("Before:", sem._router.get_thresholds())  # noqa: SLF001
    print("Accuracy before:", sem._router.evaluate(X=x, y=y))  # noqa: SLF001
    sem._router.fit(X=x, y=y, max_iter=500)  # noqa: SLF001
    print("After:", sem._router.get_thresholds())  # noqa: SLF001
    print("Accuracy after:", sem._router.evaluate(X=x, y=y))  # noqa: SLF001


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it (only meaningful with the customer file present)**

Run: `.venv/bin/python scripts/tune_semantic_thresholds.py`
Expected: prints before/after thresholds and accuracy. Record the global/per-route thresholds; update `SemanticConfig.score_threshold` default (and document any per-route overrides) accordingly. If the file is absent it prints a notice and exits 0.

- [ ] **Step 3: Commit**

```bash
rtk git add scripts/tune_semantic_thresholds.py
rtk git commit -m "chore(semantic): add threshold tuning harness

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: Version bump, ADRs, CHANGELOG, docs

**Files:**
- Modify: `pyproject.toml:7` (version)
- Create: `docs/adr/082-…085-….md`
- Modify: `docs/adr/index.md`, `CHANGELOG.md`
- Create: `docs/research/semantic-classifier.md`

- [ ] **Step 1: Bump the version**

In `pyproject.toml`: `version = "10.0.0"`.

- [ ] **Step 2: Write the four ADRs**

Create each file following the existing ADR format (open `docs/adr/081-customer-app-classification-rules.md` first with `rtk read` to copy the heading/structure). Content summaries:

- `082-semantic-router-primary-classifier.md` — Decision: semantic-router (FastEmbed) is the primary classifier; deterministic rules demoted to `build_override_rules()` (priority<900). Context: regex list became unmaintainable; LLM flaky/slow. Consequences: example-driven, offline, explainable via recorded score.
- `083-fastembed-offline-encoder.md` — Decision: `FastEmbedEncoder(BAAI/bge-small-en-v1.5)` baked into the Docker image. Alternatives weighed: sentence-transformers (torch bloat), OllamaEncoder (runtime dep). Consequences: ~130 MB image cost, fully offline, deterministic.
- `084-retire-llm-fallback-dormant.md` — Decision: remove the LLM tier from the active pipeline but keep `llm_classifier.py` dormant (unwired, tests retained). Consequences: simpler runtime; re-enable is a wiring change.
- `085-curated-self-learning-exemplars.md` — Decision: curated `classification_exemplars.yaml` + in-memory same-file self-learning from override hits; never persisted. Consequences: per-file adaptivity, deterministic per input, no customer data committed.

- [ ] **Step 3: Add the ADRs to the index**

In `docs/adr/index.md`, add entries 082–085 following the existing list format.

- [ ] **Step 4: Add a CHANGELOG entry**

At the top of `CHANGELOG.md`, add a `## [10.0.0]` section (follow the existing style) describing: semantic-router primary classifier, FastEmbed offline encoder, rules demoted to overrides, LLM tier retired (dormant), new `SEMANTIC_*` config, curated exemplars + self-learning. Mark **BREAKING**: classifier behavior and removal of LLM from the active path.

- [ ] **Step 5: Write the research page**

Create `docs/research/semantic-classifier.md` summarizing the design (link the spec), the cascade diagram, encoder choice rationale, and tuning workflow. Reuse the spec content.

- [ ] **Step 6: Build docs to verify**

Run: `rtk mkdocs build`
Expected: builds with no broken-link/reference errors for the new pages.

- [ ] **Step 7: Commit**

```bash
rtk git add pyproject.toml docs/adr/ CHANGELOG.md docs/research/semantic-classifier.md
rtk git commit -m "docs: v10.0.0 semantic classifier ADRs, changelog, research

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Full quality gate

**Files:** none (verification only)

- [ ] **Step 1: Lint + type-check the whole tree**

Run: `rtk ruff check . && rtk ruff format --check . && rtk mypy src/`
Expected: clean. Fix any finding (read the file only to fix, per the CLI-linters-first convention).

- [ ] **Step 2: Run the full test suite (including slow)**

Run: `.venv/bin/pytest -m "slow or not slow" --cov=store_predict`
Expected: all pass; `test_llm_classifier.py` still green (dormant module intact); coverage not regressed below the prior threshold.

- [ ] **Step 3: Run a Semgrep scan on the new modules**

Use the `semgrep_scan` MCP tool on `src/store_predict/pipeline/semantic_classifier.py`, `src/store_predict/services/semantic_config.py`, and the modified `classification.py` / `upload.py`.
Expected: no new findings. Address any that appear.

- [ ] **Step 4: Final commit (if any fixes were needed)**

```bash
rtk git add -A
rtk git commit -m "chore: quality-gate fixes for semantic classifier

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review Notes (for the implementer)

- **Spec §2 cascade** → Tasks 4, 5, 6 (semantic tier, overrides, integration). ✔
- **Spec §3 modules** → Tasks 2 (config), 3 (exemplars), 4 (classifier), 6 (classification.py), 8 (upload.py), 9 (Dockerfile), keep-dormant honored in Task 8. ✔
- **Spec §4 confidence/provenance** → Task 6 produces `override` / `semantic:<route> (score)` / `default`. ✔
- **Spec §5 lifecycle + self-learning** → Task 4 (cached encoder, per-instance router, `add_learned`) + Task 6 (same-file seeding). Concurrency refinement (per-upload instance) documented in plan header & Task 4. ✔
- **Spec §6 tuning** → Task 11. ✔
- **Spec §7 error handling/security** → Task 6 (per-row try/except → default; no VM-name logging) + Task 4 (no query logging). ✔
- **Spec §8 testing/baseline gate** → Tasks 4, 6, 10, 13. ✔
- **Spec §9 versioning/ADRs/docs** → Task 12. ✔
- **Spec §10 risks** → image size (Task 9), accuracy/tuning (Tasks 10–11), CI time (`slow` marker, Task 4). ✔

**Known follow-ups to confirm during execution (not blockers):**
1. `RouteChoice.similarity_score` attribute name — verify in Task 4 Step 4; fallback path documented.
2. FastEmbed runtime user/cache-dir writability in Docker — verify in Task 9.
3. The `300` Unknown-rate ceiling in Task 10 is a target; tune in Tasks 11/3 and document if changed.
