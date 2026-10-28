"""Regression tests for the DXF privacy scan.

The scan must keep detecting real private strings and numbers in TEXT/MTEXT,
symbol names and XDATA values, while *not* reporting a numeric token that only
appears as a substring of a content-derived 64-hex digest (or a GUID).  A
SHA-256 digest such as ``canonical_hash`` / ``source_hash`` / ``rep_hash`` /
``ring_key`` is uniformly random hex, so a control number like ``95119``
appears inside one by chance at roughly 6% per 208-entity DXF — a false
positive that used to abort an otherwise clean evidence regeneration.
"""
from __future__ import annotations

import json
from pathlib import Path

import ezdxf
import pytest

from dgcad_e2e import DEFAULT_FORBIDDEN_TOKENS, scan_dxf_privacy

ROOT = Path(__file__).resolve().parents[1]
DESIGN_DXF = ROOT / "docs" / "e2e" / "design-synthesis-001" / "design-proposal.dxf"
THIRD_PARTY = ROOT / "docs" / "e2e" / "third-party-003c"
HANDOFF_EVIDENCE = ROOT / "docs" / "e2e" / "sketch-handoff-a"

NUMERIC_TOKENS = tuple(
    token for token in DEFAULT_FORBIDDEN_TOKENS if token.isdigit()
)
NON_NUMERIC_TOKENS = tuple(
    token for token in DEFAULT_FORBIDDEN_TOKENS if not token.isdigit()
)
APPID = "DESIGN_GRADE"


def _hex64(prefix: str, fill: str = "a") -> str:
    """A deterministic 64-character hex digest that starts with ``prefix``."""
    assert prefix and len(prefix) < 64
    return (prefix + fill * 64)[:64]


def _build_dxf(
    tmp_path: Path,
    *,
    name: str = "privacy.dxf",
    texts: tuple[str, ...] = (),
    mtexts: tuple[str, ...] = (),
    extra_layers: tuple[str, ...] = (),
    xdata_values: tuple[str, ...] = (),
) -> Path:
    doc = ezdxf.new("R2010")
    doc.appids.add(APPID)
    for layer in extra_layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    for value in texts:
        msp.add_text(value, height=2.0)
    for value in mtexts:
        msp.add_mtext(value)
    for index, value in enumerate(xdata_values):
        entity = msp.add_text(f"xdata-{index}", height=2.0)
        entity.set_xdata(APPID, [(1000, value)])
    path = tmp_path / name
    doc.saveas(path)
    return path


def _token_set(report: dict) -> set[str]:
    return {finding["token"] for finding in report["findings"]}


# ---------------------------------------------------------------------------
# a) opaque identifiers never produce a numeric false positive
# ---------------------------------------------------------------------------


def test_numeric_token_inside_xdata_digests_is_not_a_leak(tmp_path):
    digests = (
        _hex64("45393"),          # source_hash-like
        _hex64("95119", "b"),     # rep_hash-like
        _hex64("204131", "c"),    # ring_key-like
        _hex64("193009", "d"),    # another hash
        "45393abc-0000-0000-0000-000000000000",     # GUID without braces
        "{45393abc-0000-0000-0000-000000000000}",   # GUID with braces
    )
    dxf = _build_dxf(tmp_path, xdata_values=digests)
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is True
    assert report["code"] == "PRIVACY_SCAN_PASS"
    assert report["findings"] == []


def test_numeric_token_inside_text_digest_is_not_a_leak(tmp_path):
    # A digest can legitimately reach TEXT (labels, debug text); it is still an
    # opaque identifier, not private numeric data.
    dxf = _build_dxf(tmp_path, texts=(_hex64("95119"),))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is True
    assert report["findings"] == []


def test_uppercase_hex_digest_is_opaque(tmp_path):
    dxf = _build_dxf(tmp_path, xdata_values=(_hex64("95119", "A"),))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is True
    assert report["findings"] == []


# ---------------------------------------------------------------------------
# b) real numeric data is still detected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", NUMERIC_TOKENS)
def test_real_numeric_token_in_text_is_detected(tmp_path, token):
    dxf = _build_dxf(tmp_path, texts=(f"grid coordinate {token}.5 m",))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is False
    assert report["code"] == "PRIVACY_LEAK"
    assert token in _token_set(report)
    finding = next(item for item in report["findings"] if item["token"] == token)
    assert finding["source"] == "text"
    assert token in finding["value"]


def test_real_numeric_token_in_mtext_is_detected(tmp_path):
    dxf = _build_dxf(tmp_path, mtexts=("control point 204131.0",))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is False
    assert "204131" in _token_set(report)
    assert {f["source"] for f in report["findings"]} == {"mtext"}


def test_real_numeric_token_in_layer_name_is_detected(tmp_path):
    dxf = _build_dxf(tmp_path, extra_layers=("A-193009",))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is False
    assert "193009" in _token_set(report)
    assert {f["source"] for f in report["findings"]} == {"layer"}


