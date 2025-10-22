"""Structures de configuration pour le pipeline LaTeX."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import textwrap

from pydantic import BaseModel, Field, field_validator

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_PATH = PACKAGE_ROOT / "templates" / "document.tex.j2"


class DocumentMetadata(BaseModel):
    """Informations affichées dans l'en-tête et le pied de page."""

    title: Optional[str] = None
    author: Optional[str] = None
    company: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    logo_path: Optional[Path] = None
    title_color: Optional[str] = None
    title_font: Optional[str] = None
    body_font: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("logo_path", mode="before")
    @classmethod
    def _cast_logo_path(cls, value: Any) -> Optional[Path]:
        if value in (None, ""):
            return None
        if isinstance(value, Path):
            return value
        return Path(value)

    def as_template_context(self) -> Dict[str, Any]:
        data = self.model_dump()
        if self.logo_path is not None:
            data["logo_path"] = self.logo_path
        return data


class TemplateConfig(BaseModel):
    """Chemins et options liés au template LaTeX."""

    template_path: Path = Field(default=DEFAULT_TEMPLATE_PATH)
    preamble_path: Optional[Path] = None
    extra_preamble: Optional[str] = None

    @field_validator("template_path", "preamble_path", mode="before")
    @classmethod
    def _cast_path(cls, value: Any) -> Optional[Path]:
        if value in (None, ""):
            return None
        if isinstance(value, Path):
            return value
        return Path(value)


class MermaidConfig(BaseModel):
    """Configuration dédiée à mermaid-cli."""

    enabled: bool = True
    cli_path: str = "mmdc"
    output_format: str = "png"  # png recommandé pour LaTeX
    theme: Optional[str] = None
    background_color: Optional[str] = None
    config_file: Optional[Path] = None
    extra_args: list[str] = Field(default_factory=lambda: ["--scale", "2"])
    puppeteer_args: list[str] = Field(
        default_factory=lambda: ["--no-sandbox", "--disable-setuid-sandbox"]
    )

    @field_validator("config_file", mode="before")
    @classmethod
    def _cast_config_path(cls, value: Any) -> Optional[Path]:
        if value in (None, ""):
            return None
        if isinstance(value, Path):
            return value
        return Path(value)


class PlantUMLConfig(BaseModel):
    """Configuration pour l'appel au CLI PlantUML."""

    enabled: bool = True
    cli_path: str = "plantuml"
    output_format: str = "pdf"
    charset: str = "UTF-8"
    extra_args: list[str] = Field(default_factory=list)


class RemoteImageConfig(BaseModel):
    """Paramètres de récupération des images distantes référencées en Markdown."""

    enabled: bool = True
    timeout: float = 10.0
    user_agent: str = "markdown-pdf/0.1"


class PandocConfig(BaseModel):
    """Paramètres pour l'appel à Pandoc."""

    executable: str = "pandoc"
    from_format: str = "markdown+lists_without_preceding_blankline"
    to_format: str = "latex"
    extra_args: list[str] = Field(default_factory=lambda: ["--listings"])


class LatexEngineConfig(BaseModel):
    """Contrôle de l'appel du moteur LaTeX."""

    executable: str = "xelatex"
    runs: int = 2
    extra_args: list[str] = Field(default_factory=list)


class ConversionOptions(BaseModel):
    """Options globales du pipeline."""

    output_dir: Path
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    mermaid: MermaidConfig = Field(default_factory=MermaidConfig)
    plantuml: PlantUMLConfig = Field(default_factory=PlantUMLConfig)
    remote_images: RemoteImageConfig = Field(default_factory=RemoteImageConfig)
    pandoc: PandocConfig = Field(default_factory=PandocConfig)
    latex: LatexEngineConfig = Field(default_factory=LatexEngineConfig)
    keep_temp_dir: bool = False
    include_cover: bool = True
    include_toc: bool = True
    meta_template: str = Field(
        default_factory=lambda: textwrap.dedent(
            """
# Metadata template for markdown-pdf
# Remplissez les champs souhaités puis utilisez ce fichier avec `--meta`.
# Les champs optionnels peuvent être supprimés.

title: Nom du document
company: Société
author: Responsable du contenu
contact: email@example.com
address: 12 rue de la documentation, 75000 Paris
logo_path: assets/logo.png

# Couleurs et polices (optionnels)
title_color: "#870160"
title_font: "TeX Gyre Heros"
body_font: "TeX Gyre Heros"

# Informations additionnelles affichées sur la couverture
extra:
  subtitle: Sous-titre optionnel
  cover_notes: Notes supplémentaires sur la couverture
            """.strip()
        )
    )

    @field_validator("output_dir", mode="before")
    @classmethod
    def _cast_output_dir(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value
        return Path(value)
