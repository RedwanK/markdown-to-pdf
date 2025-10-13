from pathlib import Path

from typer.testing import CliRunner

from markdown_pdf.cli import app


runner = CliRunner()


def test_init_metadata_creates_file(tmp_path: Path):
    target = tmp_path / "metadata.yaml"
    result = runner.invoke(app, ["init-metadata", "--output", str(target)])

    assert result.exit_code == 0
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "Nom du document" in content
    assert content.startswith("# Metadata template")


def test_init_metadata_refuses_overwrite(tmp_path: Path):
    target = tmp_path / "metadata.yaml"
    target.write_text("existing", encoding="utf-8")

    result = runner.invoke(app, ["init-metadata", "--output", str(target)])

    assert result.exit_code != 0
    assert target.read_text(encoding="utf-8") == "existing"


def test_convert_accepts_nested_metadata_section(tmp_path: Path, monkeypatch):
    markdown_file = tmp_path / "doc.md"
    markdown_file.write_text("# Demo", encoding="utf-8")

    metadata_file = tmp_path / "meta.yaml"
    metadata_file.write_text(
        (
            "metadata:\n"
            "  title_font: Custom Title\n"
            "  body_font: Custom Body\n"
            "  extra:\n"
            "    subtitle: Nested subtitle\n"
            "company: Example Corp\n"
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    class DummyBuilder:
        def __init__(self, options):
            captured["metadata"] = options.metadata

        def convert(self, markdown_file, output_path=None, version_note=None):
            pdf_path = tmp_path / "doc.pdf"
            pdf_path.write_bytes(b"PDF")
            captured["version_note"] = version_note
            return pdf_path

    monkeypatch.setattr("markdown_pdf.cli.MarkdownPDFBuilder", DummyBuilder)

    result = runner.invoke(
        app,
        [
            "convert",
            str(markdown_file),
            "--meta",
            str(metadata_file),
            "--output-dir",
            str(tmp_path),
            "--version-note",
            "Note CLI",
        ],
    )

    assert result.exit_code == 0
    metadata = captured["metadata"]
    assert metadata.title_font == "Custom Title"
    assert metadata.body_font == "Custom Body"
    assert metadata.extra and metadata.extra.get("subtitle") == "Nested subtitle"
    assert metadata.company == "Example Corp"
    assert captured["version_note"] == "Note CLI"
