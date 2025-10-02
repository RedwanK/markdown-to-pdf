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
