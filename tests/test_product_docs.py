"""Documentation integrity: links, images and API reference stay in sync with code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.main import app

BASE_DIR = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = [BASE_DIR / "README.md", *sorted((BASE_DIR / "docs").glob("*.md"))]
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")


@pytest.mark.parametrize("markdown_file", MARKDOWN_FILES, ids=lambda path: path.name)
def test_relative_links_and_images_exist(markdown_file: Path) -> None:
    text = markdown_file.read_text(encoding="utf-8")
    for target in LINK_PATTERN.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        assert (markdown_file.parent / target).exists(), f"{markdown_file.name}: {target}"


def test_api_reference_covers_every_route() -> None:
    api_doc = (BASE_DIR / "docs" / "api.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^### (?:GET|POST|PUT|PATCH|DELETE) (\S+)", api_doc, re.M))
    documented = {re.sub(r"\{[^}]+\}", "{}", path) for path in documented}

    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith(("/docs", "/openapi", "/redoc")) or not path:
            continue
        assert re.sub(r"\{[^}]+\}", "{}", path) in documented, path
