import math
from types import SimpleNamespace

from src.search import RAGSearch


def _row(score, distance, user_id="u1", source="doc.pdf", bm25=0.0):
    return {
        "score": score,
        "distance": distance,
        "bm25_score": bm25,
        "document": "chunk text",
        "metadata": {"user_id": user_id, "source": source, "source_id": "s1"},
    }


def _run(rows, top_k=5, user_id="u1"):
    fused = list(rows)
    fake = SimpleNamespace(
        _query_terms=lambda query: ["term"],
        _memory_retrieval_hint=lambda memory: "",
        vectorstore=SimpleNamespace(query=lambda *a, **k: list(rows)),
        _bm25_retrieve=lambda *a, **k: [],
        _rrf_fuse=lambda dense, sparse: list(fused),
        _rank_results=lambda query, fused_rows: list(fused_rows),
        _expand_to_parent_context=lambda ranked, top_k=5: list(ranked),
    )
    return RAGSearch._retrieve_for_answer(fake, "Isi pdf nya bahas apa", top_k, None, user_id=user_id)[0]


def test_generic_question_below_cutoff_still_returns_close_documents():
    rows = [_row(-4.20, 0.760), _row(-4.37, 0.810), _row(-4.49, 0.741), _row(-5.26, 0.714)]
    assert len(_run(rows)) == 3


def test_far_documents_still_report_no_relevant_documents():
    rows = [_row(-4.20, 0.91), _row(-5.30, 0.95), _row(-6.10, 0.97)]
    assert _run(rows) == []


def test_rows_above_the_cutoff_are_untouched():
    rows = [_row(12.05, 0.361), _row(3.04, 0.517), _row(-0.87, 0.642)]
    assert len(_run(rows)) == 3


def test_rescue_respects_the_requested_top_k():
    rows = [_row(-4.20, 0.70), _row(-4.30, 0.71), _row(-4.40, 0.72), _row(-4.50, 0.73)]
    assert len(_run(rows, top_k=1)) == 1
    assert len(_run(rows, top_k=2)) == 2


def test_rescue_drops_rows_from_other_users():
    rows = [_row(-4.20, 0.70), _row(-4.30, 0.71, user_id="someone-else")]
    result = _run(rows)
    assert all(row["metadata"]["user_id"] == "u1" for row in result)
