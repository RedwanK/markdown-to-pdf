import re
from pathlib import Path

import pytest

from markdown_pdf.config import (
    ConversionOptions,
    DocumentMetadata,
    MermaidConfig,
    PlantUMLConfig,
    TemplateConfig,
)
from markdown_pdf.config import PandocConfig
from markdown_pdf.pandoc import PandocConverter
from markdown_pdf.pipeline import MarkdownPDFBuilder


@pytest.fixture()
def markdown_file(tmp_path: Path) -> Path:
    md = tmp_path / "sample.md"
    md.write_text(
        """---\ncompany: Test Corp\nmetadata:\n  address: Rue test\n---\n\n# Bonjour\n""",
        encoding="utf-8",
    )
    return md


def test_pipeline_converts_using_mocks(monkeypatch, tmp_path: Path, markdown_file: Path):
    def fake_pandoc_convert(self, markdown_file, resource_paths=()):
        return "\\section{Bonjour}"

    def fake_compile(self, tex_file: Path, search_paths=()):
        pdf_path = tex_file.with_suffix(".pdf")
        pdf_path.write_bytes(b"PDF")
        return pdf_path

    monkeypatch.setattr("markdown_pdf.pandoc.PandocConverter.convert_to_latex", fake_pandoc_convert)
    monkeypatch.setattr("markdown_pdf.latex_engine.LatexCompiler.compile", fake_compile)

    options = ConversionOptions(
        output_dir=tmp_path / "out",
        template=TemplateConfig(),
        metadata=DocumentMetadata(title="Titre"),
        mermaid=MermaidConfig(enabled=False),
        plantuml=PlantUMLConfig(enabled=False),
    )

    builder = MarkdownPDFBuilder(options)
    result = builder.convert(markdown_file)

    assert result.exists()
    assert result.read_bytes() == b"PDF"

    version_file = options.output_dir / ".version"
    assert version_file.exists()
    lines = version_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parts = lines[0].split("|")
    assert parts[0] == "1"
    assert re.match(r"\d{4}-\d{2}-\d{2}$", parts[1])
    assert re.match(r"\d{2}:\d{2}$", parts[2])
    assert parts[3] == ""
    assert parts[4] == "sample.pdf"
    assert parts[5] == ""


def test_pipeline_concatenate_directory(monkeypatch, tmp_path: Path):
    md1 = tmp_path / "part1.md"
    md1.write_text("# Partie 1", encoding="utf-8")
    md2 = tmp_path / "part2.md"
    md2.write_text("# Partie 2", encoding="utf-8")

    combined_markdown: dict[str, str] = {}

    def fake_pandoc_convert(self, markdown_file, resource_paths=()):
        combined_markdown["markdown"] = Path(markdown_file).read_text(encoding="utf-8")
        return "\\section{Combined}"

    def fake_compile(self, tex_file: Path, search_paths=()):
        pdf_path = tex_file.with_suffix(".pdf")
        pdf_path.write_bytes(b"PDF")
        return pdf_path

    monkeypatch.setattr("markdown_pdf.pandoc.PandocConverter.convert_to_latex", fake_pandoc_convert)
    monkeypatch.setattr("markdown_pdf.latex_engine.LatexCompiler.compile", fake_compile)

    options = ConversionOptions(
        output_dir=tmp_path / "out",
        template=TemplateConfig(),
        metadata=DocumentMetadata(title="Titre"),
        mermaid=MermaidConfig(enabled=False),
        plantuml=PlantUMLConfig(enabled=False),
    )

    builder = MarkdownPDFBuilder(options)
    result = builder.convert_many([md1, md2], output_path=tmp_path / "out" / "merged.pdf")

    assert result.exists()
    assert result.read_bytes() == b"PDF"
    assert combined_markdown["markdown"].count("\\newpage") == 1


def test_pandoc_parses_lists_without_blankline(tmp_path: Path):
    markdown = (
        "Composants\n"
        "- Application web\n"
        "- Broker MQTT\n"
    )

    md_path = tmp_path / "doc.md"
    md_path.write_text(markdown, encoding="utf-8")

    pandoc = PandocConverter(PandocConfig())
    latex = pandoc.convert_to_latex(md_path)

    assert "\\begin{itemize}" in latex
    assert latex.count("\\item") == 2


