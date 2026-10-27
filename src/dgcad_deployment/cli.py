from __future__ import annotations

import argparse
import json
from typing import Callable

from .service import DeploymentService


def run_cli(service: DeploymentService, argv: list[str]) -> dict:
    parser = argparse.ArgumentParser(prog="dgcad")
    parser.add_argument("tool")
    parser.add_argument("--args-json", default="{}")
    parser.add_argument("--idempotency-key")
    ns = parser.parse_args(argv)
    args = json.loads(ns.args_json)
    return service.invoke(ns.tool, args, idempotency_key=ns.idempotency_key)


def main(service_factory: Callable[[], DeploymentService] | None = None) -> int:
    if service_factory is None:
        raise RuntimeError("CLI_REQUIRES_HOST_RUNTIME_FACTORY")
    result = run_cli(service_factory(), __import__('sys').argv[1:])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0
