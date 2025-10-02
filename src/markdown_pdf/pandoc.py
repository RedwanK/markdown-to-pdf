"""Wrapper minimal autour de Pandoc."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List

from .config import PandocConfig


class PandocError(RuntimeError):
    """Exception levée en cas d'échec Pandoc."""


class PandocConverter:
    def __init__(self, config: PandocConfig) -> None:
        self._config = config

    def convert_to_latex(self, markdown_file: Path, resource_paths: Iterable[Path] = ()) -> str:
        cmd: List[str] = [self._config.executable]

        if self._config.extra_args:
            cmd.extend(self._config.extra_args)

        cmd.extend(
            [
                "--from",
                self._config.from_format,
                "--to",
                self._config.to_format,
                str(markdown_file),
            ]
        )

        resource_path_values = [str(path) for path in resource_paths]
        if resource_path_values:
            cmd.extend(["--resource-path", ":".join(resource_path_values)])

        result = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise PandocError(result.stderr.decode("utf-8", errors="ignore"))
        return result.stdout.decode("utf-8")
