from calliope.domain.enums import CanonPolicy, ProfileCapability, ProfileKind
from calliope.domain.schemas import SourceReference, WorkspaceCreate


def test_workspace_create_defaults_globs() -> None:
    payload = WorkspaceCreate(name="World", root_path="/tmp/world")

    assert payload.include_globs == ["**/*.md", "**/*.markdown"]
    assert payload.exclude_globs == [".git/**", ".venv/**", "node_modules/**"]


def test_source_reference_contains_citation_fields() -> None:
    source = SourceReference(
        document_id="doc_1",
        chunk_id="chunk_1",
        path="characters/kaelen.md",
        heading="Biography > Exile",
        excerpt="After the Second Winter War",
        score=0.87,
    )

    assert source.score == 0.87
    assert "Exile" in source.heading


def test_enums_cover_mvp_values() -> None:
    assert CanonPolicy.STRICT_CANON == "strict_canon"
    assert CanonPolicy.CANON_PLUS_INFERENCE == "canon_plus_inference"
    assert CanonPolicy.CREATIVE_BUT_CONSISTENT == "creative_but_consistent"
    assert ProfileKind.OPENAI_COMPATIBLE == "openai_compatible"
    assert ProfileCapability.CHAT == "chat"
