import json
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AuthorizedAction:
    playbook: str
    target_id: str
    target_host: str
    service_id: str
    service_name: str
    critical: bool

def _json_map(name):
    try:
        value = json.loads(os.getenv(name, "{}"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must contain a JSON object") from exc
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise RuntimeError(f"{name} must map string IDs to string values")
    return value

def authorize(playbook, target_id, service_id=""):
    targets = _json_map("ALLOWED_TARGETS_JSON")
    services = _json_map("ALLOWED_SERVICES_JSON")
    if playbook not in {"ping", "restart_service"}:
        raise ValueError("Playbook not allowed")
    if target_id not in targets:
        raise ValueError("Target not allowed")
    if playbook == "ping":
        if service_id:
            raise ValueError("Ping must not specify a service")
        return AuthorizedAction(playbook, target_id, targets[target_id], "", "", False)
    if service_id not in services:
        raise ValueError("Service not allowed")
    return AuthorizedAction(playbook, target_id, targets[target_id], service_id, services[service_id], True)
