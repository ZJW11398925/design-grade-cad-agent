#!/usr/bin/env python3
"""Run a real AutoCAD Core Console DXF round-trip and record semantic evidence.

The script is intentionally host-dependent: it only produces evidence when a
real AutoCAD Core Console is available. Otherwise it records `blocked` and does
not pretend that same-library ezdxf readback is third-party evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ezdxf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
E2E_FIXTURE = ROOT / "fixtures" / "e2e" / "living-pipeline-001.yaml"
DEFAULT_OUTPUT = ROOT / "docs" / "e2e" / "third-party-003c"
XDATA_APPID = "DESIGN_GRADE"
VERSION_TO_PROFILE = {
    "AC1024": "R2010",
    "AC1027": "R2013",
    "AC1032": "R2018",
}


def find_accoreconsole(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    env_path = os.environ.get("DGCAD_ACCORECONSOLE")
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path
    if os.name == "nt":
        import winreg

        locations = (
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        for location in locations:
            try:
                root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, location)
            except OSError:
                continue
            for index in range(winreg.QueryInfoKey(root)[0]):
                try:
                    name = winreg.EnumKey(root, index)
                    subkey = winreg.OpenKey(root, name)
                    display = str(
                        winreg.QueryValueEx(subkey, "DisplayName")[0]
                    )
                    install = str(
                        winreg.QueryValueEx(subkey, "InstallLocation")[0]
                    )
                except OSError:
                    continue
                if "AutoCAD" not in display or not install:
                    continue
                candidate = Path(install) / "accoreconsole.exe"
                if candidate.is_file():
                    return candidate
    return None


def file_version(path: Path) -> str | None:
    if os.name != "nt":
        return None
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-Item '{path}').VersionInfo.FileVersion",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return completed.stdout.strip() or None
    except Exception:
        return None


def decode_console(raw: bytes) -> str:
    for encoding in ("utf-16-le", "utf-8", "gbk"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if text.count("\x00") < len(text) // 4:
            return text
    return raw.decode("utf-8", errors="replace")


def xdata_map(path: Path) -> dict[tuple[str, str], tuple[Any, ...]]:
    doc = ezdxf.readfile(path)
    result: dict[tuple[str, str], tuple[Any, ...]] = {}
    for entity in doc.modelspace():
        if not entity.has_xdata(XDATA_APPID):
            continue
        values = list(entity.get_xdata(XDATA_APPID))
        try:
            key = (str(values[0][1]), str(values[5][1]))
        except (IndexError, TypeError):
            continue
        result[key] = tuple(value for _, value in values)
    return result


def layer_state(path: Path) -> dict[str, dict[str, Any]]:
    doc = ezdxf.readfile(path)
    return {
        layer.dxf.name: {
            "color": int(layer.dxf.color),
            "linetype": str(layer.dxf.linetype),
            "lineweight": int(layer.dxf.lineweight),
        }
        for layer in doc.layers
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entity_state(path: Path) -> dict[str, Any]:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    audit = doc.audit()
    return {
        "dxf_version": doc.dxfversion,
        "insunits": doc.header.get("$INSUNITS"),
        "entity_count": len(msp),
        "entity_types": {
            dxftype: sum(1 for e in msp if e.dxftype() == dxftype)
            for dxftype in sorted({e.dxftype() for e in msp})
        },
        "layers": layer_state(path),
        "blocks": sorted(block.name for block in doc.blocks),
        "dimstyles": sorted(style.dxf.name for style in doc.dimstyles),
        "text_styles": sorted(style.dxf.name for style in doc.styles),
        "xdata_count": len(xdata_map(path)),
        "audit_errors": len(audit.errors),
        "audit_fixes": len(audit.fixes),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accoreconsole", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = output_dir / "input.dxf"
    roundtrip_path = output_dir / "roundtrip.dxf"
    script_path = output_dir / "save.scr"
    environment_path = output_dir / "environment.json"
    comparison_path = output_dir / "comparison.json"
    stdout_path = output_dir / "stdout.txt"

    for stale in (roundtrip_path, comparison_path, environment_path):
        if stale.exists():
            stale.unlink()

    exe = find_accoreconsole(args.accoreconsole)
    environment = {
        "schema_id": "dgcad.third_party.roundtrip.environment.v0.1",
        "platform": platform.platform(),
        "python": sys.version,
        "autocad_executable": None if exe is None else str(exe),
        "autocad_file_version": None if exe is None else file_version(exe),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "timeout_seconds": args.timeout,
        "isolated_profile": "DGCAD",
    }

    if exe is None:
        comparison = {
            "schema_id": "dgcad.third_party.roundtrip.comparison.v0.1",
            "verdict": "blocked",
            "blocker": "AutoCAD Core Console not found; set --accoreconsole or DGCAD_ACCORECONSOLE",
            "non_claims": [
                "No third-party CAD round-trip was executed.",
                "Same-library ezdxf readback is not third-party evidence.",
            ],
        }
        comparison_path.write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        environment_path.write_text(
            json.dumps(environment, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(comparison, indent=2, ensure_ascii=False))
        return 0

    from dgcad_cad import validate_dxf
    from dgcad_e2e import LivingProject

    work = Path(tempfile.mkdtemp(prefix="dgcad-autocad-"))
    project = LivingProject.create(E2E_FIXTURE, work / "project")
    project.bootstrap()
    source = project.output_dir / "living-mutations-002.dxf"
    input_path.write_bytes(source.read_bytes())

    isolated = output_dir / "isolated"
    isolated.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                '(princ "DGCAD_SAVE\\n")',
                '(command "_.SAVEAS" "DXF" "16" "{}")'.format(
                    roundtrip_path.as_posix()
                ),
                '(princ "DGCAD_SAVED\\n")',
                '(command "_.QUIT" "_Y")',
                "",
            ]
        ),
        encoding="utf-8",
    )

    command = [
        str(exe),
        "/i",
        str(input_path),
        "/s",
        str(script_path),
        "/isolate",
        "DGCAD",
        str(isolated),
    ]
    environment["command"] = command
    stdout_text = ""
    returncode = None
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
        returncode = completed.returncode
        stdout_text = decode_console(completed.stdout)
        stdout_path.write_text(stdout_text, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        if exc.stdout:
            stdout_text = decode_console(exc.stdout)
            stdout_path.write_text(
                stdout_text, encoding="utf-8", errors="replace"
            )

    environment["returncode"] = returncode
    environment["timed_out"] = timed_out
    environment_path.write_text(
        json.dumps(environment, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if timed_out or not roundtrip_path.is_file():
        comparison = {
            "schema_id": "dgcad.third_party.roundtrip.comparison.v0.1",
            "verdict": "blocked",
            "blocker": (
                "AutoCAD Core Console timed out"
                if timed_out
                else "AutoCAD did not produce roundtrip.dxf"
            ),
            "returncode": returncode,
            "environment_ref": environment_path.name,
            "non_claims": [
                "No semantic pass is claimed without a round-trip file.",
            ],
        }
        comparison_path.write_text(
            json.dumps(comparison, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(comparison, indent=2, ensure_ascii=False))
        return 1

    input_state = entity_state(input_path)
    roundtrip_state = entity_state(roundtrip_path)
    input_xdata = xdata_map(input_path)
    roundtrip_xdata = xdata_map(roundtrip_path)
    short_version = VERSION_TO_PROFILE.get(
        roundtrip_state["dxf_version"], project.profile.dxf_version
    )
    semantic_profile = replace(project.profile, dxf_version=short_version)
    validation = validate_dxf(
        roundtrip_path, project.latest_cad_ir, semantic_profile
    )

    differences: list[dict[str, Any]] = []
    if input_state["dxf_version"] != roundtrip_state["dxf_version"]:
        differences.append(
            {
                "kind": "dxf_version",
                "input": input_state["dxf_version"],
                "roundtrip": roundtrip_state["dxf_version"],
            }
        )
    for layer_name, input_layer in input_state["layers"].items():
        roundtrip_layer = roundtrip_state["layers"].get(layer_name)
        if roundtrip_layer is None:
            continue
        if input_layer["linetype"].upper() != roundtrip_layer[
            "linetype"
        ].upper():
            differences.append(
                {
                    "kind": "linetype_semantics",
                    "layer": layer_name,
                    "input": input_layer["linetype"],
                    "roundtrip": roundtrip_layer["linetype"],
                }
            )
        elif input_layer["linetype"] != roundtrip_layer["linetype"]:
            differences.append(
                {
                    "kind": "symbol_name_case",
                    "table": "linetype",
                    "layer": layer_name,
                    "input": input_layer["linetype"],
                    "roundtrip": roundtrip_layer["linetype"],
                }
            )
    if input_state["entity_count"] != roundtrip_state["entity_count"]:
        differences.append(
            {
                "kind": "entity_count",
                "input": input_state["entity_count"],
                "roundtrip": roundtrip_state["entity_count"],
            }
        )
    if input_state["entity_types"] != roundtrip_state["entity_types"]:
        differences.append(
            {
                "kind": "entity_types",
                "input": input_state["entity_types"],
                "roundtrip": roundtrip_state["entity_types"],
            }
        )
    if input_state["xdata_count"] != roundtrip_state["xdata_count"]:
        differences.append(
            {
                "kind": "xdata_count",
                "input": input_state["xdata_count"],
                "roundtrip": roundtrip_state["xdata_count"],
            }
        )
    if input_xdata != roundtrip_xdata:
        differences.append(
            {
                "kind": "xdata_values",
                "input_keys": sorted(input_xdata),
                "roundtrip_keys": sorted(roundtrip_xdata),
            }
        )
    if input_state["insunits"] != roundtrip_state["insunits"]:
        differences.append(
            {
                "kind": "insunits",
                "input": input_state["insunits"],
                "roundtrip": roundtrip_state["insunits"],
            }
        )

    blocking = validation.verdict != "pass"
    if blocking:
        verdict = "fail"
    elif differences and all(
        item["kind"] in {"dxf_version", "symbol_name_case"}
        for item in differences
    ):
        verdict = "semantic_pass_with_serialization_differences"
    elif differences:
        verdict = "conditional"
    else:
        verdict = "semantic_pass"

    comparison = {
        "schema_id": "dgcad.third_party.roundtrip.comparison.v0.1",
        "verdict": verdict,
        "tool": "AutoCAD Core Console",
        "environment_ref": environment_path.name,
        "input": {
            "file": input_path.name,
            "sha256": file_sha256(input_path),
            "state": input_state,
        },
        "roundtrip": {
            "file": roundtrip_path.name,
            "sha256": file_sha256(roundtrip_path),
            "state": roundtrip_state,
        },
        "scope": {
            "matrix_status": "partial",
            "apps_executed": ["AutoCAD 2024 Core Console"],
            "apps_not_executed": [
                "LibreCAD",
                "FreeCAD",
                "AutoCAD GUI visual QA",
            ],
        },
        "validator": {
            "profile_version": semantic_profile.dxf_version,
            "verdict": validation.verdict,
            "codes": list(validation.codes),
        },
        "differences": differences,
        "non_claims": [
            "Single AutoCAD 2024 Core Console host; no LibreCAD/FreeCAD/GUI visual QA.",
            "Synthetic E2E fixture only; no real design-office profile.",
            "Modelspace-only comparison.",
            "Same CAD-IR and one fixture; not a general CAD compatibility proof.",
        ],
    }
    comparison_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
    return 0 if verdict in {
        "semantic_pass",
        "semantic_pass_with_serialization_differences",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
