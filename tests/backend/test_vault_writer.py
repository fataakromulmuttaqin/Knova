import hashlib
from pathlib import Path

from langchain_core.documents import Document
import pytest

from src import vault_writer
from src.chroma_store import ChromaVectorStore


@pytest.fixture
def vault(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_writer, "_VAULT_DIR", str(tmp_path))
    return tmp_path


def _upload_pair(name="report.pdf", text="Alpha content", source_id="src_abc12345"):
    docs = [Document(page_content=text, metadata={"source": name, "source_type": "upload"})]
    indexed = [{
        "source_id": source_id,
        "source_key": ChromaVectorStore.canonical_source(name, "upload", None),
        "source_name": name,
        "source_type": "upload",
        "chunk_count": 3,
        "pages": {"1"},
    }]
    return docs, indexed


def test_record_sources_writes_note_registry_and_index(vault):
    docs, indexed = _upload_pair()
    vault_writer.record_sources("user-1", docs, indexed)

    notes_dir = vault / "Knova"
    note = notes_dir / "report.pdf.md"
    assert note.exists()
    content = note.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert f'source_id: "{indexed[0]["source_id"]}"' in content
    assert "# report.pdf" in content
    assert "Alpha content" in content

    registry = (notes_dir / "index.json").read_text(encoding="utf-8")
    assert indexed[0]["source_id"] in registry
    index_note = (notes_dir / "Knova Index.md").read_text(encoding="utf-8")
    assert "[[report.pdf|report.pdf]]" in index_note


def test_reingest_updates_note_in_place(vault):
    docs, indexed = _upload_pair()
    vault_writer.record_sources("user-1", docs, indexed)
    note = vault / "Knova" / "report.pdf.md"

    docs2, indexed2 = _upload_pair(text="Alpha content v2")
    vault_writer.record_sources("user-1", docs2, indexed2)

    updated = note.read_text(encoding="utf-8")
    assert "Alpha content v2" in updated
    assert len(list((vault / "Knova").glob("*.md"))) == 2  # note + index note


def test_edited_note_is_preserved(vault):
    docs, indexed = _upload_pair()
    vault_writer.record_sources("user-1", docs, indexed)
    note = vault / "Knova" / "report.pdf.md"
    original = note.read_text(encoding="utf-8")
    note.write_text(original.replace("Alpha content", "Alpha content + my edits"), encoding="utf-8")

    docs2, indexed2 = _upload_pair(text="Alpha content v3")
    vault_writer.record_sources("user-1", docs2, indexed2)

    assert "my edits" in note.read_text(encoding="utf-8")
    reindexed = list((vault / "Knova").glob("report.pdf (re-indexed *).md"))
    assert len(reindexed) == 1
    assert "Alpha content v3" in reindexed[0].read_text(encoding="utf-8")


def test_url_source_matching_by_canonical_key(vault):
    url = "https://example.com/article"
    docs = [Document(page_content="Web text", metadata={"source": url, "source_type": "url", "title": "Example Article"})]
    indexed = [{
        "source_id": "src_url1111",
        "source_key": ChromaVectorStore.canonical_source(url, "url", None),
        "source_name": "Example Article",
        "source_type": "url",
        "chunk_count": 1,
        "pages": set(),
    }]
    vault_writer.record_sources("user-1", docs, indexed)

    note = vault / "Knova" / "Example Article.md"
    assert note.exists()
    assert "Origin: https://example.com/article" in note.read_text(encoding="utf-8")


def test_disabled_vault_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_writer, "_VAULT_DIR", "")
    docs, indexed = _upload_pair()
    assert vault_writer.record_sources("user-1", docs, indexed) is None
    assert not (tmp_path / "Knova").exists()


def test_failure_is_swallowed(vault, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk exploded")
    monkeypatch.setattr(vault_writer, "_write_notes", boom)
    docs, indexed = _upload_pair()
    vault_writer.record_sources("user-1", docs, indexed)  # must not raise


def test_unsafe_titles_are_sanitized(vault):
    docs = [Document(page_content="x", metadata={"source": 'a<b>:"c"/d|e?.pdf', "source_type": "upload"})]
    name = 'a<b>:"c"/d|e?.pdf'
    indexed = [{
        "source_id": "src_bad99",
        "source_key": ChromaVectorStore.canonical_source(name, "upload", None),
        "source_name": name,
        "source_type": "upload",
        "chunk_count": 1,
        "pages": set(),
    }]
    vault_writer.record_sources("user-1", docs, indexed)
    assert any(p.suffix == ".md" for p in (vault / "Knova").iterdir() if p.name != "Knova Index.md")


def test_body_hash_roundtrip(vault):
    docs, indexed = _upload_pair()
    vault_writer.record_sources("user-1", docs, indexed)
    note = vault / "Knova" / "report.pdf.md"
    text = note.read_text(encoding="utf-8")
    recorded = vault_writer._frontmatter_value(text, "knova_body_hash")
    _, body = vault_writer._split_frontmatter(text)
    assert recorded == hashlib.sha256(body.encode("utf-8")).hexdigest()
