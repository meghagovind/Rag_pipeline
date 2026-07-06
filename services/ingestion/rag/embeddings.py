"""Text-only embedding setup with optional vision integrations disabled."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def get_embed_model() -> Any:
    """Return the shared Hugging Face text embedding model.

    Transformers probes torchvision when it is installed, even though this
    pipeline only embeds text. A mismatched optional torchvision wheel should
    not prevent document ingestion, so its availability probe is disabled
    before SentenceTransformers is imported.
    """
    import transformers.utils as transformers_utils
    import transformers.utils.import_utils as import_utils

    vision_unavailable = lambda: False  # noqa: E731
    import_utils.is_torchvision_available = vision_unavailable
    transformers_utils.is_torchvision_available = vision_unavailable

    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    model_name = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    return HuggingFaceEmbedding(model_name=model_name)
