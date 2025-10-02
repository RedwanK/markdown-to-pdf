# Markdown PDF (LaTeX)

Outil CLI pour convertir des fichiers Markdown en PDF stylisés en s'appuyant sur LaTeX.

## Installation (développement)

```bash
pip install -e .[dev]
```

## Dépendances système

- [Pandoc](https://pandoc.org/) doit être présent dans le `PATH`.
- Une distribution LaTeX (ex. TeX Live, MikTeX) avec les packages `geometry`, `fontspec`, `fancyhdr`, `graphicx`, `hyperref`, `lastpage`, `listings`, `xcolor`.
- Pour les diagrammes Mermaid : `@mermaid-js/mermaid-cli` (`npm install -g @mermaid-js/mermaid-cli`).

## Usage rapide

```bash
markdown-pdf convert examples/sample.md --output-dir dist/ \
  --meta company="Mon Entreprise" --meta contact="contact@example.com"
```

### Personnalisation

- `--template` : fournir un template LaTeX Jinja personnalisé.
- `--preamble` : injecter un fichier LaTeX supplémentaire dans le préambule.
- `--metadata-file` / `--meta cle=valeur` : en-tête/pied personnalisables (logo, adresse, contact...).
- `--disable-mermaid` ou options `--mermaid-*` pour maîtriser le rendu des diagrammes (par défaut rendu en PNG, compatible XeLaTeX).
- `--mermaid-puppeteer-arg "--no-sandbox"` si Chromium n'a pas accès au sandbox (ex. serveurs verrouillés).

### Tests

```bash
pytest
```
