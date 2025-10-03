# Blocs de code

Les extraits sont mis en forme via le package LaTeX `listings` avec fond gris et police monospace.

## Commandes shell

```bash
python -m venv .venv
source .venv/bin/activate
markdown-pdf convert docs/*.md --output-dir dist
```

## Code Python

```python
from pathlib import Path

from markdown_pdf.pipeline import MarkdownPDFBuilder

source = Path("notes.md")
builder = MarkdownPDFBuilder.from_defaults(output_dir=Path("dist"))
builder.convert(source)
```

## Code JSON

```json
{
  "title": "Rapport mensuel",
  "owner": "Product Ops",
  "tags": ["finance", "kpi", "reporting"],
  "published_at": "2025-01-31"
}
```

## Inline code

Utilisez des backticks simples pour insérer du code dans un paragraphe, par exemple `print("hello")`.
