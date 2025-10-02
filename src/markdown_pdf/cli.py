"""Interface CLI pour la conversion Markdown → PDF via LaTeX."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import typer
import yaml

from .config import (
    ConversionOptions,
    DocumentMetadata,
    LatexEngineConfig,
    MermaidConfig,
    PandocConfig,
    TemplateConfig,
)
from .pipeline import MarkdownPDFBuilder

app = typer.Typer(help="Convertit des fichiers Markdown en PDF en s'appuyant sur LaTeX.")


def _parse_key_value(values: List[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise typer.BadParameter(f"Format attendu: cle=valeur (reçu: {raw})")
        key, value = raw.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _load_mapping_file(path: Optional[Path]) -> Dict[str, str]:
    if not path:
        return {}
    if not path.exists():
        raise typer.BadParameter(f"Fichier introuvable: {path}")
    content = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(content)
        else:
            data = yaml.safe_load(content)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise typer.BadParameter(f"Configuration invalide ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise typer.BadParameter(f"Le fichier {path} doit contenir un objet clé/valeur.")
    return data


@app.command()
def convert(
    sources: List[Path] = typer.Argument(..., exists=True, help="Markdown à convertir (fichiers ou dossiers)."),
    output_dir: Path = typer.Option(Path("dist"), "--output-dir", "-o", help="Répertoire de sortie."),
    template_path: Optional[Path] = typer.Option(None, "--template", help="Template LaTeX Jinja personnalisé."),
    preamble_path: Optional[Path] = typer.Option(None, "--preamble", help="Fichier LaTeX à injecter dans le préambule."),
    preamble_inline: Optional[str] = typer.Option(None, "--preamble-inline", help="Code LaTeX inline ajouté au préambule."),
    metadata_file: Optional[Path] = typer.Option(None, "--metadata-file", help="Fichier JSON/YAML pour les métadonnées."),
    meta: List[str] = typer.Option([], "--meta", help="Métadonnées supplémentaires clé=valeur."),
    disable_mermaid: bool = typer.Option(False, "--disable-mermaid", help="Désactiver le rendu Mermaid."),
    mermaid_cli_path: Optional[str] = typer.Option(None, "--mermaid-cli", help="Chemin du binaire mmdc."),
    mermaid_format: str = typer.Option("png", "--mermaid-format", help="Format Mermaid (svg/png)."),
    mermaid_theme: Optional[str] = typer.Option(None, "--mermaid-theme", help="Thème Mermaid (default, forest, ...)."),
    mermaid_background: Optional[str] = typer.Option(None, "--mermaid-background", help="Couleur de fond Mermaid."),
    mermaid_config_file: Optional[Path] = typer.Option(None, "--mermaid-config", help="Fichier de config JSON Mermaid."),
    mermaid_arg: List[str] = typer.Option([], "--mermaid-arg", help="Argument supplémentaire transmis à mermaid-cli."),
    mermaid_puppeteer_arg: List[str] = typer.Option(
        [],
        "--mermaid-puppeteer-arg",
        help="Argument passé à Chromium via Puppeteer (par ex. --no-sandbox).",
    ),
    keep_temp: bool = typer.Option(False, "--keep-temp", help="Conserver le répertoire temporaire."),
    pandoc_path: Optional[str] = typer.Option(None, "--pandoc", help="Chemin de l'exécutable pandoc."),
    pandoc_arg: List[str] = typer.Option([], "--pandoc-arg", help="Argument additionnel passé à Pandoc (répétable)."),
    latex_engine: Optional[str] = typer.Option(None, "--latex-engine", help="Moteur LaTeX (xelatex/pdflatex/tectonic)."),
    latex_runs: int = typer.Option(1, "--latex-runs", help="Nombre de passes LaTeX."),
    latex_arg: List[str] = typer.Option([], "--latex-arg", help="Argument supplémentaire passé au moteur LaTeX."),
) -> None:
    """Convertit un ou plusieurs fichiers Markdown en PDF."""

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_data: Dict[str, str] = {}
    metadata_data.update(_load_mapping_file(metadata_file))
    metadata_data.update(_parse_key_value(meta))

    template_config = TemplateConfig(
        template_path=template_path or TemplateConfig().template_path,
        preamble_path=preamble_path,
        extra_preamble=preamble_inline,
    )

    default_mermaid = MermaidConfig()
    mermaid_config = MermaidConfig(
        enabled=not disable_mermaid,
        cli_path=mermaid_cli_path or default_mermaid.cli_path,
        output_format=mermaid_format,
        theme=mermaid_theme,
        background_color=mermaid_background,
        config_file=mermaid_config_file,
        extra_args=default_mermaid.extra_args + mermaid_arg,
        puppeteer_args=default_mermaid.puppeteer_args + mermaid_puppeteer_arg,
    )

    default_pandoc = PandocConfig()
    pandoc_config = PandocConfig(
        executable=pandoc_path or default_pandoc.executable,
        from_format=default_pandoc.from_format,
        to_format=default_pandoc.to_format,
        extra_args=default_pandoc.extra_args + pandoc_arg,
    )

    latex_config = LatexEngineConfig(
        executable=latex_engine or LatexEngineConfig().executable,
        runs=latex_runs,
        extra_args=latex_arg,
    )

    known_fields = set(DocumentMetadata.model_fields.keys())
    structured_metadata: Dict[str, object] = {}
    extra_metadata: Dict[str, object] = {}
    for key, value in metadata_data.items():
        if key in known_fields:
            structured_metadata[key] = value
        else:
            extra_metadata[key] = value
    if extra_metadata:
        structured_metadata["extra"] = extra_metadata

    metadata = DocumentMetadata(**structured_metadata)

    options = ConversionOptions(
        output_dir=output_dir,
        template=template_config,
        metadata=metadata,
        mermaid=mermaid_config,
        pandoc=pandoc_config,
        latex=latex_config,
        keep_temp_dir=keep_temp,
    )

    builder = MarkdownPDFBuilder(options)

    for source in sources:
        if source.is_dir():
            for markdown_file in sorted(source.glob("**/*.md")):
                _convert_single(builder, markdown_file, output_dir)
        else:
            _convert_single(builder, source, output_dir)


def _convert_single(builder: MarkdownPDFBuilder, markdown_file: Path, output_dir: Path) -> None:
    try:
        result = builder.convert(markdown_file)
    except Exception as exc:  # pragma: no cover - feedback utilisateur
        typer.secho(f"❌ {markdown_file}: {exc}", fg=typer.colors.RED)
        return
    try:
        relative = result.relative_to(output_dir)
    except ValueError:
        relative = result
    typer.secho(f"✅ {markdown_file} → {relative}", fg=typer.colors.GREEN)
