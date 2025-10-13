"""Pipeline complet Markdown → PDF basé sur LaTeX."""

from __future__ import annotations

import re
import shutil
import tempfile
from datetime import datetime
from contextlib import ExitStack
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .config import ConversionOptions, DocumentMetadata
from .latex_engine import LatexCompiler
from .latex_template import TemplateRenderer
from .markdown_preprocessor import MarkdownPreprocessor
from .mermaid import MermaidRenderer
from .plantuml import PlantUMLRenderer
from .pandoc import PandocConverter
from .remote_images import RemoteImageDownloader
from .versioning import VersionManager


class MarkdownPDFBuilder:
    """Coordonne la conversion Markdown → PDF en passant par LaTeX."""

    def __init__(self, options: ConversionOptions) -> None:
        self._options = options
        self._mermaid_renderer = MermaidRenderer(options.mermaid) if options.mermaid.enabled else None
        self._plantuml_renderer = PlantUMLRenderer(options.plantuml) if options.plantuml.enabled else None
        self._remote_image_downloader = (
            RemoteImageDownloader(options.remote_images) if options.remote_images.enabled else None
        )
        self._preprocessor = MarkdownPreprocessor(
            self._mermaid_renderer,
            self._plantuml_renderer,
            self._remote_image_downloader,
        )
        self._pandoc = PandocConverter(options.pandoc)
        self._template = TemplateRenderer(options.template)
        self._compiler = LatexCompiler(options.latex)

    def convert(
        self,
        markdown_path: Path,
        output_path: Optional[Path] = None,
        *,
        version_note: Optional[str] = None,
    ) -> Path:
        markdown_path = markdown_path.resolve()
        return self._convert_documents([markdown_path], output_path, version_note=version_note)

    def convert_many(
        self,
        markdown_paths: Sequence[Path],
        output_path: Optional[Path] = None,
        *,
        version_note: Optional[str] = None,
    ) -> Path:
        resolved_paths = [path.resolve() for path in markdown_paths]
        if not resolved_paths:
            raise ValueError("Aucun fichier Markdown fourni pour la conversion groupée.")
        return self._convert_documents(resolved_paths, output_path, version_note=version_note)

    def _convert_documents(
        self,
        markdown_paths: Sequence[Path],
        output_path: Optional[Path],
        *,
        version_note: Optional[str],
    ) -> Path:
        output_dir = self._options.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            if len(markdown_paths) == 1:
                stem = markdown_paths[0].stem
            else:
                stem = markdown_paths[0].parent.name or markdown_paths[0].stem
            output_path = output_dir / f"{stem}.pdf"
        output_path = output_path.resolve()

        version_manager = VersionManager(output_dir)
        history_entries = version_manager.history_for(output_path.name)
        bootstrap_entry = None
        if not version_manager.version_file_exists and output_path.exists():
            bootstrap_entry = version_manager.build_entry_from_existing_pdf(output_path)
            if bootstrap_entry:
                history_entries = [*history_entries, bootstrap_entry]

        new_version_entry = None
        version_history_context: list[dict[str, object]] = []

        with ExitStack() as stack:
            if self._options.keep_temp_dir:
                temp_dir_path = Path(tempfile.mkdtemp(prefix="markdown_pdf_"))
            else:
                temp_dir = stack.enter_context(tempfile.TemporaryDirectory(prefix="markdown_pdf_"))
                temp_dir_path = Path(temp_dir)

            combined_markdown_parts: list[str] = []
            combined_front_matter: dict = {}

            for index, markdown_path in enumerate(markdown_paths):
                markdown_text = markdown_path.read_text(encoding="utf-8")
                preprocess = self._preprocessor.run(
                    markdown_text,
                    temp_dir_path,
                    f"{markdown_path.stem}-{index:03d}" if len(markdown_paths) > 1 else markdown_path.stem,
                )

                part = preprocess.markdown
                if part.strip():
                    combined_markdown_parts.append(part)

                if isinstance(preprocess.front_matter, dict):
                    combined_front_matter.update(preprocess.front_matter)

            processed_md = temp_dir_path / "document.md"
            separator = "\n\n\\newpage\n\n"
            processed_md.write_text(separator.join(combined_markdown_parts), encoding="utf-8")

            resource_paths: list[Path] = [temp_dir_path]
            resource_paths.extend(self._iter_resource_paths(markdown_paths))
            latex_body = self._pandoc.convert_to_latex(processed_md, resource_paths=resource_paths)
            latex_body = self._sanitize_latex(latex_body)
            toc_entries = self._extract_toc_entries(latex_body)
            if not self._options.include_toc:
                toc_entries = []

            metadata = self._resolve_metadata(combined_front_matter, markdown_paths[0].parent)
            preamble_extra = (
                combined_front_matter.get("preamble") if isinstance(combined_front_matter, dict) else None
            )

            timestamp = datetime.now()
            next_version_number = history_entries[-1].version + 1 if history_entries else 1
            new_version_entry = version_manager.build_entry(
                version=next_version_number,
                timestamp=timestamp,
                filename=output_path.name,
                author=metadata.author,
                note=version_note,
            )
            version_history_for_template = [*history_entries, new_version_entry]
            version_history_context = [entry.as_dict() for entry in version_history_for_template]

            tex_content = self._template.render(
                body_latex=latex_body,
                metadata=metadata,
                extra_context={
                    "front_matter": combined_front_matter,
                    "preamble_extra": preamble_extra,
                    "toc_entries": toc_entries,
                    "show_cover": self._options.include_cover,
                    "show_toc": self._options.include_toc,
                    "version_history": version_history_context,
                },
            )

            tex_file = temp_dir_path / "document.tex"
            tex_file.write_text(tex_content, encoding="utf-8")

            search_paths = [temp_dir_path]
            search_paths.extend(self._iter_resource_paths(markdown_paths))
            pdf_path = self._compiler.compile(tex_file, search_paths=search_paths)

            shutil.copy2(pdf_path, output_path)

        if new_version_entry:
            version_manager.append_entries([new_version_entry], bootstrap_entry=bootstrap_entry)

        return output_path

    @staticmethod
    def _iter_resource_paths(markdown_paths: Iterable[Path]) -> list[Path]:
        seen: set[Path] = set()
        paths: list[Path] = []
        for markdown_path in markdown_paths:
            parent = markdown_path.parent
            if parent not in seen:
                seen.add(parent)
                paths.append(parent)
        return paths

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
    def _sanitize_latex(latex_body: str) -> str:
        """Nettoie certaines séquences LaTeX problématiques générées par pandoc."""

        latex_body = re.sub(r"^\s*\\\*?\s*$\n?", "", latex_body, flags=re.MULTILINE)
        latex_body = re.sub(r"\\\*?[ \t]*(?=\n\s*\\end\{)", "", latex_body)
        return latex_body

    @staticmethod
    def _extract_toc_entries(latex_body: str) -> list[dict[str, object]]:
        """Récupère les sections pour alimenter une table des matières personnalisée."""

        pattern = re.compile(
            r"\\hypertarget\{(?P<target>[^}]+)\}\{%\s*\\(?P<command>section|subsection|subsubsection|paragraph|subparagraph)\{(?P<title>.*?)\}\\label\{(?P<label>[^}]+)\}\}",
            flags=re.DOTALL,
        )
        level_map = {
            "section": 1,
            "subsection": 2,
            "subsubsection": 3,
            "paragraph": 4,
            "subparagraph": 5,
        }
        entries: list[dict[str, object]] = []
        for match in pattern.finditer(latex_body):
            command = match.group("command")
            level = level_map.get(command)
            if level is None:
                continue
            title = match.group("title").replace("\n", " ").strip()
            entries.append(
                {
                    "level": level,
                    "title": title,
                    "target": match.group("target"),
                    "label": match.group("label"),
                }
            )
        return entries
