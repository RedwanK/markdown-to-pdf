"""Téléchargement des images distantes référencées dans le Markdown."""

from __future__ import annotations

import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .config import RemoteImageConfig


class RemoteImageError(RuntimeError):
    """Erreur lors du téléchargement d'une image distante."""


class RemoteImageDownloader:
    """Télécharge les images distantes dans un répertoire donné."""

    def __init__(self, config: RemoteImageConfig) -> None:
        self._config = config

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def download(self, url: str, output_dir: Path, stem: str) -> Path:
        if not self.enabled:
            raise RemoteImageError("Téléchargement d'images distantes désactivé")

        output_dir.mkdir(parents=True, exist_ok=True)

        request = urllib.request.Request(url, headers={"User-Agent": self._config.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout) as response:
                data = response.read()
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        except urllib.error.HTTPError as exc:  # pragma: no cover - dépend des ressources externes
            raise RemoteImageError(f"HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RemoteImageError(str(exc.reason)) from exc
        except TimeoutError as exc:  # pragma: no cover - dépend du système
            raise RemoteImageError("délai dépassé") from exc

        extension = self._resolve_extension(url, content_type)
        target_path = output_dir / f"{stem}{extension}"

        try:
            target_path.write_bytes(data)
        except OSError as exc:  # pragma: no cover - dépend du FS
            raise RemoteImageError(f"écriture impossible ({exc})") from exc

        return target_path

    def _resolve_extension(self, url: str, content_type: str) -> str:
        ext_from_content = mimetypes.guess_extension(content_type) if content_type else None
        if ext_from_content:
            return ext_from_content

        parsed = urllib.parse.urlparse(url)
        name = os.path.basename(parsed.path)
        match = re.search(r"(\.[A-Za-z0-9]{1,5})$", name)
        if match:
            return match.group(1)

        # Repli raisonnable
        return ".png"
