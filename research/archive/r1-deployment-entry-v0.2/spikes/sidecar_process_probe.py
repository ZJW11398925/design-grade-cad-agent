from __future__ import annotations
import json, os, sys
from pathlib import Path
from dgcad_deployment import (
    BridgeRegistry, CapabilityAuthority, EndpointRegistry, PairingBroker,
    ProjectLeaseStore, SidecarLifecycleHost,
)

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
lease = ProjectLeaseStore(root / "project.db")
auth = CapabilityAuthority()
pairing = PairingBroker(auth)
host = SidecarLifecycleHost(
    project_id="P-PROBE", instance_id="I-PROBE", lease_store=lease,
    discovery=EndpointRegistry(root / "runtime.json"), authority=auth,
    pairing=pairing, bridges=BridgeRegistry(), lease_ttl_seconds=30,
)
try:
    desc = host.start()
    pair_token, grant = host.mint_pairing(role="agent", actor_id="probe-agent", ttl_seconds=30)
    handoff = root / "agent.pairing"
    handoff.write_text(pair_token, encoding="utf-8")
    try: os.chmod(handoff, 0o600)
    except OSError: pass
    print(json.dumps({"status":"ready","base_url":desc.base_url,"pairing_id":grant.pairing_id}), flush=True)
    sys.stdin.readline()
finally:
    host.stop()
    lease.close()
