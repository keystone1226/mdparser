from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import Lock
from typing import Optional

from .config import STORAGE_DIR, settings

_INDEX_PATH = STORAGE_DIR / "index.json"
_lock = Lock()


@dataclass
class ConversionRecord:
    id: str
    original_name: str
    markdown_name: str
    size_bytes: int
    created_at: float
    llm_used: bool
    status: str  # "ok" | "error"
    error: Optional[str] = None

    @property
    def markdown_path(self) -> Path:
        return STORAGE_DIR / f"{self.id}.md"

    def to_dict(self) -> dict:
        return asdict(self)


def _load_index() -> list[dict]:
    if not _INDEX_PATH.exists():
        return []
    try:
        with _INDEX_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(items: list[dict]) -> None:
    tmp = _INDEX_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    tmp.replace(_INDEX_PATH)


def _markdown_filename(original_name: str) -> str:
    stem = Path(original_name).stem or "converted"
    return f"{stem}.md"


def save_conversion(original_name: str, markdown: str, llm_used: bool) -> ConversionRecord:
    record_id = uuid.uuid4().hex
    record = ConversionRecord(
        id=record_id,
        original_name=original_name,
        markdown_name=_markdown_filename(original_name),
        size_bytes=len(markdown.encode("utf-8")),
        created_at=time.time(),
        llm_used=llm_used,
        status="ok",
    )
    record.markdown_path.write_text(markdown, encoding="utf-8")
    with _lock:
        items = _load_index()
        items.append(record.to_dict())
        _save_index(items)
    return record


def save_error(original_name: str, error: str) -> ConversionRecord:
    record = ConversionRecord(
        id=uuid.uuid4().hex,
        original_name=original_name,
        markdown_name=_markdown_filename(original_name),
        size_bytes=0,
        created_at=time.time(),
        llm_used=False,
        status="error",
        error=error,
    )
    with _lock:
        items = _load_index()
        items.append(record.to_dict())
        _save_index(items)
    return record


def list_records() -> list[ConversionRecord]:
    with _lock:
        items = _load_index()
    return [ConversionRecord(**item) for item in items]


def get_record(record_id: str) -> Optional[ConversionRecord]:
    for record in list_records():
        if record.id == record_id:
            return record
    return None


def read_markdown(record: ConversionRecord) -> str:
    if record.status != "ok":
        return ""
    if not record.markdown_path.exists():
        return ""
    return record.markdown_path.read_text(encoding="utf-8")


def cleanup_expired() -> int:
    if settings.retention_hours <= 0:
        return 0
    cutoff = time.time() - settings.retention_hours * 3600
    removed = 0
    with _lock:
        items = _load_index()
        kept: list[dict] = []
        for item in items:
            if item.get("created_at", 0) < cutoff:
                md_path = STORAGE_DIR / f"{item['id']}.md"
                if md_path.exists():
                    try:
                        md_path.unlink()
                    except OSError:
                        pass
                removed += 1
            else:
                kept.append(item)
        if removed:
            _save_index(kept)
    return removed
