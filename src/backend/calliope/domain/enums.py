from enum import StrEnum


class CanonPolicy(StrEnum):
    STRICT_CANON = "strict_canon"
    CANON_PLUS_INFERENCE = "canon_plus_inference"
    CREATIVE_BUT_CONSISTENT = "creative_but_consistent"


class ProfileKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"


class ProfileCapability(StrEnum):
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    RERANK = "rerank"
    STREAMING = "streaming"


class EditMode(StrEnum):
    APPEND = "append"
    REWRITE = "rewrite"
