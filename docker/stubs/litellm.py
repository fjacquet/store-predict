"""Drop-in stub for ``litellm``, swapped into the runtime Docker image.

store-predict uses semantic-router only with ``FastEmbedEncoder`` (local ONNX
embeddings) and never instantiates a LiteLLM-backed encoder. semantic-router
nonetheless imports ``litellm`` *eagerly* via ``encoders/__init__.py``, so we
satisfy that import with the three symbols it touches — without shipping the
real ~61 MB package (and its CVE surface) in the runtime image.

The whole stub surface was derived by grepping every ``litellm.X`` reference in
the semantic-router package; only ``EmbeddingResponse``/``embedding``/
``aembedding`` are used, and none are exercised on the FastEmbed routing path.
If a LiteLLM encoder is ever wired up, the NotImplementedError makes the
omission loud rather than silent.

Source-level dependency metadata (uv.lock, SBOM) is intentionally left intact;
only the shipped image swaps this in. See docs/adr and Dockerfile.
"""

from typing import ClassVar

__version__ = "0.0.0+storepredict-stub"


class EmbeddingResponse:  # referenced only in isinstance()/annotations, never constructed
    data: ClassVar[list] = []


def embedding(*args: object, **kwargs: object) -> "EmbeddingResponse":
    raise NotImplementedError("litellm is stubbed out in store-predict; LiteLLM-backed encoders are unavailable.")


async def aembedding(*args: object, **kwargs: object) -> "EmbeddingResponse":
    raise NotImplementedError("litellm is stubbed out in store-predict; LiteLLM-backed encoders are unavailable.")