def test_pipeline_can_disable_cover_and_toc(monkeypatch, tmp_path: Path, markdown_file: Path):
    def fake_pandoc_convert(self, markdown_file, resource_paths=()):
        return "\\section{Bonjour}"

    captured: dict[str, object] = {}

    def fake_render(self, body_latex, metadata, extra_context=None):
        captured["extra_context"] = extra_context or {}
        return "\\documentclass{article}\\begin{document}Test\\end{document}"

    def fake_compile(self, tex_file: Path, search_paths=()):
        pdf_path = tex_file.with_suffix(".pdf")
        pdf_path.write_bytes(b"PDF")
        return pdf_path

    monkeypatch.setattr("markdown_pdf.pandoc.PandocConverter.convert_to_latex", fake_pandoc_convert)
    monkeypatch.setattr("markdown_pdf.latex_template.TemplateRenderer.render", fake_render)
    monkeypatch.setattr("markdown_pdf.latex_engine.LatexCompiler.compile", fake_compile)

    options = ConversionOptions(
        output_dir=tmp_path / "out",
        template=TemplateConfig(),
        metadata=DocumentMetadata(title="Titre"),
        mermaid=MermaidConfig(enabled=False),
        plantuml=PlantUMLConfig(enabled=False),
        include_cover=False,
        include_toc=False,
    )

    builder = MarkdownPDFBuilder(options)
    result = builder.convert(markdown_file)

    assert result.exists()
    ctx = captured["extra_context"]
    assert ctx["show_cover"] is False
    assert ctx["show_toc"] is False
    assert ctx["toc_entries"] == []
    history = ctx["version_history"]
    assert len(history) == 1
    assert history[0]["version"] == 1
    assert history[0]["filename"] == "sample.pdf"
    assert history[0]["note"] == ""


def test_pipeline_versioning_appends_entries(monkeypatch, tmp_path: Path, markdown_file: Path):
    def fake_pandoc_convert(self, markdown_file, resource_paths=()):
        return "\\section{Bonjour}"

    def fake_compile(self, tex_file: Path, search_paths=()):
        pdf_path = tex_file.with_suffix(".pdf")
        pdf_path.write_bytes(b"PDF")
        return pdf_path

    monkeypatch.setattr("markdown_pdf.pandoc.PandocConverter.convert_to_latex", fake_pandoc_convert)
    monkeypatch.setattr("markdown_pdf.latex_engine.LatexCompiler.compile", fake_compile)

    options = ConversionOptions(
        output_dir=tmp_path / "out",
        template=TemplateConfig(),
        metadata=DocumentMetadata(title="Titre", author="Alice"),
        mermaid=MermaidConfig(enabled=False),
        plantuml=PlantUMLConfig(enabled=False),
    )

    builder = MarkdownPDFBuilder(options)
    builder.convert(markdown_file, version_note="Initial import")
    builder.convert(markdown_file, version_note="Mise a jour")

    version_file = options.output_dir / ".version"
    lines = version_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first_parts = lines[0].split("|")
    second_parts = lines[1].split("|")
    assert first_parts[0] == "1"
    assert second_parts[0] == "2"
    assert first_parts[5] == "Initial import"
    assert second_parts[3] == "Alice"
    assert second_parts[4] == "sample.pdf"
    assert second_parts[5] == "Mise a jour"


def test_pipeline_bootstrap_version_file(monkeypatch, tmp_path: Path, markdown_file: Path):
    def fake_pandoc_convert(self, markdown_file, resource_paths=()):
        return "\\section{Bonjour}"

    def fake_compile(self, tex_file: Path, search_paths=()):
        pdf_path = tex_file.with_suffix(".pdf")
        pdf_path.write_bytes(b"PDF")
        return pdf_path

    monkeypatch.setattr("markdown_pdf.pandoc.PandocConverter.convert_to_latex", fake_pandoc_convert)
    monkeypatch.setattr("markdown_pdf.latex_engine.LatexCompiler.compile", fake_compile)

    options = ConversionOptions(
        output_dir=tmp_path / "out",
        template=TemplateConfig(),
        metadata=DocumentMetadata(title="Titre"),
        mermaid=MermaidConfig(enabled=False),
        plantuml=PlantUMLConfig(enabled=False),
    )

    builder = MarkdownPDFBuilder(options)
    builder.convert(markdown_file)

    version_file = options.output_dir / ".version"
    assert version_file.exists()
    version_file.unlink()
    existing_pdf = options.output_dir / "sample.pdf"
    assert existing_pdf.exists()

    builder.convert(markdown_file, version_note="Nouvelle compilation")

    lines = version_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first_parts = lines[0].split("|")
    second_parts = lines[1].split("|")
    assert first_parts[0] == "1"
    assert first_parts[4] == "sample.pdf"
    assert first_parts[5] == ""
    assert second_parts[0] == "2"
    assert second_parts[5] == "Nouvelle compilation"
