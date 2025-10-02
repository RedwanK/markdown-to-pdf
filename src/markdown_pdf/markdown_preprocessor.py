"""Pré-traitement du Markdown : front matter + diagrammes Mermaid."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

from .mermaid import MermaidRenderer, MermaidRenderingError

_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class PreprocessResult:
    markdown: str
    front_matter: dict
    assets: List[Path]


class MarkdownPreprocessor:
    def __init__(self, mermaid_renderer: Optional[MermaidRenderer] = None) -> None:
        self._mermaid_renderer = mermaid_renderer

    def run(self, markdown_text: str, work_dir: Path, doc_stem: str) -> PreprocessResult:
        front_matter, content = self._extract_front_matter(markdown_text)
        processed, assets = self._render_mermaid_blocks(content, work_dir, doc_stem)
        return PreprocessResult(markdown=processed, front_matter=front_matter, assets=assets)

    @staticmethod
    def _extract_front_matter(markdown_text: str) -> Tuple[dict, str]:
        match = _FRONT_MATTER_PATTERN.match(markdown_text)
        if not match:
            return {}, markdown_text

        raw_front = match.group(1)
        try:
            data = yaml.safe_load(raw_front) or {}
            if not isinstance(data, dict):
                data = {}
        except yaml.YAMLError:
            data = {}

        content = markdown_text[match.end() :]
        return data, content

    def _render_mermaid_blocks(self, markdown_text: str, work_dir: Path, doc_stem: str) -> Tuple[str, List[Path]]:
        if not self._mermaid_renderer or not self._mermaid_renderer.enabled:
            return markdown_text, []

        assets: List[Path] = []
        output_dir = work_dir / "diagrams"
        counter = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal counter
            diagram_source = match.group(1)
            stem = f"{doc_stem}-{counter:03d}"
            counter += 1
            try:
                asset_path = self._mermaid_renderer.render(diagram_source, output_dir, stem)
            except MermaidRenderingError as exc:
                return f"```mermaid\n{diagram_source}\n```\n\n> Rendu Mermaid indisponible: {exc}\n"
            assets.append(asset_path)
            rel_path = asset_path.relative_to(work_dir)
            return f"![Diagramme Mermaid]({rel_path.as_posix()})"

        updated = _MERMAID_PATTERN.sub(replace, markdown_text)
        return updated, assets
