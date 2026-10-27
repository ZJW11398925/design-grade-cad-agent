from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from shapely.geometry import box

from dgcad_analysis import (
    ShadowBlocker,
    ShadowConfig,
    ShadowSample,
    evaluate_sample,
    run_shadow_baseline,
    solar_position_noaa,
    sun_vector_project,
)
from dgcad_domain import (
    build_initial_scene,
    building_proposal,
    load_confirmed_trace_fixture,
    road_corridor_proposal,
)
from dgcad_foundation import ActorContext, AtomicChangeSet, CanonicalStore, RevisionStamp

DOMAIN_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "domain"
    / "domain-slice-001-r2.yaml"
)
E2E_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "e2e"
    / "living-pipeline-001.yaml"
)
HUMAN = ActorContext("designer-1", is_human=True, can_unlock=True)


@pytest.fixture(scope="module")
def trace_scene():
    return load_confirmed_trace_fixture(DOMAIN_FIXTURE)


@pytest.fixture(scope="module")
def analysis_config():
    data = yaml.safe_load(E2E_FIXTURE.read_text(encoding="utf-8"))
    return ShadowConfig.from_dict(data["analysis"])


@pytest.fixture(scope="module")
def committed_scene(trace_scene):
    store = CanonicalStore(build_initial_scene(trace_scene))
    for building_id in ("B-001", "B-002", "B-003"):
        proposal = building_proposal(
            store.current,
            trace_scene,
            building_id,
            proposal_id=f"P-{building_id}",
            confirm=True,
        )
        store.commit(AtomicChangeSet(f"CS-{building_id}", (proposal,)), HUMAN)
    road = road_corridor_proposal(
        store.current, trace_scene, "R-002", proposal_id="P-R002", confirm=True
    )
    store.commit(AtomicChangeSet("CS-R002", (road,)), HUMAN)
    return store.current


def test_solar_position_matches_known_sydney_example(analysis_config):
    position = solar_position_noaa(
        analysis_config.latitude_deg,
        analysis_config.longitude_deg,
        analysis_config.local_datetime,
    )
    assert position.elevation_deg == pytest.approx(72.0467, abs=1e-3)
    assert position.azimuth_deg == pytest.approx(32.3093, abs=1e-3)


def test_solar_position_requires_timezone():
    with pytest.raises(ValueError):
        solar_position_noaa(-33.87, 151.22, datetime(2025, 11, 15, 11, 0))


def test_sun_vector_respects_project_north_bearing():
    east = sun_vector_project(90.0, 0.0, 0.0)
    assert east == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)
    north_after_rotation = sun_vector_project(90.0, 0.0, 90.0)
    assert north_after_rotation == pytest.approx((0.0, 1.0, 0.0), abs=1e-9)
    with pytest.raises(ValueError):
        sun_vector_project(90.0, 0.0, float("nan"))


def test_shadow_sample_statuses_are_explicit(committed_scene, analysis_config):
    result = run_shadow_baseline(committed_scene, analysis_config)
    statuses = {sample.sample_id: sample.status for sample in result.samples}
    assert statuses["SAMPLE-01"] == "confirmed_sunlit_given_declared_context"
    assert statuses["SAMPLE-02"] == "confirmed_shaded"
    assert statuses["SAMPLE-03"] == "unknown_obstruction_height"
    assert statuses["SAMPLE-04"] == "confirmed_sunlit_given_declared_context"
    shaded = next(
        sample for sample in result.samples if sample.sample_id == "SAMPLE-02"
    )
    assert shaded.blocker_ids == ("B-001",)
    unknown = next(
        sample for sample in result.samples if sample.sample_id == "SAMPLE-03"
    )
    assert unknown.blocker_ids == ("B-002",)
    assert result.status == "bounded_or_unknown"


def test_confirmed_blocker_and_unknown_blocker_semantics():
    confirmed = ShadowBlocker(
        object_id="B-CONFIRMED",
        footprint=box(1.0, 0.0, 2.0, 2.0),
        base_elevation_m=0.0,
        height_m=10.0,
        height_state="confirmed",
        geometry_revision=1,
        parameter_revision=1,
    )
    sample = ShadowSample("S", 0.0, 1.0)
    shaded = evaluate_sample(
        sample,
        (confirmed,),
        (1.0, 0.0, 0.2),
        sensor_height_m=0.0,
        context_complete=True,
    )
    assert shaded.status == "confirmed_shaded"

    unknown = ShadowBlocker(
        object_id="B-UNKNOWN",
        footprint=box(1.0, 0.0, 2.0, 2.0),
        base_elevation_m=0.0,
        height_m=None,
        height_state="unknown",
        geometry_revision=1,
        parameter_revision=1,
    )
    unknown_result = evaluate_sample(
        sample,
        (unknown,),
        (1.0, 0.0, 0.2),
        sensor_height_m=0.0,
        context_complete=True,
    )
    assert unknown_result.status == "unknown_obstruction_height"
    assert unknown_result.blocker_ids == ("B-UNKNOWN",)


def test_incomplete_context_is_bounded_unknown(committed_scene, analysis_config):
    config = replace(analysis_config, context_complete=False)
    result = run_shadow_baseline(committed_scene, config)
    assert result.status == "bounded_or_unknown"
    assert any(
        sample.status == "incomplete_surrounding_context"
        for sample in result.samples
    )


def test_fingerprint_changes_when_building_parameter_revision_changes(
    committed_scene, analysis_config
):
    baseline = run_shadow_baseline(committed_scene, analysis_config)
    building = committed_scene.objects["B-001"]
    changed = replace(
        building,
        revisions=RevisionStamp(
            building.revisions.semantic,
            building.revisions.geometry,
            building.revisions.parameter + 1,
        ),
    )
    changed_scene = replace(
        committed_scene,
        objects={**committed_scene.objects, "B-001": changed},
    )
    mutated = run_shadow_baseline(changed_scene, analysis_config)
    assert baseline.dependency_fingerprint != mutated.dependency_fingerprint
