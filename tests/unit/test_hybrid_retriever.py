from calliope.retrieval.hybrid import fuse_ranked_results


def test_fuse_ranked_results_combines_vector_and_lexical_rankings() -> None:
    vector_ids = ["chunk_a", "chunk_b", "chunk_c"]
    lexical_ids = ["chunk_c", "chunk_a"]

    hits = fuse_ranked_results(vector_ids, lexical_ids, k=60)

    assert hits[0].chunk_id == "chunk_a"
    assert hits[0].score > hits[-1].score
