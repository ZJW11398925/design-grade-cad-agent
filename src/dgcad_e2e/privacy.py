from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import ezdxf


DEFAULT_FORBIDDEN_TOKENS = (
    "site-master",
    "45393",
    "95119",
    "204131",
    "193009",
    "homography-bend6",
    "PROJ-SITE",
    "后湖",
    "private site reference",
)


def _strings_from_doc(doc) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []

    def add(source: str, value: Any) -> None:
        if isinstance(value, str) and value:
            values.append((source, value))

    for layer in doc.layers:
        add("layer", layer.dxf.name)
    for linetype in doc.linetypes:
        add("linetype", linetype.dxf.name)
        add("linetype", linetype.dxf.description)
    for style in doc.styles:
        add("style", style.dxf.name)
        add("style", style.dxf.font)
    for dimstyle in doc.dimstyles:
        add("dimstyle", dimstyle.dxf.name)
    for block in doc.blocks:
        add("block", block.name)
        for entity in block:
            for pair in _entity_strings(entity):
                values.append(pair)
    for entity in doc.modelspace():
        for pair in _entity_strings(entity):
            values.append(pair)
    return values


def _entity_strings(entity) -> Iterable[tuple[str, str]]:
    dxftype = entity.dxftype()
    if dxftype == "TEXT":
        yield "text", str(entity.dxf.text)
    elif dxftype == "MTEXT":
        yield "mtext", str(entity.text)
    if entity.has_xdata("DESIGN_GRADE"):
        for tag in entity.get_xdata("DESIGN_GRADE"):
            if isinstance(tag[1], str):
                yield "xdata", tag[1]


def scan_dxf_privacy(
    path: str | Path,
    forbidden: Iterable[str] = DEFAULT_FORBIDDEN_TOKENS,
) -> dict[str, Any]:
    path = Path(path)
    tokens = [token.lower() for token in forbidden if token]
    try:
        doc = ezdxf.readfile(path)
    except Exception as exc:  # ezdxf raises several parse-specific errors
        return {
            "ok": False,
            "code": "DXF_UNREADABLE",
            "file": path.name,
            "error": str(exc),
            "findings": [],
        }

    findings: list[dict[str, str]] = []
    for source, value in _strings_from_doc(doc):
        lowered = value.lower()
        for token in tokens:
            if token in lowered:
                findings.append(
                    {
                        "token": token,
                        "source": source,
                        "value": value,
                    }
                )

    raw = path.read_bytes().decode("latin-1", errors="ignore").lower()
    for token in tokens:
        index = raw.find(token)
        if index >= 0:
            findings.append(
                {
                    "token": token,
                    "source": "raw_bytes",
                    "value": raw[max(0, index - 40) : index + len(token) + 40],
                }
            )

    return {
        "ok": not findings,
        "code": "PRIVACY_SCAN_PASS" if not findings else "PRIVACY_LEAK",
        "file": path.name,
        "findings": findings,
    }
