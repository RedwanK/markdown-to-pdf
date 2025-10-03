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
    PlantUMLConfig,
    RemoteImageConfig,
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
    output_file: Optional[Path] = typer.Option(
        None,
        "--output-file",
        "-f",
        help="Nom du PDF généré (relatif à --output-dir sauf chemin absolu).",
    ),
    template_path: Optional[Path] = typer.Option(None, "--template", help="Template LaTeX Jinja personnalisé."),
    preamble_path: Optional[Path] = typer.Option(None, "--preamble", help="Fichier LaTeX à injecter dans le préambule."),
    preamble_inline: Optional[str] = typer.Option(None, "--preamble-inline", help="Code LaTeX inline ajouté au préambule."),
    metadata_file: Optional[Path] = typer.Option(None, "--meta", help="Fichier JSON/YAML pour les métadonnées."),
    meta_entry: List[str] = typer.Option([], "--meta-entry", help="Métadonnées supplémentaires clé=valeur."),
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
    disable_remote_images: bool = typer.Option(
        False,
        "--disable-remote-images",
        help="Désactiver le téléchargement des images distantes référencées dans le Markdown.",
    ),
    remote_image_timeout: float = typer.Option(
        10.0,
        "--remote-image-timeout",
        help="Délai maximal (en secondes) pour récupérer une image distante.",
    ),
    remote_image_user_agent: Optional[str] = typer.Option(
        None,
        "--remote-image-user-agent",
        help="User-Agent HTTP utilisé pour télécharger les images distantes.",
    ),
    disable_plantuml: bool = typer.Option(
        False,
        "--disable-plantuml",
        help="Désactiver le rendu PlantUML.",
    ),
    plantuml_cli_path: Optional[str] = typer.Option(None, "--plantuml-cli", help="Chemin du binaire plantuml."),
    plantuml_format: str = typer.Option("png", "--plantuml-format", help="Format PlantUML (png/svg/eps/pdf)."),
    plantuml_charset: str = typer.Option("UTF-8", "--plantuml-charset", help="Encodage utilisé par PlantUML."),
    plantuml_arg: List[str] = typer.Option(
        [],
        "--plantuml-arg",
        help="Argument supplémentaire transmis à plantuml.",
    ),
    keep_temp: bool = typer.Option(False, "--keep-temp", help="Conserver le répertoire temporaire."),
    pandoc_path: Optional[str] = typer.Option(None, "--pandoc", help="Chemin de l'exécutable pandoc."),
    pandoc_arg: List[str] = typer.Option([], "--pandoc-arg", help="Argument additionnel passé à Pandoc (répétable)."),
    latex_engine: Optional[str] = typer.Option(None, "--latex-engine", help="Moteur LaTeX (xelatex/pdflatex/tectonic)."),
    latex_runs: int = typer.Option(2, "--latex-runs", help="Nombre de passes LaTeX."),
    latex_arg: List[str] = typer.Option([], "--latex-arg", help="Argument supplémentaire passé au moteur LaTeX."),
) -> None:
    """Convertit un ou plusieurs fichiers Markdown en PDF."""

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_data: Dict[str, str] = {}
    metadata_data.update(_load_mapping_file(metadata_file))
    metadata_data.update(_parse_key_value(meta_entry))

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

    default_plantuml = PlantUMLConfig()
    plantuml_config = PlantUMLConfig(
        enabled=not disable_plantuml,
        cli_path=plantuml_cli_path or default_plantuml.cli_path,
        output_format=plantuml_format,
        charset=plantuml_charset,
        extra_args=default_plantuml.extra_args + plantuml_arg,
    )

    default_remote_images = RemoteImageConfig()
    remote_images_config = RemoteImageConfig(
        enabled=not disable_remote_images,
        timeout=remote_image_timeout,
        user_agent=remote_image_user_agent or default_remote_images.user_agent,
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
        plantuml=plantuml_config,
        remote_images=remote_images_config,
        pandoc=pandoc_config,
        latex=latex_config,
        keep_temp_dir=keep_temp,
    )

    if output_file and len(sources) != 1:
        raise typer.BadParameter("L'option --output-file nécessite une seule source.")

    custom_output: Optional[Path] = None
    if output_file:
        custom_output = output_file if output_file.is_absolute() else output_dir / output_file
        custom_output = custom_output.resolve()
        custom_output.parent.mkdir(parents=True, exist_ok=True)

    builder = MarkdownPDFBuilder(options)

    for source in sources:
        if source.is_dir():
            markdown_files = sorted(path for path in source.glob("**/*.md") if path.is_file())
            if not markdown_files:
                typer.secho(f"⚠️ {source}: aucun fichier Markdown trouvé.", fg=typer.colors.YELLOW)
                continue
            output_path = custom_output if custom_output else output_dir / f"{source.name}.pdf"
            _convert_directory(builder, source, markdown_files, output_path)
        else:
            _convert_single(builder, source, output_dir, custom_output)


def _convert_single(
    builder: MarkdownPDFBuilder,
    markdown_file: Path,
    output_dir: Path,
    output_path: Optional[Path] = None,
) -> None:
    try:
        result = builder.convert(markdown_file, output_path=output_path)
    except Exception as exc:  # pragma: no cover - feedback utilisateur
        typer.secho(f"❌ {markdown_file}: {exc}", fg=typer.colors.RED)
        return
    try:
        relative = result.relative_to(output_dir)
    except ValueError:
        relative = result
    typer.secho(f"✅ {markdown_file} → {relative}", fg=typer.colors.GREEN)


def _convert_directory(
    builder: MarkdownPDFBuilder,
    source_dir: Path,
    markdown_files: list[Path],
    output_path: Path,
) -> None:
    try:
        result = builder.convert_many(markdown_files, output_path=output_path)
    except Exception as exc:  # pragma: no cover - feedback utilisateur
        typer.secho(f"❌ {source_dir}: {exc}", fg=typer.colors.RED)
        return
    typer.secho(f"✅ dossier {source_dir} → {result.name}", fg=typer.colors.GREEN)
