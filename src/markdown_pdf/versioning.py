"""Gestion centralisée des versions générées pour les documents PDF."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


def _sanitize(value: str) -> str:
    """Nettoie les champs avant sérialisation."""
    return value.replace("|", "/").replace("\n", " ").strip()


@dataclass
class VersionEntry:
    """Représente une ligne du fichier `.version`."""

    version: int
    date: str
    time: str
    author: Optional[str]
    filename: str
    note: Optional[str] = None

    def to_line(self) -> str:
        author = _sanitize(self.author) if self.author else ""
        filename = _sanitize(self.filename)
        note = _sanitize(self.note) if self.note else ""
        return f"{self.version}|{_sanitize(self.date)}|{_sanitize(self.time)}|{author}|{filename}|{note}"

    def as_dict(self) -> dict[str, str | int]:
        data = asdict(self)
        data["author"] = data.get("author") or ""
        data["note"] = data.get("note") or ""
        return data

    @classmethod
    def from_line(cls, line: str) -> Optional["VersionEntry"]:
        parts = [part.strip() for part in line.strip().split("|")]
        if len(parts) < 5:
            return None
        try:
            version = int(parts[0])
        except ValueError:
            return None
        date, time, author, filename = parts[1], parts[2], parts[3], parts[4]
        note = parts[5] if len(parts) > 5 else ""
        author = author if author else None
        if not filename:
            return None
        return cls(version=version, date=date, time=time, author=author, filename=filename, note=note or None)


class VersionManager:
    """Lit et persiste les entrées de version associées aux PDF générés."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._version_file = directory / ".version"

    @property
    def version_file_path(self) -> Path:
        return self._version_file

    @property
    def version_file_exists(self) -> bool:
        return self._version_file.exists()

    def read_entries(self) -> List[VersionEntry]:
        if not self._version_file.exists():
            return []
        entries: list[VersionEntry] = []
        with self._version_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                entry = VersionEntry.from_line(line)
                if entry:
                    entries.append(entry)
        return entries

    def history_for(self, filename: str) -> List[VersionEntry]:
        history = [entry for entry in self.read_entries() if entry.filename == filename]
        history.sort(key=lambda entry: entry.version)
        return history

    def build_entry(
        self,
        version: int,
        timestamp: datetime,
        filename: str,
        author: Optional[str],
        note: Optional[str],
    ) -> VersionEntry:
        cleaned_note = note.strip() if isinstance(note, str) else None
        return VersionEntry(
            version=version,
            date=timestamp.strftime("%Y-%m-%d"),
            time=timestamp.strftime("%H:%M"),
            author=author or None,
            filename=filename,
            note=cleaned_note or None,
        )

    def build_entry_from_existing_pdf(self, pdf_path: Path, version: int = 1) -> Optional[VersionEntry]:
        if not pdf_path.exists():
            return None
        timestamp = datetime.fromtimestamp(pdf_path.stat().st_mtime)
        author = self._pdf_author(pdf_path)
        return VersionEntry(
            version=version,
            date=timestamp.strftime("%Y-%m-%d"),
            time=timestamp.strftime("%H:%M"),
            author=author,
            filename=pdf_path.name,
            note=None,
        )

    def append_entries(
        self,
        entries: Iterable[VersionEntry],
        *,
        bootstrap_entry: Optional[VersionEntry] = None,
    ) -> None:
        entries_list = list(entries)
        lines_to_write: list[str] = []

        if bootstrap_entry and not self._version_file.exists():
            lines_to_write.append(bootstrap_entry.to_line())

        for entry in entries_list:
            lines_to_write.append(entry.to_line())

        if not lines_to_write:
            return

        self._directory.mkdir(parents=True, exist_ok=True)
        mode = "a" if self._version_file.exists() else "w"
        with self._version_file.open(mode, encoding="utf-8") as handle:
            for line in lines_to_write:
                handle.write(line + "\n")

    @staticmethod
    def _pdf_author(pdf_path: Path) -> Optional[str]:
        try:
            result = subprocess.run(
                ["pdfinfo", str(pdf_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode != 0:
            return None

        for raw_line in result.stdout.splitlines():
            if raw_line.startswith("Author:"):
                _, value = raw_line.split(":", 1)
                cleaned = value.strip()
                return cleaned or None
        return None
