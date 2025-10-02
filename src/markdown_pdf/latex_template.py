"""Gestion du rendu du template LaTeX via Jinja."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template

from .config import DocumentMetadata, TemplateConfig
from .latex_utils import latex_escape


def _build_environment(template_path: Path) -> Environment:
    loader = FileSystemLoader(str(template_path.parent))
    env = Environment(loader=loader, autoescape=False, trim_blocks=True, lstrip_blocks=True)
    env.filters["latex_escape"] = latex_escape
    return env


class TemplateRenderer:
    def __init__(self, config: TemplateConfig) -> None:
        self._config = config
        self._env = _build_environment(config.template_path)
        self._template: Template | None = None

    def _get_template(self) -> Template:
        if self._template is None:
            self._template = self._env.get_template(self._config.template_path.name)
        return self._template

    def render(
        self,
        body_latex: str,
        metadata: DocumentMetadata,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        template = self._get_template()
        metadata_ctx = metadata.as_template_context()
        if metadata.logo_path:
            metadata_ctx["logo_path"] = metadata.logo_path.resolve().as_posix()

        preamble_parts: list[str] = []
        if self._config.preamble_path:
            preamble_parts.append(self._config.preamble_path.read_text(encoding="utf-8"))
        if self._config.extra_preamble:
            preamble_parts.append(self._config.extra_preamble)

        

        context_extra: Dict[str, Any] = {}
        if extra_context:
            context_extra = dict(extra_context)
            preamble_extra = context_extra.pop("preamble_extra", None)
            if preamble_extra:
                preamble_parts.append(preamble_extra)

        context: Dict[str, Any] = {
            "body": body_latex,
            "metadata": metadata_ctx,
            "preamble": "\n".join(preamble_parts) if preamble_parts else None,
        }
        if context_extra:
            context.update(context_extra)
        return template.render(**context)
