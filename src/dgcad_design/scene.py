from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dgcad_foundation import (
    AuthorityState,
    CanonicalObject,
    RevisionStamp,
    SceneState,
    World,
)

from .basis import DesignBasis


@dataclass(frozen=True)
class DesignElement:
    element_id: str
    object_class: str
    layer_key: str
    representation_kind: str
    geometry: dict[str, Any]
    text: str | None = None
    text_height: float = 0.0
    rotation: float = 0.0
    massing: dict[str, Any] | None = None
    source_trace_ref: str | None = None
    annotation_role: str | None = None

    def to_canonical_object(
        self, basis: DesignBasis
    ) -> CanonicalObject:
        values: dict[str, Any] = {
            "geometry": self.geometry,
            "layer_key": self.layer_key,
            "representation_kind": self.representation_kind,
            "design_basis_id": basis.basis_id,
            "design_authority": basis.design_authority,
            "human_confirmed": False,
            "confirmation_scope": "design_draft",
            "source_trace_ref": self.source_trace_ref,
            "annotation_role": self.annotation_role,
        }
        if self.object_class == "building":
            values["professional_footprint"] = self.geometry
            values["height"] = {
                "value": basis.building_height_m(),
                "unit": "metre",
                "state": "proposed",
                "source_ref": basis.basis_id,
            }
            values["base_elevation"] = {
                "value": 0.0,
                "unit": "metre",
                "state": "proposed",
                "source_ref": basis.basis_id,
            }
        if self.text is not None:
            values["text"] = self.text
            values["text_height"] = self.text_height
            values["rotation"] = self.rotation
        return CanonicalObject(
            object_id=self.element_id,
            object_class=self.object_class,
            revisions=RevisionStamp(1, 1, 1),
            authority_state=AuthorityState.RULE_DERIVED,
            values=values,
        )


def design_scene(
    elements: tuple[DesignElement, ...],
    basis: DesignBasis,
    *,
    scene_id: str,
) -> SceneState:
    objects = {
        element.element_id: element.to_canonical_object(basis)
        for element in elements
    }
    if len(objects) != len(elements):
        raise ValueError("duplicate design element IDs")
    return SceneState(
        scene_id=scene_id,
        scene_revision=1,
        objects=objects,
        world=World.PROPOSAL_PREVIEW,
    )


def scene_objects_for_export(
    scene: SceneState,
) -> list[dict[str, Any]]:
    return [
        {
            "object_id": obj.object_id,
            "object_class": obj.object_class,
            "authority_state": obj.authority_state.value,
            "values": obj.values,
        }
        for obj in sorted(scene.objects.values(), key=lambda item: item.object_id)
    ]
