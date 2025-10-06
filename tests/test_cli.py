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
