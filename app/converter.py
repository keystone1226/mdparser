from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown

from .config import settings
from .llm import build_fabrix_client


@dataclass
class ConversionResult:
    markdown: str
    llm_used: bool


_converter_cache: dict[bool, MarkItDown] = {}


def _get_converter(use_llm: bool) -> MarkItDown:
    if use_llm not in _converter_cache:
        if use_llm:
            client = build_fabrix_client()
            _converter_cache[use_llm] = MarkItDown(
                enable_plugins=False,
                llm_client=client,
                llm_model=settings.fabrix_model_name,
            )
        else:
            _converter_cache[use_llm] = MarkItDown(enable_plugins=False)
    return _converter_cache[use_llm]


def reset_converter_cache() -> None:
    _converter_cache.clear()


def convert_file(path: Path) -> ConversionResult:
    use_llm = settings.llm_enabled
    converter = _get_converter(use_llm)
    result = converter.convert(str(path))
    return ConversionResult(markdown=result.text_content or "", llm_used=use_llm)
