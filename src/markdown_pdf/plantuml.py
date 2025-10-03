"""Rendu des diagrammes PlantUML via le CLI plantuml."""

from __future__ import annotations

import subprocess
import shlex
from pathlib import Path

from .config import PlantUMLConfig


class PlantUMLRenderingError(RuntimeError):
    """Erreur lors de la génération d'un diagramme PlantUML."""


class PlantUMLRenderer:
    """Encapsule l'appel à l'exécutable PlantUML."""

    def __init__(self, config: PlantUMLConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def render(self, diagram: str, output_dir: Path, stem: str) -> Path:
        if not self.enabled:
            raise PlantUMLRenderingError("PlantUML rendering is disabled")

        output_dir.mkdir(parents=True, exist_ok=True)
        extension = self._resolve_extension()
        output_path = output_dir / f"{stem}.{extension}"

        cmd = self._build_command()

        try:
            result = subprocess.run(
                cmd,
                check=True,
                input=diagram.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:  # pragma: no cover - dépend du système hôte
            raise PlantUMLRenderingError(
                "plantuml introuvable. Installez plantuml et rendez-le accessible dans le PATH."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr_output = exc.stderr.decode("utf-8", errors="ignore").strip()
            stdout_output = exc.stdout.decode("utf-8", errors="ignore").strip()
            details = stderr_output or stdout_output or str(exc)
            raise PlantUMLRenderingError(f"Erreur PlantUML ({' '.join(cmd)}): {details}") from exc

        try:
            output_path.write_bytes(result.stdout)
        except OSError as exc:
            raise PlantUMLRenderingError(
                f"Impossible d'écrire le diagramme PlantUML ({output_path}): {exc}"
            ) from exc

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise PlantUMLRenderingError("Diagramme PlantUML vide ou non généré")

        return output_path

    def _resolve_extension(self) -> str:
        fmt = (self._config.output_format or "").lower()
        if not fmt:
            return "png"
        return fmt

    def _base_cli(self) -> list[str]:
        cli_value = self._config.cli_path
        if not cli_value:
            raise PlantUMLRenderingError("Chemin vers plantuml non défini")
        return shlex.split(cli_value)

    def _build_command(self) -> list[str]:
        base = self._base_cli()
        command = base + ["-pipe"]

        if self._config.charset:
            command.extend(["-charset", self._config.charset])

        if self._config.output_format:
            command.append(f"-t{self._config.output_format}")

        if self._config.extra_args:
            command.extend(self._config.extra_args)

        return command
