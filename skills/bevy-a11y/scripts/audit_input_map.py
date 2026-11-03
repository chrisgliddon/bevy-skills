#!/usr/bin/env python3
"""Audit a device-neutral game action manifest for accessibility coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_SETTINGS = {
    "hotplug",
    "simultaneous_devices",
    "multiple_devices_per_player",
    "prompt_updates",
    "capture_unknown_controls",
    "adjustable_deadzone",
    "adjustable_sensitivity",
    "invert_axes",
}

DEMAND_ALTERNATIVES = {
    "hold": {"toggle", "adjustable_hold", "automatic"},
    "mash": {"hold", "toggle", "automatic"},
    "chord": {"sequential", "single_binding", "automatic"},
    "tight_timing": {"adjustable_timing", "slowdown", "retry", "automatic"},
    "precision_analog": {"digital", "snap", "assist", "automatic"},
}


def issue(level: str, code: str, path: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "path": path, "message": message}


def audit(data: Any) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not isinstance(data, dict):
        return [issue("error", "schema", "$", "manifest root must be an object")]

    if data.get("version") != 1:
        findings.append(issue("error", "version", "$.version", "supported version is 1"))

    required_devices = data.get("required_devices", ["keyboard", "gamepad"])
    if not isinstance(required_devices, list) or not all(
        isinstance(item, str) and item for item in required_devices
    ):
        findings.append(
            issue("error", "schema", "$.required_devices", "must be an array of device names")
        )
        required_devices = []
    required_devices = list(dict.fromkeys(required_devices))

    settings = data.get("settings", {})
    if not isinstance(settings, dict):
        findings.append(issue("error", "schema", "$.settings", "must be an object"))
        settings = {}
    for setting in sorted(REQUIRED_SETTINGS):
        if settings.get(setting) is not True:
            findings.append(
                issue(
                    "warning",
                    "setting",
                    f"$.settings.{setting}",
                    "highest-standard input policy expects this setting to be true",
                )
            )

    actions = data.get("actions")
    if not isinstance(actions, list) or not actions:
        findings.append(issue("error", "schema", "$.actions", "must be a non-empty array"))
        return findings

    ids: set[str] = set()
    bindings_by_context: dict[tuple[str, str, str], list[tuple[str, bool]]] = defaultdict(list)

    for index, action in enumerate(actions):
        base = f"$.actions[{index}]"
        if not isinstance(action, dict):
            findings.append(issue("error", "schema", base, "action must be an object"))
            continue

        action_id = action.get("id")
        if not isinstance(action_id, str) or not action_id:
            findings.append(issue("error", "action-id", f"{base}.id", "must be a non-empty string"))
            action_id = f"<action-{index}>"
        elif action_id in ids:
            findings.append(issue("error", "action-id", f"{base}.id", f"duplicate action id {action_id!r}"))
        ids.add(action_id)

        contexts = action.get("contexts")
        if not isinstance(contexts, list) or not contexts or not all(
            isinstance(item, str) and item for item in contexts
        ):
            findings.append(issue("error", "contexts", f"{base}.contexts", "must contain at least one context"))
            contexts = []

        essential = action.get("essential", False)
        if not isinstance(essential, bool):
            findings.append(issue("error", "schema", f"{base}.essential", "must be boolean"))
            essential = False
        if essential and action.get("remappable") is not True:
            findings.append(
                issue("warning", "remappable", f"{base}.remappable", "essential actions should be remappable")
            )

        bindings = action.get("bindings", [])
        if not isinstance(bindings, list):
            findings.append(issue("error", "schema", f"{base}.bindings", "must be an array"))
            bindings = []
        devices_present: set[str] = set()
        for binding_index, binding in enumerate(bindings):
            binding_path = f"{base}.bindings[{binding_index}]"
            if not isinstance(binding, dict):
                findings.append(issue("error", "schema", binding_path, "binding must be an object"))
                continue
            device = binding.get("device")
            control = binding.get("control")
            if not isinstance(device, str) or not device:
                findings.append(issue("error", "binding", f"{binding_path}.device", "must be a device name"))
                continue
            if not isinstance(control, str) or not control:
                findings.append(issue("error", "binding", f"{binding_path}.control", "must be a stable control id"))
                continue
            devices_present.add(device)
            allow_conflict = binding.get("allow_conflict", False)
            if not isinstance(allow_conflict, bool):
                findings.append(issue("error", "schema", f"{binding_path}.allow_conflict", "must be boolean"))
                allow_conflict = False
            for context in contexts:
                bindings_by_context[(context, device, control)].append((action_id, allow_conflict))

        excluded = action.get("excluded_devices", [])
        if not isinstance(excluded, list) or not all(isinstance(item, str) for item in excluded):
            findings.append(issue("error", "schema", f"{base}.excluded_devices", "must be an array of strings"))
            excluded = []
        if essential:
            for device in required_devices:
                if device not in excluded and device not in devices_present:
                    findings.append(
                        issue(
                            "warning",
                            "device-coverage",
                            f"{base}.bindings",
                            f"essential action {action_id!r} has no {device!r} binding",
                        )
                    )

        input_kind = action.get("input_kind", "digital")
        if input_kind in {"analog_1d", "analog_2d", "pointer_delta"} and action.get(
            "digital_alternative"
        ) is not True:
            findings.append(
                issue(
                    "warning",
                    "analog-alternative",
                    f"{base}.digital_alternative",
                    "analog/pointing action should expose a digital alternative",
                )
            )

        demands = action.get("demands", [])
        alternatives = action.get("alternatives", [])
        if not isinstance(demands, list) or not all(isinstance(item, str) for item in demands):
            findings.append(issue("error", "schema", f"{base}.demands", "must be an array of strings"))
            demands = []
        if not isinstance(alternatives, list) or not all(
            isinstance(item, str) for item in alternatives
        ):
            findings.append(issue("error", "schema", f"{base}.alternatives", "must be an array of strings"))
            alternatives = []
        alternative_set = set(alternatives)
        for demand in demands:
            accepted = DEMAND_ALTERNATIVES.get(demand)
            if accepted is None:
                findings.append(issue("warning", "unknown-demand", f"{base}.demands", f"unknown demand {demand!r}"))
            elif not (accepted & alternative_set):
                findings.append(
                    issue(
                        "warning",
                        "mechanic-alternative",
                        f"{base}.alternatives",
                        f"{demand!r} needs one of {sorted(accepted)}",
                    )
                )

    for (context, device, control), uses in sorted(bindings_by_context.items()):
        action_ids = sorted({action_id for action_id, _ in uses})
        if len(action_ids) > 1 and not all(allowed for _, allowed in uses):
            findings.append(
                issue(
                    "warning",
                    "binding-conflict",
                    "$.actions",
                    f"{context}/{device}/{control} is bound to {', '.join(action_ids)} without explicit conflict allowance",
                )
            )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    parser.add_argument("--strict", action="store_true", help="fail on warnings as well as errors")
    args = parser.parse_args()

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    findings = audit(data)
    if args.json:
        print(json.dumps({"manifest": str(args.manifest), "findings": findings}, indent=2))
    else:
        for finding in findings:
            print(
                f"{finding['level'].upper()} {finding['code']} {finding['path']}: "
                f"{finding['message']}"
            )
        if not findings:
            print("OK: input manifest passed all checks")

    has_errors = any(item["level"] == "error" for item in findings)
    has_warnings = any(item["level"] == "warning" for item in findings)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