def test_real_numeric_token_in_short_xdata_value_is_detected(tmp_path):
    dxf = _build_dxf(tmp_path, xdata_values=("ref 95119",))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is False
    assert "95119" in _token_set(report)
    assert {f["source"] for f in report["findings"]} == {"xdata"}


def test_non_numeric_tokens_are_still_detected_everywhere(tmp_path):
    for token in NON_NUMERIC_TOKENS:
        dxf = _build_dxf(
            tmp_path, name=f"leak-{len(token)}.dxf", texts=(f"note {token}",)
        )
        report = scan_dxf_privacy(dxf)
        # findings carry the lowercased token, matching the scanner's contract
        assert report["ok"] is False, token
        assert token.lower() in _token_set(report), token


def test_almost_hex_strings_still_produce_findings(tmp_path):
    almost = (
        _hex64("95119")[:-1],            # 63 hex characters
        _hex64("95119") + "a",          # 65 hex characters
        "95119" + "g" * 59,             # 64 chars but not hex
        "95119" + "-" * 59,             # 64 chars with separators
    )
    dxf = _build_dxf(tmp_path, xdata_values=almost)
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is False
    assert "95119" in _token_set(report)


# ---------------------------------------------------------------------------
# c) committed evidence and non-DXF inputs
# ---------------------------------------------------------------------------


def test_committed_design_evidence_scans_clean():
    assert DESIGN_DXF.is_file()
    report = scan_dxf_privacy(DESIGN_DXF)
    assert report["ok"] is True
    assert report["code"] == "PRIVACY_SCAN_PASS"
    assert report["findings"] == []
    assert report["file"] == DESIGN_DXF.name


def test_committed_third_party_dxfs_scan_clean():
    for name in ("input.dxf", "roundtrip.dxf"):
        path = THIRD_PARTY / name
        assert path.is_file(), name
        report = scan_dxf_privacy(path)
        assert report["ok"] is True, name
        assert report["findings"] == [], name


def test_non_dxf_evidence_fails_closed_without_crashing():
    # review-packet.json / .html are not DXF files; the scanner must return the
    # structured DXF_UNREADABLE result instead of passing silently or raising.
    for name in ("review-packet.json", "review-packet.html"):
        path = HANDOFF_EVIDENCE / name
        if not path.is_file():
            continue
        report = scan_dxf_privacy(path)
        assert report["ok"] is False
        assert report["code"] == "DXF_UNREADABLE"
        assert report["file"] == path.name
        assert report["findings"] == []
        assert report["error"]


def test_missing_file_fails_closed(tmp_path):
    report = scan_dxf_privacy(tmp_path / "does-not-exist.dxf")
    assert report["ok"] is False
    assert report["code"] == "DXF_UNREADABLE"
    assert report["findings"] == []


# ---------------------------------------------------------------------------
# d) public API and return structure are unchanged
# ---------------------------------------------------------------------------


def test_return_structure_is_unchanged(tmp_path):
    clean = scan_dxf_privacy(_build_dxf(tmp_path, name="clean.dxf"))
    assert set(clean) == {"ok", "code", "file", "findings"}
    leak = scan_dxf_privacy(
        _build_dxf(tmp_path, name="leak.dxf", texts=("site-master",))
    )
    assert set(leak) == {"ok", "code", "file", "findings"}
    assert leak["code"] == "PRIVACY_LEAK"
    for finding in leak["findings"]:
        assert set(finding) == {"token", "source", "value"}


def test_custom_forbidden_tokens_are_honoured(tmp_path):
    dxf = _build_dxf(tmp_path, texts=("client XYZ-42 boundary",))
    assert scan_dxf_privacy(dxf, forbidden=["XYZ-42"])["ok"] is False
    assert scan_dxf_privacy(dxf, forbidden=["nothing-here"])["ok"] is True


def test_twenty_digest_variants_in_one_document_have_no_false_positive(tmp_path):
    variants: list[str] = []
    for index in range(20):
        token = NUMERIC_TOKENS[index % len(NUMERIC_TOKENS)]
        fill = "0123456789abcdef"[index % 16]
        variants.append(_hex64(f"{token}{index:02d}", fill))
    dxf = _build_dxf(tmp_path, xdata_values=tuple(variants))
    report = scan_dxf_privacy(dxf)
    assert report["ok"] is True
    assert report["findings"] == []
    assert len(variants) == 20


# ---------------------------------------------------------------------------
# sanity: the fixture helper itself must produce a readable DXF
# ---------------------------------------------------------------------------


def test_fixture_dxf_is_readable_and_inspectable(tmp_path):
    dxf = _build_dxf(tmp_path, xdata_values=(_hex64("95119"),))
    doc = ezdxf.readfile(dxf)
    entities = [entity for entity in doc.modelspace() if entity.has_xdata(APPID)]
    assert len(entities) == 1
    values = list(entities[0].get_xdata(APPID))
    assert isinstance(values[0][1], str)
    assert json.dumps(values[0][1])  # serializable, no opaque ezdxf object
