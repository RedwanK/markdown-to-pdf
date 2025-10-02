"""Utilitaires LaTeX."""

from __future__ import annotations

_LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: str | None) -> str:
    """Échappe les caractères spéciaux LaTeX d'une chaîne."""

    if value is None:
        return ""
    escaped = []
    for char in value:
        escaped.append(_LATEX_SPECIAL_CHARS.get(char, char))
    return "".join(escaped)
