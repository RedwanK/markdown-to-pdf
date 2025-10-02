"""Compilation LaTeX vers PDF."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from .config import LatexEngineConfig


class LatexCompilationError(RuntimeError):
    """Erreur lors de la compilation LaTeX."""


class LatexCompiler:
    def __init__(self, config: LatexEngineConfig) -> None:
        self._config = config

    def compile(self, tex_file: Path, search_paths: Optional[Iterable[Path]] = None) -> Path:
        tex_file = tex_file.resolve()
        workdir = tex_file.parent
        pdf_path = tex_file.with_suffix(".pdf")

        env = os.environ.copy()
        if search_paths:
            existing = env.get("TEXINPUTS", "")
            extra = os.pathsep.join(str(Path(path).resolve()) for path in search_paths)
            env["TEXINPUTS"] = os.pathsep.join(filter(None, [extra, existing])) + os.pathsep

        for run_index in range(self._config.runs):
            cmd = [
                self._config.executable,
                "-interaction=nonstopmode",
                *self._config.extra_args,
                tex_file.name,
            ]
            result = subprocess.run(
                cmd,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            if result.returncode != 0:
                log = result.stdout.decode("utf-8", errors="ignore") + "\n" + result.stderr.decode(
                    "utf-8", errors="ignore"
                )
                raise LatexCompilationError(log)
        if not pdf_path.exists():
            raise LatexCompilationError(f"PDF non généré: {pdf_path}")
        return pdf_path
