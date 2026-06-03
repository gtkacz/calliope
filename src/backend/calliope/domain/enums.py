from enum import StrEnum


class CanonPolicy(StrEnum):
    STRICT_CANON = "strict_canon"
    CANON_PLUS_INFERENCE = "canon_plus_inference"
    CREATIVE_BUT_CONSISTENT = "creative_but_consistent"


class ProfileKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    # Routes chat through Ollama's native /api/chat so num_ctx and the min_p /
    # repeat_penalty sampling knobs take effect; Ollama's OpenAI-compatible /v1
    # endpoint silently drops all three.
    OLLAMA = "ollama"
    # Sends the repetition penalty under KoboldCpp's native rep_pen name because
    # its OpenAI-compatible endpoint silently ignores repetition_penalty, which
    # would otherwise leave repetition unconstrained.
    KOBOLDCPP = "koboldcpp"


class ProfileCapability(StrEnum):
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    RERANK = "rerank"
    STREAMING = "streaming"


class EditMode(StrEnum):
    APPEND = "append"
    REWRITE = "rewrite"
