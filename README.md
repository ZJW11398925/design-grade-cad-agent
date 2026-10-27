# Design-Grade CAD Agent (DGCAD)

[![CI](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJW11398925/design-grade-cad-agent/actions/workflows/ci.yml)

**A traceable research-and-development workspace for turning hand-drawn site sketches into professional, verifiable site models and editable CAD/BIM output.**

> **Status: research prototype (v0.6.0).** This is not production CAD software, not a compliance certification, and not a validated AutoCAD/FreeCAD integration. Claims are scoped to the tests and evidence recorded in this repository.

---

## 1. The problem

A designer supplies a rough site sketch with buildings, roads, green space and boundaries. The system must:

1. preserve the original sketch and a faithful trace as immutable evidence;
2. extract semantic intent and resolve it into topology-correct professional geometry;
3. produce an early lightweight 3D massing with explicit height/floor provenance;
4. support shadow, obstruction and planning-rule feedback;
5. export editable, independently verifiable DXF/IFC;
6. keep every object traceable from source to delivery, including revisions, authority, locks and staleness;
7. reserve a deterministic rule layer for national, industry, local and design-office standards.

The hard part is not drawing. It is **truth ownership, identity, authority, dependency and verification**.

## 2. Architecture in one screen

```text
DATA PLANE
  Source evidence
    -> Trace geometry
      -> Intent candidate
        -> Professional candidate
          -> Canonical Site Model        (single confirmed design truth)
            -> Derived 3D / analysis
              -> DXF / IFC / renderings  (derived, invalidatable)

CONTROL PLANE
  Agent proposal
    -> authority check
      -> deterministic tool execution
        -> rule / profile resolution
          -> validator
            -> human confirmation where required
              -> canonical commit
                -> stale propagation / local rebuild
```

Core invariants:

- **Source and Trace are never overwritten** by professionalization.
- **The Agent never writes confirmed design state.** It proposes; deterministic engines compute; humans confirm.
- **DXF/IFC are adapters, not the database.** External edits re-enter only through reconcile proposals.
- **Unknown is a valid state.** Missing scale, height, road class or rule applicability is surfaced, never silently defaulted.
- **Every derived artifact carries a dependency fingerprint** and becomes stale when its inputs change.
- **Validation is layered and scoped.** A file that opens is not a design that complies.

The provisional architecture defines 11 modules (M01 Source & Calibration through M11 Agent), a typed Canonical Site IR, a three-world model (`canonical_current` / `proposal_preview` / `external`), and an authority matrix separating Agent, deterministic engine, rule engine, validator and human reviewer. See [docs/architecture/overview.md](docs/architecture/overview.md).

## 3. Current evidence base

| Area | State | Evidence |
|---|---|---|
| Foundation contracts | implemented, 21 tests | stable identity, three revision axes, authority/locks, AtomicChangeSet, ProposalSnapshot, dependency/stale, canonical hash, audit, migration, AgentGateway |
| Stateful runtime | implemented, 22 tests | proposals, approvals, jobs, artifacts, idempotency, restart recovery, stale-writer CAS |
| Deployment boundary | implemented, 8 tests | SQLite/WAL spike, content-addressed artifact store, CLI/service parity |
| Local sidecar lifecycle | implemented, 14 tests | token-free discovery, role-bound pairing, sessions, loopback HTTP, project lease, CAD bridge registry, child-process probe |
| Domain slice 001 | implemented, 26 tests | confirmed trace → Building/Road canonical objects; proposal/preview/commit; T-junction atomic change set; stale massing/surface; structured validators |
| E2E-001 living pipeline | implemented, 8 tests + 9 CAD tests | Domain → massing → shadow → CAD-IR → DXF → readback, using living packages only; bulge/width and full LWPOLYLINE checks now positive |
| E2E-002 mutation/rebuild | implemented, 6 tests | height change, T-junction move, north bearing, real rebuild worker, manifest comparison; road surface deferred |
| E2E-003 adversarial delivery | implemented, 20 tests (all pass) | geometry, style, identity, serialization and validator-error checks; same-library only |
| R0 research | archived | 5 acquisition batches, synthetic benchmarks, adversarial reviews, architecture challenge |
| Real-world evidence | **not yet obtained** | real site sketches, real design-office profile, IFC round-trip, independent solar engine, AutoCAD/FreeCAD host exchange, MCP wire conformance |

**Verified test baseline: 141 passed (141 collected)** (`python -m pytest -q`).

### Explicit non-claims

- No MCP wire-level conformance: the official MCP Python SDK was unavailable in the research environment.
- No real AutoCAD or FreeCAD host message exchange: only a generic loopback bridge lifecycle was executed.
- No production database decision: SQLite/WAL is a local-sidecar candidate only.
- No production security approval: session authority is in-memory; Windows ACL/DPAPI, installer trust and same-user malware resistance are out of scope.
- No Chinese road/building daylight compliance claim: standard clauses were not fully obtained and no numeric design defaults were frozen.
- No third-party CAD round-trip in E2E-001/002/003: both compile and readback use ezdxf, so this is same-library evidence only; DEV-CAD-006 remains open.
- Remaining open validator/dependency gaps: `DEV-CAD-001/004/005/008/011` (#1/#4/#5/#8/#16). No permanent xfails remain.
- Road surface geometry is deferred in E2E-002: no `SURFACE-R-002` artifact is registered or presented as generated road surface.

## 4. Repository layout

```text
.
├── src/
│   ├── dgcad_foundation/      Canonical IR, authority, dependency, audit, gateway
│   ├── dgcad_runtime/         Stateful runtime, proposals, jobs, idempotency, human control plane
│   ├── dgcad_deployment/      SQLite/artifact spike, lifecycle, discovery, pairing, local HTTP
│   ├── dgcad_domain/          Confirmed trace → Building/Road adapters and validators
│   ├── dgcad_analysis/        Synthetic solar/shadow baseline with dependency fingerprint
│   ├── dgcad_cad/             CAD-IR, DXF compiler, readback validator
│   └── dgcad_e2e/             Living end-to-end pipeline orchestration
├── tests/                     Executable contract suites (141 collected)
├── contracts/                 Machine-readable IR, domain, E2E, lifecycle/auth/MCP/CAD bridge contracts
├── fixtures/                  Typed synthetic fixtures (scene, authority, dependency, domain, E2E)
├── spikes/                    Executed process probe and MCP install-attempt evidence
├── docs/
│   ├── architecture/          Provisional architecture and module boundaries
│   ├── development/           Testing strategy and contribution workflow
│   ├── adr/                   Architecture decision records
│   ├── status.md              Current gate/status matrix
│   └── roadmap.md             Milestones and next actions
├── research/
│   ├── README.md              Provenance and scope of the research archive
│   └── archive/
│       ├── r0-v0.19/          Full R0 research workspace
│       └── r1-deployment-entry-v0.2/  Original R1 deployment snapshot
├── scripts/                   Local test runners
├── pyproject.toml
├── LICENSE                    Apache-2.0
└── README.md
```

The root `src/` and `tests/` are the **living code**. `research/archive/` is historical evidence and may contain outdated paths and status labels.

## 5. Quick start

```bash
git clone https://github.com/ZJW11398925/design-grade-cad-agent.git
cd design-grade-cad-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

python -m pip install -e ".[dev]"
python -m pytest -q
```

Expected:

```text
141 passed
```

With coverage:

```bash
python -m pytest -q --cov --cov-report=term-missing
```

## 6. Test suites

| Suite | File | Tests | Contract scope |
|---|---|---|---|
| Foundation | `tests/test_foundation_contracts.py` | 21 | identity, revisions, authority, atomic changes, preview isolation, dependency, locks, audit, migration |
| Runtime | `tests/test_runtime_contracts.py` | 22 | proposal lifecycle, approval binding, jobs, idempotency, recovery, stale writer, CLI/MCP parity |
| Deployment | `tests/test_deployment_contracts.py` | 8 | SQLite WAL/CAS, artifact dedup/tamper, service parity, MCP-unverified marking |
| Lifecycle | `tests/test_lifecycle_contracts.py` | 14 | discovery, pairing, roles, sessions, loopback security, lease, bridge expiry |
| Domain | `tests/test_domain_contracts.py` | 26 | confirmed trace, building footprint/height, road class/profile, T-junction, stale, runtime integration |
| Analysis | `tests/test_analysis_contracts.py` | 7 | solar position, confirmed/unknown blockers, context completeness, dependency fingerprint |
| CAD delivery | `tests/test_cad_delivery_contracts.py` | 9 | CAD-IR mapping, DXF compile/readback, mutation detection, bulge/width/LWPOLYLINE semantics |
| E2E-001 | `tests/e2e/test_living_pipeline.py` | 8 | full living pipeline, evidence files, declared unknowns, living-package-only check |
| E2E-002 | `tests/e2e/test_e2e_002_mutations.py` | 6 | height change, node move, north bearing, rebuild worker, manifest comparison, road-surface deferral |
| E2E-003 | `tests/e2e/test_e2e_003_adversarial.py` | 20 | geometry, style, identity, serialization, validator-error checks |
| **Total** | | **141 (all passing)** | |

Read [docs/development/testing.md](docs/development/testing.md) for what these tests prove, what they do **not** prove, and how new test layers are added.

## 7. Contracts

| File | Purpose |
|---|---|
| `contracts/runtime-state-contract-v0.1.yaml` | Durable runtime state envelope and registry semantics |
| `contracts/runtime-agent-surface-v0.1.yaml` | Agent tool surface; no approval/unlock tool |
| `contracts/deployment-boundary-contract-v0.2.yaml` | Sidecar / bridge / control-plane boundary |
| `contracts/sidecar-lifecycle-contract-v0.1.yaml` | Discovery, pairing, session and lease lifecycle |
| `contracts/local-auth-capability-contract-v0.1.yaml` | Role/capability model for Agent, Human Review, CAD Bridge |
| `contracts/cad-bridge-contract-v0.1.yaml` | External CAD representation authority |
| `contracts/cad-bridge-lifecycle-contract-v0.2.yaml` | Bridge registration, heartbeat, expiry; host execution blockers |
| `contracts/canonical-site-ir-v0.4.yaml` | Living Canonical Site IR promoted from R0 v0.3 |
| `contracts/domain-contract-v0.1.yaml` | Living Building/Road domain contract for domain slice 001 |
| `contracts/cad-ir-v0.1.yaml` | Minimal living CAD-IR for the E2E delivery slice |
| `contracts/e2e-pipeline-v0.1.yaml` | Living E2E-001 stage and invariant contract |
| `contracts/e2e-mutation-v0.1.yaml` | E2E-002 mutation, rebuild and manifest-comparison contract |
| `contracts/e2e-adversarial-v0.1.yaml` | E2E-003 adversarial scenario, category and issue-mapping contract |
| `contracts/evidence-gate-register-v0.2.yaml` | Living R1 evidence gate register; packages remain planned |
| `contracts/mcp-binding-v0.3.yaml` | MCP binding candidate; wire-level status remains unexecuted |

The promotion status of every research artifact is tracked in [docs/research-to-product-map.md](docs/research-to-product-map.md). Archive documents are not living contracts.

## 8. Next milestone

**Milestone 3 — CAD validator hardening.** Milestones 0/1/2a/2b/2c are complete: the workspace, domain slice, living pipeline, scoped mutation/rebuild and adversarial delivery regression all have CI evidence. The next step is to implement `DEV-CAD-001..011` and add a repeatable third-party CAD round-trip matrix. Real sketch, road engineering, IFC and standards compliance remain separate evidence packages.

See [docs/roadmap.md](docs/roadmap.md) for the milestone plan and exit criteria.

## 9. Research provenance

This repository consolidates two research deliverables:

- **R0 v0.19** — research workspace covering `COV-01..23`, five acquisition batches, local synthetic benchmarks, E2E synthetic vertical slice and the provisional architecture.
- **R1 deployment-entry v0.2** — the executable Foundation + Runtime + Deployment + Lifecycle prototype (65 tests).

The vendored copy of the private research-methodology skill is intentionally **not** published; only its version is recorded in [research/README.md](research/README.md).

## 10. Contributing

Tests come first. Any contract change requires the contract YAML, the executable test and `CHANGELOG.md` to change together. Research claims stay in `research/`; code claims stay in tests.

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [SECURITY.md](SECURITY.md)
- [docs/development/workflow.md](docs/development/workflow.md)

## 11. License

Apache-2.0. See [LICENSE](LICENSE).

---

## 中文简介

**Design-Grade CAD Agent（DGCAD）** 是一个以研究为先导的开源工作区，目标是建立一条可追溯的 **草图 → 专业场地模型 → CAD/BIM** 转换链。

当前仓库整合了 R0 v0.19 研究证据、R1 部署生命周期原型、Domain Slice 001、E2E-001 纵向链路、E2E-002 mutation/rebuild 与 E2E-003 对抗性交付回归：根目录 `src/`、`tests/` 是可执行的正式代码，`research/archive/` 保存历史研究快照。当前 141 个测试全部通过，无长期 xfail。

项目坚持四条底线：原始 Source/Trace 不可覆盖；Agent 只能提议、不能写入 confirmed 设计真值；DXF/IFC 只是派生表示；未知状态必须显式保留。真实草图、真实设计院 Profile、IFC round-trip、独立日照引擎与真实 AutoCAD/FreeCAD 宿主接入仍是明确的证据缺口，仓库不会把合成测试包装成生产能力。

E2E-001/002/003 已打通：DOMAIN-SLICE-001 → Runtime canonical → massing → 合成 shadow → CAD-IR → DXF → readback manifest，验证了高度/节点/北向的 scoped stale 与真实 rebuild。Milestone 3a 已把 15 个 strict xfail 全部转为正向检查：结构化 validator_error、实体样式覆盖、CIRCLE/TEXT 3D 与文本策略、LWPOLYLINE 全语义。下一步是 3b 的符号表/依赖指纹/环身份与 3c 的第三方 CAD round-trip；真实草图、道路面几何和规范合规仍是独立证据缺口。
