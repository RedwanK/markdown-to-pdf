"""Pipeline complet Markdown → PDF basé sur LaTeX."""

from __future__ import annotations

import re
import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Optional

from .config import ConversionOptions, DocumentMetadata
from .latex_engine import LatexCompiler
from .latex_template import TemplateRenderer
from .markdown_preprocessor import MarkdownPreprocessor
from .mermaid import MermaidRenderer
from .pandoc import PandocConverter


class MarkdownPDFBuilder:
    """Coordonne la conversion Markdown → PDF en passant par LaTeX."""

    def __init__(self, options: ConversionOptions) -> None:
        self._options = options
        self._mermaid_renderer = MermaidRenderer(options.mermaid) if options.mermaid.enabled else None
        self._preprocessor = MarkdownPreprocessor(self._mermaid_renderer)
        self._pandoc = PandocConverter(options.pandoc)
        self._template = TemplateRenderer(options.template)
        self._compiler = LatexCompiler(options.latex)

    def convert(self, markdown_path: Path, output_path: Optional[Path] = None) -> Path:
        markdown_path = markdown_path.resolve()
        output_dir = self._options.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            output_path = output_dir / f"{markdown_path.stem}.pdf"
        output_path = output_path.resolve()

        markdown_text = markdown_path.read_text(encoding="utf-8")

        with ExitStack() as stack:
            if self._options.keep_temp_dir:
                temp_dir_path = Path(tempfile.mkdtemp(prefix="markdown_pdf_"))
            else:
                temp_dir = stack.enter_context(tempfile.TemporaryDirectory(prefix="markdown_pdf_"))
                temp_dir_path = Path(temp_dir)

            preprocess = self._preprocessor.run(markdown_text, temp_dir_path, markdown_path.stem)

            processed_md = temp_dir_path / "document.md"
            processed_md.write_text(preprocess.markdown, encoding="utf-8")

            resource_paths = [temp_dir_path, markdown_path.parent]
            latex_body = self._pandoc.convert_to_latex(processed_md, resource_paths=resource_paths)
            latex_body = self._stabilize_figures(latex_body)

            metadata = self._resolve_metadata(preprocess.front_matter, markdown_path.parent)
            preamble_extra = preprocess.front_matter.get("preamble") if isinstance(preprocess.front_matter, dict) else None

            tex_content = self._template.render(
                body_latex=latex_body,
                metadata=metadata,
                extra_context={
                    "front_matter": preprocess.front_matter,
                    "preamble_extra": preamble_extra,
                },
            )

            tex_file = temp_dir_path / "document.tex"
            tex_file.write_text(tex_content, encoding="utf-8")

            search_paths = [temp_dir_path, markdown_path.parent]
            pdf_path = self._compiler.compile(tex_file, search_paths=search_paths)

            shutil.copy2(pdf_path, output_path)

        return output_path

    def _resolve_metadata(self, front_matter: dict, base_dir: Path) -> DocumentMetadata:
        base_data = self._options.metadata.model_dump()
        for key in DocumentMetadata.model_fields.keys():
            if key in front_matter:
                base_data[key] = front_matter[key]

        metadata_section = front_matter.get("metadata") if isinstance(front_matter, dict) else None
        if isinstance(metadata_section, dict):
            base_data.update(metadata_section)

        logo_value = base_data.get("logo_path")
        if logo_value:
            logo_path = Path(logo_value)
            if not logo_path.is_absolute():
                base_data["logo_path"] = (base_dir / logo_path).resolve()

        return DocumentMetadata(**base_data)

    @staticmethod
    def _stabilize_figures(latex_body: str) -> str:
        """Force les environnements figure/longtable à rester à l'emplacement courant."""

        figure_pattern = re.compile(r"\\begin\{figure\}(?!\[)")
        latex_body = figure_pattern.sub(r"\\begin{figure}[H]", latex_body)

        table_pattern = re.compile(r"\\begin\{longtable\}(?!\[)")
        latex_body = table_pattern.sub(r"\\begin{longtable}[H]", latex_body)

        return latex_body
