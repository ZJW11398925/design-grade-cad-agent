from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import ezdxf

from dgcad_domain import parse_geometry
from dgcad_foundation import canonical_hash

from .ir import CadIR, CadObject, DeliveryProfile


XDATA_APPID = "DESIGN_GRADE"
XDATA_FIELDS = (
    "object_id",
    "object_class",
    "geometry_revision",
    "source_hash",
    "rep_hash",
    "entity_role",
    "part_index",
    "ring_index",
    "ring_role",
)


@dataclass(frozen=True)
class DxfCompileResult:
    dxf_path: str
    entity_count: int
    audit_errors: int
    audit_fixes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "dxf_path": self.dxf_path,
            "entity_count": self.entity_count,
            "audit_errors": self.audit_errors,
            "audit_fixes": self.audit_fixes,
            "sha256": self.sha256,
        }


def _source_hash(obj: CadObject) -> str:
    return canonical_hash(
        {
            "object_id": obj.object_id,
            "source_world": obj.source_world,
            "source_trace_ref": obj.provenance.get("source_trace_ref"),
            "geometry_revision": obj.geometry_revision,
            "provenance": obj.provenance,
        }
    )


def _rep_hash(obj: CadObject) -> str:
    return canonical_hash(
        {
            "representation_kind": obj.representation_kind,
            "geometry": obj.geometry,
            "massing": obj.massing,
        }
    )


def _set_xdata(
    entity,
    obj: CadObject,
    *,
    entity_role: str,
    part_index: int,
    ring_index: int,
    ring_role: str,
) -> None:
    entity.set_xdata(
        XDATA_APPID,
        [
            (1000, obj.object_id),
            (1000, obj.object_class),
            (1070, obj.geometry_revision),
            (1000, _source_hash(obj)),
            (1000, _rep_hash(obj)),
            (1000, entity_role),
            (1070, part_index),
            (1070, ring_index),
            (1000, ring_role),
        ],
    )


def _polygon_rings(geometry):
    if geometry.geom_type == "Polygon":
        yield 0, "outer", geometry.exterior
        for index, interior in enumerate(geometry.interiors, start=1):
            yield 0, "hole", interior
    elif geometry.geom_type == "MultiPolygon":
        for part_index, polygon in enumerate(geometry.geoms):
            yield part_index, "outer", polygon.exterior
            for interior in polygon.interiors:
                yield part_index, "hole", interior
    else:
        raise ValueError(f"unsupported polygon geometry: {geometry.geom_type}")


def _ring_coords(ring) -> list[tuple[float, float]]:
    coords = [(float(x), float(y)) for x, y in ring.coords]
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return coords


def _insunits(units: str) -> int:
    if units == "metre":
        return 6
    if units == "millimetre":
        return 4
    raise ValueError(f"unsupported units: {units}")


def compile_to_dxf(
    cad_ir: CadIR, profile: DeliveryProfile, out_path: str | Path
) -> DxfCompileResult:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = _insunits(profile.units)
    doc.header["$LWDISPLAY"] = 1
    doc.appids.add(XDATA_APPID)

    for layer_name, spec in profile.layers.items():
        doc.layers.add(
            layer_name,
            color=int(spec.get("color", 7)),
            linetype=str(spec.get("linetype", "CONTINUOUS")),
            lineweight=int(spec.get("lineweight", -1)),
        )

    msp = doc.modelspace()
    entity_count = 0
    for obj in cad_ir.objects:
        geometry = parse_geometry(obj.geometry)
        if obj.representation_kind == "polygon_ring":
            ring_index = 0
            for part_index, ring_role, ring in _polygon_rings(geometry):
                entity = msp.add_lwpolyline(
                    _ring_coords(ring),
                    close=True,
                    dxfattribs={"layer": obj.layer_key},
                )
                _set_xdata(
                    entity,
                    obj,
                    entity_role="polygon_ring",
                    part_index=part_index,
                    ring_index=ring_index,
                    ring_role=ring_role,
                )
                ring_index += 1
                entity_count += 1
        elif obj.representation_kind == "centerline":
            if geometry.geom_type == "LineString":
                lines = [geometry]
            elif geometry.geom_type == "MultiLineString":
                lines = list(geometry.geoms)
            else:
                raise ValueError(
                    f"unsupported centerline geometry: {geometry.geom_type}"
                )
            for part_index, line in enumerate(lines):
                coords = [(float(x), float(y)) for x, y in line.coords]
                entity = msp.add_lwpolyline(
                    coords,
                    close=False,
                    dxfattribs={"layer": obj.layer_key},
                )
                _set_xdata(
                    entity,
                    obj,
                    entity_role="centerline",
                    part_index=part_index,
                    ring_index=0,
                    ring_role="none",
                )
                entity_count += 1
        elif obj.representation_kind == "point_marker":
            if geometry.geom_type != "Point":
                raise ValueError(
                    f"unsupported point marker geometry: {geometry.geom_type}"
                )
            x, y = float(geometry.x), float(geometry.y)
            circle = msp.add_circle(
                (x, y),
                radius=0.25,
                dxfattribs={"layer": obj.layer_key},
            )
            _set_xdata(
                circle,
                obj,
                entity_role="point_marker",
                part_index=0,
                ring_index=0,
                ring_role="none",
            )
            label = msp.add_text(
                obj.object_id,
                height=0.35,
                dxfattribs={"layer": "ANNO-DIM"},
            )
            label.dxf.insert = (x + 0.3, y + 0.3)
            _set_xdata(
                label,
                obj,
                entity_role="point_marker_label",
                part_index=0,
                ring_index=0,
                ring_role="none",
            )
            entity_count += 2
        else:
            raise ValueError(
                f"unsupported representation kind: {obj.representation_kind}"
            )

    doc.saveas(out_path)
    audit = doc.audit()
    content_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    return DxfCompileResult(
        dxf_path=str(out_path),
        entity_count=entity_count,
        audit_errors=len(audit.errors),
        audit_fixes=len(audit.fixes),
        sha256=content_hash,
    )
