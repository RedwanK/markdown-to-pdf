from pathlib import Path

from markdown_pdf.markdown_preprocessor import MarkdownPreprocessor


def test_front_matter_extraction(tmp_path: Path):
    markdown = """---\ntitle: Doc\n---\n\n# Titre\n"""
    preprocessor = MarkdownPreprocessor(mermaid_renderer=None)
    result = preprocessor.run(markdown, tmp_path, "doc")
    assert result.front_matter["title"] == "Doc"
    assert result.markdown.strip() == "# Titre"


def test_mermaid_replaced_when_renderer_absent(tmp_path: Path):
    markdown = """```mermaid\ngraph TD;A-->B;\n```"""
    preprocessor = MarkdownPreprocessor(mermaid_renderer=None)
    result = preprocessor.run(markdown, tmp_path, "doc")
    assert "mermaid" in result.markdown


def test_plantuml_preserved_when_renderer_absent(tmp_path: Path):
    markdown = """```plantuml\nAlice -> Bob\n```"""
    preprocessor = MarkdownPreprocessor(mermaid_renderer=None)
    result = preprocessor.run(markdown, tmp_path, "doc")
    assert "plantuml" in result.markdown


def test_plantuml_replaced_with_renderer(tmp_path: Path):
    class DummyRenderer:
        enabled = True

        def render(self, diagram: str, output_dir: Path, stem: str) -> Path:
            output_dir.mkdir(parents=True, exist_ok=True)
            asset_path = output_dir / f"{stem}.png"
            asset_path.write_bytes(b"PNG")
            return asset_path

    preprocessor = MarkdownPreprocessor(mermaid_renderer=None, plantuml_renderer=DummyRenderer())
    markdown = """```plantuml\nAlice -> Bob\n```"""
    result = preprocessor.run(markdown, tmp_path, "doc")

    assert "\\includegraphics" in result.markdown
    assert "detokenize" in result.markdown
    assert result.assets


def test_mermaid_replaced_with_renderer(tmp_path: Path):
    class DummyRenderer:
        enabled = True

        def render(self, diagram: str, output_dir: Path, stem: str) -> Path:
            output_dir.mkdir(parents=True, exist_ok=True)
            asset_path = output_dir / f"{stem}.png"
            asset_path.write_bytes(b"PNG")
            return asset_path

    preprocessor = MarkdownPreprocessor(mermaid_renderer=DummyRenderer())
    markdown = """```mermaid\ngraph TD;A-->B;\n```"""
    result = preprocessor.run(markdown, tmp_path, "doc")

    assert "\\includegraphics" in result.markdown
    assert result.assets
