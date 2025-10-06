"""Transformation des balises HTML stylées vers du LaTeX inline."""

from __future__ import annotations

import html
import re
from typing import Callable, Dict, List, Tuple

from .latex_utils import latex_escape


_STYLE_ATTR_PATTERN = re.compile(r'style\s*=\s*"([^"]*)"', re.IGNORECASE)
_SPAN_PATTERN = re.compile(
    r"<span[^>]*style=\"[^\"]*\"[^>]*>(.*?)</span>", re.IGNORECASE | re.DOTALL
)
_BLOCK_PATTERN = re.compile(
    r"<(div|p)[^>]*style=\"[^\"]*\"[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL
)
_BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)


def apply_html_styles(markdown_text: str) -> str:
    """Convertit quelques balises HTML stylées en commandes LaTeX."""

    text = markdown_text

    # Remplacer les retours à la ligne simples
    text = _BR_PATTERN.sub(r"\\\\", text)

    def _replace_spans(match: re.Match[str]) -> str:
        span_html = match.group(0)
        attrs_match = _STYLE_ATTR_PATTERN.search(span_html)
        if not attrs_match:
            return span_html
        style = _parse_style(attrs_match.group(1))
        inner = match.group(1)
        transformed = apply_html_styles(inner)
        base_plain = html.unescape(inner)
        if transformed == inner:
            if _should_escape(base_plain):
                content = latex_escape(base_plain)
            else:
                content = base_plain
        else:
            content = transformed
        wrappers = _inline_wrappers("span", style)
        for wrapper in wrappers:
            content = wrapper(content)
        return content

    def _replace_blocks(match: re.Match[str]) -> str:
        block_html = match.group(0)
        attrs_match = _STYLE_ATTR_PATTERN.search(block_html)
        if not attrs_match:
            return block_html
        style = _parse_style(attrs_match.group(1))
        inner = match.group(2)
        transformed = apply_html_styles(inner)
        base_plain = html.unescape(inner)
        if transformed == inner:
            if _should_escape(base_plain):
                content = latex_escape(base_plain)
            else:
                content = base_plain
        else:
            content = transformed
        inline_wrappers = _inline_wrappers(match.group(1).lower(), style)
        for wrapper in inline_wrappers:
            content = wrapper(content)
        alignment = _extract_alignment(style)
        if alignment:
            begin, end = alignment
            content = f"{begin}\n{content}\n{end}"
        return content

    previous = None
    while previous != text:
        previous = text
        text = _SPAN_PATTERN.sub(_replace_spans, text)
        text = _BLOCK_PATTERN.sub(_replace_blocks, text)

    return text


def _parse_style(style_value: str) -> Dict[str, str]:
    style: Dict[str, str] = {}
    for part in style_value.split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        style[key.strip().lower()] = value.strip()
    return style


def _inline_wrappers(tag: str, style: Dict[str, str]) -> List[Callable[[str], str]]:
    wrappers: List[Tuple[str, Callable[[str], str]]] = []

    # Sémantique simple des balises
    if tag in {"strong", "b"}:
        wrappers.append(("bold", lambda s: f"\\textbf{{{s}}}"))
    if tag in {"em", "i"}:
        wrappers.append(("italic", lambda s: f"\\textit{{{s}}}"))
    if tag in {"u"}:
        wrappers.append(("underline", lambda s: f"\\underline{{{s}}}"))
    if tag in {"code"}:
        wrappers.append(("code", lambda s: f"\\texttt{{{s}}}"))

    color_value = style.get("color")
    if color_value:
        wrappers.append((
            f"color:{color_value}",
            lambda s, spec=_normalize_color(color_value): _wrap_color(s, spec),
        ))

    font_weight = style.get("font-weight")
    if font_weight and "bold" in font_weight.lower():
        wrappers.append(("font-weight:bold", lambda s: f"\\textbf{{{s}}}"))

    font_style = style.get("font-style")
    if font_style and "italic" in font_style.lower():
        wrappers.append(("font-style:italic", lambda s: f"\\textit{{{s}}}"))

    decoration = style.get("text-decoration")
    if decoration and "underline" in decoration.lower():
        wrappers.append(("text-decoration:underline", lambda s: f"\\underline{{{s}}}"))

    background = style.get("background-color")
    if background:
        wrappers.append(
            (
                f"background:{background}",
                lambda s, spec=_normalize_color(background): _wrap_background(s, spec),
            )
        )

    # Éviter les doublons en conservant l'ordre
    unique_wrappers: List[Callable[[str], str]] = []
    seen: set[str] = set()
    for key, wrapper in wrappers:
        if key not in seen:
            unique_wrappers.append(wrapper)
            seen.add(key)
    return unique_wrappers


def _extract_alignment(style: Dict[str, str]) -> Tuple[str, str] | None:
    align = style.get("text-align")
    if not align:
        return None
    align = align.lower()
    if "center" in align:
        return "\\begin{center}", "\\end{center}"
    if "right" in align:
        return "\\begin{flushright}", "\\end{flushright}"
    if "left" in align:
        return "\\begin{flushleft}", "\\end{flushleft}"
    if "justify" in align:
        return "\\begin{flushleft}", "\\end{flushleft}"
    return None


def _normalize_color(value: str) -> Tuple[str, str]:
    raw = value.strip()
    hex_match = re.match(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", raw)
    if hex_match:
        hex_value = hex_match.group(1)
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        return "HTML", hex_value.upper()

    rgb_match = re.match(r"rgb\s*\((\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\)", raw, re.IGNORECASE)
    if rgb_match:
        r, g, b = [max(0, min(255, int(component))) for component in rgb_match.groups()]
        return "HTML", f"{r:02X}{g:02X}{b:02X}"

    return "NAME", raw


def _wrap_color(content: str, color_spec: Tuple[str, str]) -> str:
    mode, value = color_spec
    if mode == "HTML":
        return f"\\textcolor[HTML]{{{value}}}{{{content}}}"
    return f"\\textcolor{{{value}}}{{{content}}}"


def _wrap_background(content: str, color_spec: Tuple[str, str]) -> str:
    mode, value = color_spec
    if mode == "HTML":
        return f"\\colorbox[HTML]{{{value}}}{{{content}}}"
    return f"\\colorbox{{{value}}}{{{content}}}"


def _should_escape(value: str) -> bool:
    return not any(ch in value for ch in ("\\", "{", "}"))
