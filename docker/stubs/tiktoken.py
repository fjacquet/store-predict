"""Drop-in stub for ``tiktoken``, swapped into the runtime Docker image.

semantic-router imports ``tiktoken`` eagerly (``encoders/openai.py``,
``encoders/bedrock.py``) but only calls it *inside* the OpenAI/Bedrock encoders,
which store-predict never uses (it routes via FastEmbed). There is no
module-level ``tiktoken.X`` use, so satisfying ``import tiktoken`` is enough —
no need to ship the real package.
"""

__version__ = "0.0.0+storepredict-stub"


def encoding_for_model(*args: object, **kwargs: object) -> object:
    raise NotImplementedError("tiktoken is stubbed out in store-predict.")


def get_encoding(*args: object, **kwargs: object) -> object:
    raise NotImplementedError("tiktoken is stubbed out in store-predict.")
