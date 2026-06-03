from calliope.domain.constants import VERSION_STORE_DIRNAME
from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from calliope.domain.schemas import (
    ChatRequest,
    EditProposalRequest,
    SourceReference,
    WorkspaceCreate,
    WriteRequest,
)


def test_workspace_create_defaults_globs() -> None:
    payload = WorkspaceCreate(name="World", root_path="/tmp/world")

    assert payload.include_globs == ["**/*.md", "**/*.markdown"]
    assert payload.exclude_globs == [
        ".git/**",
        ".venv/**",
        "node_modules/**",
        f"{VERSION_STORE_DIRNAME}/**",
    ]
    # Per-workspace versioning is unset by default, inheriting the global flag.
    assert payload.versioning_enabled is None
    # Guidelines are unset by default — the workspace has no standing directive.
    assert payload.guidelines is None


def test_source_reference_contains_citation_fields() -> None:
    source = SourceReference(
        document_id="doc_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Biography > Exile",
        context="After the Second Winter War",
        score=0.87,
    )

    assert source.score == 0.87
    assert source.document_id == "doc_1"
    assert source.chunk_id == "chunk_1"
    assert source.path == "characters/kaelen.md"
    assert "Exile" in source.heading
    assert source.context == "After the Second Winter War"


def test_enums_cover_mvp_values() -> None:
    assert CanonPolicy.STRICT_CANON == "strict_canon"
    assert CanonPolicy.CANON_PLUS_INFERENCE == "canon_plus_inference"
    assert CanonPolicy.CREATIVE_BUT_CONSISTENT == "creative_but_consistent"
    assert ProfileKind.OPENAI_COMPATIBLE == "openai_compatible"
    assert ProfileCapability.CHAT == "chat"
    assert ProfileCapability.EMBEDDINGS == "embeddings"
    assert ProfileCapability.RERANK == "rerank"
    assert ProfileCapability.STREAMING == "streaming"


def test_generation_requests_apply_guidelines_by_default() -> None:
    assert ChatRequest(message="hi").apply_guidelines is True
    assert WriteRequest(message="hi").apply_guidelines is True
    assert EditProposalRequest(path="a.md", instruction="x").apply_guidelines is True
