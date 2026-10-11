"""Mirror ingested sources into an Obsidian vault as markdown notes.

Every source that Knova indexes (file upload, URL, Google Drive) is also
written as a note under <OBSIDIAN_VAULT_DIR>/<KNOVA_VAULT_SUBDIR>/, together
with an auto-maintained index note. The vault becomes Knova's durable,
human-readable knowledge base; notes edited in Obsidian are never clobbered
by re-ingestion. The feature is off unless OBSIDIAN_VAULT_DIR is set, and a
vault failure must never fail ingestion itself.
"""
import hashlib
import json
import logging
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.chroma_store import ChromaVectorStore

log = logging.getLogger(__name__)

_VAULT_DIR = os.getenv("OBSIDIAN_VAULT_DIR", "").strip()
_NOTES_SUBDIR = os.getenv("KNOVA_VAULT_SUBDIR", "Knova").strip() or "Knova"
_INDEX_NOTE_NAME = "Knova Index.md"
_REGISTRY_NAME = "index.json"
_LOCK = threading.Lock()
_ILLEGAL_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def vault_enabled() -> bool:
    return bool(_VAULT_DIR)


def record_sources(user_id, documents, indexed):
    """Write one vault note per successfully indexed source.

    Called right after Chroma indexing in every ingestion path. Safe to call
    with vault mirroring disabled or on any error: it logs and returns.
    """
    if not _VAULT_DIR or not indexed:
        return
    try:
        with _LOCK:
            _write_notes(user_id, documents, indexed)
    except Exception:
        log.exception("Obsidian vault sync failed; ingestion result is unaffected")


def _notes_dir() -> Path:
    directory = Path(_VAULT_DIR).expanduser() / _NOTES_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _load_registry(directory: Path) -> dict:
    try:
        return json.loads((directory / _REGISTRY_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_registry(directory: Path, registry: dict) -> None:
    _atomic_write(directory / _REGISTRY_NAME, json.dumps(registry, indent=2, sort_keys=True))


def _atomic_write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _safe_stem(title: str) -> str:
    stem = _ILLEGAL_FS_CHARS.sub("-", str(title or "").strip())
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return stem[:80] or "untitled"


def _frontmatter_value(text: str, key: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    for line in text[3:end].splitlines():
        if line.strip().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def _split_frontmatter(text: str) -> tuple[str, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[: end + 4], text[end + 4 :].lstrip("\r\n")
    return "", text


def _group_documents(documents) -> dict:
    groups = defaultdict(list)
    for document in documents or []:
        meta = dict(getattr(document, "metadata", {}) or {})
        source = str(meta.get("source") or "").strip()
        if not source:
            continue
        source_type = str(meta.get("source_type") or "upload").lower()
        file_id = str(meta.get("file_id") or "") or None
        key = ChromaVectorStore.canonical_source(source, source_type, file_id)
        groups[key].append(document)
    return groups


def _note_body(item: dict, docs: list) -> str:
    title = str(item.get("source_name") or "").strip() or "Untitled source"
    source_type = str(item.get("source_type") or "upload").lower()
    origin = str((docs[0].metadata or {}).get("source") or item.get("source_key") or "")
    lines = [f"# {title}", ""]
    details = [
        f"Type: **{source_type}**",
        f"Indexed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Chunks: {item.get('chunk_count', '?')}",
    ]
    if origin:
        if source_type == "url":
            details.insert(0, f"Origin: {origin}")
        else:
            details.insert(0, f"Origin: `{origin}`")
    lines.extend(["> [!info] Indexed by Knova", *[f"> {line}" for line in details], ""])
    parts = [str(getattr(doc, "page_content", "") or "").strip() for doc in docs]
    parts = [part for part in parts if part]
    lines.append("\n\n---\n\n".join(parts) if parts else "_No extractable text._")
    return "\n".join(lines) + "\n"


def _compose_note(front: dict, body: str) -> str:
    front["knova_body_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    lines = ["---"]
    lines += [f"{key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, str) else value}"
              for key, value in front.items()]
    lines += ["---", ""]
    return "\n".join(lines) + body


def _write_notes(user_id, documents, indexed) -> None:
    directory = _notes_dir()
    registry = _load_registry(directory)
    groups = _group_documents(documents)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for item in indexed:
        source_key = str(item.get("source_key") or "")
        docs = groups.get(source_key)
        if docs is None and len(indexed) == 1 and len(groups) == 1:
            docs = next(iter(groups.values()))
        if not docs:
            continue

        source_id = str(item.get("source_id") or source_key)
        title = str(item.get("source_name") or "").strip() or source_id
        stem = _safe_stem(title)
        entry = registry.get(source_id)
        existing_path = directory / f"{entry['file']}" if entry and entry.get("file") else None
        if existing_path is None or not existing_path.exists():
            claimed = {str(e.get("file") or "") for e in registry.values()}
            if f"{stem}.md" in claimed or (directory / f"{stem}.md").exists():
                stem = f"{stem}-{source_id[-8:]}"
            existing_path = directory / f"{stem}.md"

        body = _note_body(item, docs)
        path = existing_path
        if path.exists():
            current = path.read_text(encoding="utf-8")
            previous_hash = _frontmatter_value(current, "knova_body_hash")
            _, current_body = _split_frontmatter(current)
            untouched = previous_hash is not None and previous_hash == hashlib.sha256(
                current_body.encode("utf-8")
            ).hexdigest()
            if not untouched:
                date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
                path = directory / f"{_safe_stem(title)} (re-indexed {date_tag}).md"
                log.info("Vault note %s was edited outside Knova; preserving it and writing %s", existing_path.name, path.name)

        front = {
            "knova": True,
            "source_id": source_id,
            "source_key": source_key,
            "source_type": str(item.get("source_type") or "upload"),
            "title": title,
            "origin": str((docs[0].metadata or {}).get("source") or ""),
            "user_id": str(user_id or ""),
            "indexed_at": stamp,
            "chunk_count": item.get("chunk_count", 0),
        }
        _atomic_write(path, _compose_note(front, body))
        registry[source_id] = {"file": path.name, "title": title, **{k: front[k] for k in ("source_key", "source_type", "chunk_count")}, "indexed_at": stamp}

    _save_registry(directory, registry)
    _write_index_note(directory, registry)


def _write_index_note(directory: Path, registry: dict) -> None:
    by_type = defaultdict(list)
    for source_id, entry in registry.items():
        by_type[entry.get("source_type", "upload")].append(entry)

    lines = ["# Knova Knowledge Index", "", "Every source indexed by Knova, mirrored into this vault automatically.", ""]
    for source_type in sorted(by_type):
        entries = sorted(by_type[source_type], key=lambda e: str(e.get("indexed_at") or ""), reverse=True)
        label = {"upload": "Uploaded documents", "url": "Web pages", "drive": "Google Drive documents"}.get(source_type, source_type)
        lines += [f"## {label} ({len(entries)})", ""]
        lines += [f"- [[{Path(e['file']).stem}|{e.get('title', e['file'])}]] — {e.get('chunk_count', '?')} chunks, indexed {str(e.get('indexed_at', ''))[:10]}" for e in entries]
        lines.append("")
    _atomic_write(directory / _INDEX_NOTE_NAME, "\n".join(lines))
