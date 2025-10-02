"""Structures de configuration pour le pipeline LaTeX."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

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
    extra_args: list[str] = Field(default_factory=list)
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


class PandocConfig(BaseModel):
    """Paramètres pour l'appel à Pandoc."""

    executable: str = "pandoc"
    from_format: str = "markdown"
    to_format: str = "latex"
    extra_args: list[str] = Field(default_factory=lambda: ["--listings", "-V", "float-placement=H"])


class LatexEngineConfig(BaseModel):
    """Contrôle de l'appel du moteur LaTeX."""

    executable: str = "xelatex"
    runs: int = 1
    extra_args: list[str] = Field(default_factory=list)


class ConversionOptions(BaseModel):
    """Options globales du pipeline."""

    output_dir: Path
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    mermaid: MermaidConfig = Field(default_factory=MermaidConfig)
    pandoc: PandocConfig = Field(default_factory=PandocConfig)
    latex: LatexEngineConfig = Field(default_factory=LatexEngineConfig)
    keep_temp_dir: bool = False

    @field_validator("output_dir", mode="before")
    @classmethod
    def _cast_output_dir(cls, value: Any) -> Path:
        if isinstance(value, Path):
            return value
        return Path(value)
