from pathlib import Path

import pytest

from markdown_pdf.config import ConversionOptions, DocumentMetadata, MermaidConfig, TemplateConfig
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

    def fake_compile(self, tex_file: Path):
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
    )

    builder = MarkdownPDFBuilder(options)
    result = builder.convert(markdown_file)

    assert result.exists()
    assert result.read_bytes() == b"PDF"
