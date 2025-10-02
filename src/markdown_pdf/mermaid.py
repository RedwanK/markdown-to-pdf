"""Rendu des diagrammes Mermaid via mermaid-cli."""

from __future__ import annotations

import json
import subprocess
import tempfile
import shlex
from pathlib import Path
from typing import List, Optional

from .config import MermaidConfig


class MermaidRenderingError(RuntimeError):
    """Erreur lors de la génération d'un diagramme Mermaid."""


class MermaidRenderer:
    """Encapsule l'appel au binaire mermaid-cli."""

    def __init__(self, config: MermaidConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def render(self, diagram: str, output_dir: Path, stem: str) -> Path:
        if not self.enabled:
            raise MermaidRenderingError("Mermaid rendering is disabled")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{stem}.{self._config.output_format}"

        with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as source_file:
            source_file.write(diagram)
            source_path = Path(source_file.name)

        temp_puppeteer_config_path: Optional[Path] = None

        config_path = self._config.config_file
        puppeteer_config_path: Optional[Path] = None

        if self._config.puppeteer_args:
            try:
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as puppeteer_config_file:
                    json.dump({"args": self._config.puppeteer_args}, puppeteer_config_file)
                    temp_puppeteer_config_path = Path(puppeteer_config_file.name)
                    puppeteer_config_path = temp_puppeteer_config_path
            except OSError as exc:
                raise MermaidRenderingError(
                    f"Impossible de créer un fichier de configuration Puppeteer temporaire: {exc}"
                ) from exc

        commands = self._build_candidate_commands(
            source_path,
            output_path,
            config_path=config_path,
            puppeteer_config_path=puppeteer_config_path,
            extra_args=self._config.extra_args,
        )
        last_error: str | None = None

        try:
            for idx, cmd in enumerate(commands):
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    break
                except FileNotFoundError as exc:
                    raise MermaidRenderingError(
                        "mermaid-cli introuvable. Installez @mermaid-js/mermaid-cli et rendez-le accessible dans le PATH."
                    ) from exc
                except subprocess.CalledProcessError as exc:
                    error_output = exc.stderr.decode("utf-8", errors="ignore").strip()
                    stdout_output = exc.stdout.decode("utf-8", errors="ignore").strip()
                    details = error_output or stdout_output or str(exc)
                    last_error = f"commande {' '.join(cmd)} → {details}"
                    if idx == len(commands) - 1:
                        cmd_repr = " ".join(cmd)
                        raise MermaidRenderingError(f"Erreur mermaid-cli ({cmd_repr}): {details}") from exc
                    continue
            else:
                if last_error:
                    raise MermaidRenderingError(f"Erreur mermaid-cli: {last_error}")
        finally:
            try:
                source_path.unlink()
            except OSError:
                pass
            if temp_puppeteer_config_path is not None:
                try:
                    temp_puppeteer_config_path.unlink()
                except OSError:
                    pass

        return output_path

    def _base_cli(self) -> List[str]:
        cli_value = self._config.cli_path
        if not cli_value:
            raise MermaidRenderingError("Chemin vers mermaid-cli non défini")
        return shlex.split(cli_value)

    def _build_candidate_commands(
        self,
        source_path: Path,
        output_path: Path,
        *,
        config_path: Optional[Path],
        puppeteer_config_path: Optional[Path],
        extra_args: List[str],
    ) -> List[List[str]]:
        base = self._base_cli()

        legacy = base + [
            "-i",
            str(source_path),
            "-o",
            str(output_path),
        ]

        if self._config.output_format:
            legacy.extend(["-f", self._config.output_format])
        if self._config.theme:
            legacy.extend(["-t", self._config.theme])
        if self._config.background_color:
            legacy.extend(["-b", self._config.background_color])
        if config_path is not None:
            legacy.extend(["-c", str(config_path)])
        if puppeteer_config_path is not None:
            legacy.extend(["-p", str(puppeteer_config_path)])
        if "--quiet" not in base:
            legacy.append("--quiet")

        commands: List[List[str]] = [legacy.copy()]

        modern_base = base + [
            "--input",
            str(source_path),
            "--output",
            str(output_path),
        ]

        if self._config.theme:
            modern_base.extend(["--theme", self._config.theme])
        if self._config.background_color:
            modern_base.extend(["--backgroundColor", self._config.background_color])
        if config_path is not None:
            modern_base.extend(["--configFile", str(config_path)])
        if puppeteer_config_path is not None:
            modern_base.extend(["--puppeteerConfigFile", str(puppeteer_config_path)])
        if "--quiet" not in base:
            modern_base.append("--quiet")

        commands.append(modern_base.copy())

        if self._config.output_format:
            for flag in ("--format", "--outputFormat"):
                cmd_with_format = modern_base + [flag, self._config.output_format]
                if cmd_with_format not in commands:
                    commands.append(cmd_with_format)

        if extra_args:
            commands = [cmd + list(extra_args) for cmd in commands]

        # Supprimer les doublons éventuels en conservant l'ordre
        unique_commands: List[List[str]] = []
        for candidate in commands:
            if candidate not in unique_commands:
                unique_commands.append(candidate)
        return unique_commands
