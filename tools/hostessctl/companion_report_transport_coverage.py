"""Transport coverage summary rows for companion report projections."""

from __future__ import annotations

from typing import Any


def project_transport_coverage_rows(
    projected_rows: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not projected_rows or not sources:
        return []

    coverage = transport_coverage(projected_rows)
    if not coverage["items"]:
        return []

    status = transport_coverage_status(coverage["items"])
    explicit_terms = {
        "websocket": bool(coverage["websocket"]),
        "tcp": bool(coverage["tcp"]),
        "wifi_direct": bool(coverage["wifi_direct"]),
    }
    term_gates = transport_term_gates(coverage)
    remaining_live_gates = transport_remaining_live_gates(term_gates)
    notes = (
        f"websocket={coverage_state(coverage['websocket'])}; "
        f"tcp={coverage_state(coverage['tcp'])}; "
        f"wifi_direct={coverage_state(coverage['wifi_direct'])}; "
        f"wifi_topologies={coverage_state(coverage['wifi_topologies'])}; "
        f"remaining={coverage_state({str(gate['gate_id']) for gate in remaining_live_gates})}"
    )
    return [
        row(
            "transport_coverage.summary",
            "transport_coverage",
            "transport_coverage_summary",
            "Transport coverage",
            status,
            sources[0],
            authority_owner="source_artifacts",
            evidence=(
                f"families={coverage_state(coverage['families'], limit=20)}; "
                f"topologies={coverage_state(coverage['topologies'])}; "
                f"probes={coverage_state(coverage['probe_ids'], limit=20)}"
            ),
            notes=notes,
            details={
                "families": sorted(coverage["families"]),
                "topologies": sorted(coverage["topologies"]),
                "wifi_topologies": sorted(coverage["wifi_topologies"]),
                "probe_ids": sorted(coverage["probe_ids"]),
                "explicit_terms": explicit_terms,
                "term_gates": term_gates,
                "remaining_live_gates": remaining_live_gates,
                "items": coverage["items"],
            },
        )
    ]


def transport_coverage(projected_rows: list[dict[str, Any]]) -> dict[str, Any]:
    coverage: dict[str, Any] = {
        "families": set(),
        "topologies": set(),
        "wifi_topologies": set(),
        "probe_ids": set(),
        "websocket": set(),
        "tcp": set(),
        "wifi_direct": set(),
        "items": [],
    }

    for projected_row in projected_rows:
        details = object_value(projected_row.get("details"))
        tokens: set[str] = set()
        add_detail_tokens(tokens, details)

        probe_id = str(details.get("probe_id") or "")
        if not probe_id:
            probe_id = probe_id_from_row_id(str(projected_row.get("row_id") or ""))
        if probe_id:
            coverage["probe_ids"].add(probe_id)

        status = str(projected_row.get("status") or "unknown")
        family_values = family_tokens(tokens)
        topology_values = topology_tokens(details)
        if not family_values and not topology_values:
            continue

        coverage["families"].update(family_values)
        coverage["topologies"].update(topology_values)
        coverage["wifi_topologies"].update(
            value
            for value in topology_values | family_values
            if "wifi" in value or "hotspot" in value
        )
        item = {
            "row_id": projected_row.get("row_id"),
            "status": status,
            "kind": projected_row.get("kind"),
            "evidence_tier": projected_row.get("evidence_tier"),
            "promotion_state": details.get("promotion_state"),
            "families": sorted(family_values),
            "topologies": sorted(topology_values),
            "probe_id": probe_id,
            **product_gate_details(details),
        }
        coverage["items"].append(item)

        haystack = " ".join(sorted(tokens | family_values | topology_values)).lower()
        if "websocket" in haystack:
            coverage["websocket"].add(str(projected_row.get("row_id") or "websocket"))
        if "tcp" in haystack:
            coverage["tcp"].add(str(projected_row.get("row_id") or "tcp"))
        if "wifi_direct" in haystack or "wi-fi direct" in haystack:
            coverage["wifi_direct"].add(str(projected_row.get("row_id") or "wifi_direct"))

    return coverage


def transport_term_gates(coverage: dict[str, Any]) -> dict[str, Any]:
    items = list(coverage["items"])
    return {
        "websocket": term_gate(
            "websocket",
            coverage["websocket"],
            scope="manifold_command_session_receipts",
            promotion_boundary=(
                "Current WebSocket coverage is the Manifold command/session "
                "receipt route, not a generic WebSocket data-plane slot."
            ),
            items=items,
        ),
        "tcp": term_gate(
            "tcp",
            coverage["tcp"],
            scope="qcl010_qcl011_echo_and_qcl082_tcp_binary_media",
            promotion_boundary=(
                "TCP visibility covers topology echo and QCL-082 binary media; "
                "product TCP over direct Wi-Fi needs a live topology/listener gate."
            ),
            items=items,
        ),
        "wifi_direct": term_gate(
            "wifi_direct",
            coverage["wifi_direct"],
            scope="qcl040_qcl041_topology_evidence",
            promotion_boundary=(
                "Wi-Fi Direct is topology evidence and remains experimental until "
                "live peer discovery, group lifecycle, socket exchange, and cleanup "
                "evidence promote it."
            ),
            items=items,
        ),
    }


def term_gate(
    term: str,
    row_ids: set[str],
    *,
    scope: str,
    promotion_boundary: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    matching = [item for item in items if str(item.get("row_id") or "") in row_ids]
    statuses = {str(item.get("status") or "unknown") for item in matching}
    if term == "websocket" and generic_websocket_capability_state({"items": matching}) != "absent":
        scope = "manifold_command_session_receipts_and_qcl079_generic_protocol_fit"
        promotion_boundary = (
            "QCL-000 covers Manifold command/session receipts. QCL-079 covers "
            "generic WebSocket protocol fit and promotes only with broker-owned "
            "or Quest-runtime endpoint evidence."
        )
    return {
        "included": bool(row_ids),
        "scope": scope,
        "promotion_boundary": promotion_boundary,
        "state": term_state(matching, statuses),
        "source_row_ids": sorted(row_ids),
        "status_counts": status_counts(statuses, matching),
        "probe_ids": sorted({str(item.get("probe_id") or "") for item in matching if item.get("probe_id")}),
        "live_or_promoted": term_live_or_promoted(term, matching),
        "items": matching,
    }


def transport_remaining_live_gates(term_gates: dict[str, Any]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    websocket_gate = object_value(term_gates.get("websocket"))
    tcp_gate = object_value(term_gates.get("tcp"))
    wifi_direct_gate = object_value(term_gates.get("wifi_direct"))

    websocket_state = generic_websocket_capability_state(websocket_gate)
    if websocket_gate.get("included") and websocket_state != "proven":
        gates.append(
            {
                "gate_id": "transport.general_websocket_capability",
                "status": (
                    "pending_live_evidence"
                    if websocket_state == "candidate"
                    else "not_in_current_scope"
                ),
                "evidence": (
                    "QCL-079 generic WebSocket is visible as protocol-fit evidence, "
                    "but promotion still needs broker-owned or Quest-runtime endpoint evidence."
                    if websocket_state == "candidate"
                    else (
                        "Current WebSocket evidence is the Manifold command/session "
                        "receipt route. Add a dedicated protocol capability before "
                        "treating generic WebSocket as a data protocol."
                    )
                ),
            }
        )
    if wifi_direct_gate.get("included") and not wifi_direct_gate.get("live_or_promoted"):
        gates.append(
            {
                "gate_id": "transport.direct_wifi_live_topology",
                "status": "pending_live_evidence",
                "evidence": (
                    "QCL-040/QCL-041 are visible as Wi-Fi Direct topology rows, "
                    "but promotion still needs live peer lifecycle and cleanup evidence."
                ),
            }
        )
    if (
        tcp_gate.get("included")
        and wifi_direct_gate.get("included")
        and not product_tcp_media_over_direct_wifi_proven(
            list_value(tcp_gate.get("items")) + list_value(wifi_direct_gate.get("items"))
        )
    ):
        gates.append(
            {
                "gate_id": "transport.product_tcp_media_over_direct_wifi",
                "status": "pending_live_evidence",
                "evidence": (
                    "QCL-082 binary media and Wi-Fi Direct topology are separate "
                    "evidence families. Product TCP media over direct Wi-Fi needs "
                    "a live RMANVID1 receiver/listener run on the promoted topology."
                ),
            }
        )
    if tcp_gate.get("included") and not product_tcp_media_listener_firewall_proven(
        list_value(tcp_gate.get("items"))
    ):
        gates.append(
            {
                "gate_id": "transport.product_tcp_media_listener_firewall",
                "status": "pending_live_evidence",
                "evidence": (
                    "Product TCP media needs a verified Hostess/WPF inbound "
                    "listener firewall rule for the RMANVID1 receiver port. "
                    "Diagnostic Python listener firewall evidence is not enough."
                ),
            }
        )
    return gates


def term_state(items: list[dict[str, Any]], statuses: set[str]) -> str:
    if not items:
        return "not_included"
    if statuses & {"candidate", "planned", "skipped", "unknown", "missing"}:
        return "visible_candidate"
    if statuses & {"warn", "usable_with_warnings"}:
        return "visible_with_warnings"
    if statuses & {"pass", "usable"}:
        return "visible"
    if statuses & {"fail", "blocked", "rejected"}:
        return "blocked_or_failed"
    return "visible"


def status_counts(statuses: set[str], items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in statuses}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def term_live_or_promoted(term: str, items: list[dict[str, Any]]) -> bool:
    if term == "wifi_direct":
        return any(
            str(item.get("probe_id") or "") in {"QCL-040", "QCL-041"}
            and str(item.get("kind") or "") == "connectivity_promotion_gate"
            and str(item.get("status") or "") == "pass"
            for item in items
        )
    if term == "tcp":
        return tcp_media_promoted({"source_row_ids": [item.get("row_id") for item in items], "items": items})
    if term == "websocket":
        return any(
            (
                str(item.get("probe_id") or "") == "QCL-000"
                and str(item.get("promotion_state") or "") in {"promoted", "promoted_with_warnings"}
            )
            or str(item.get("row_id") or "").startswith("device_link.command_result.")
            for item in items
        )
    return False


def tcp_media_promoted(tcp_gate: dict[str, Any]) -> bool:
    for item in list_value(tcp_gate.get("items")):
        row = object_value(item)
        if str(row.get("probe_id") or "") != "QCL-082":
            continue
        if str(row.get("kind") or "") == "connectivity_promotion_gate" and str(row.get("status") or "") == "pass":
            return True
        if str(row.get("promotion_state") or "") in {"promoted", "promoted_with_warnings"}:
            return True
    return False


def product_tcp_media_over_direct_wifi_proven(items: list[Any]) -> bool:
    for item in items:
        row = object_value(item)
        if str(row.get("product_gate") or "") != "product_tcp_media_over_direct_wifi":
            continue
        if row.get("product_gate_proven") is True and str(row.get("status") or "") == "pass":
            return True
    return False


def product_tcp_media_listener_firewall_proven(items: list[Any]) -> bool:
    for item in items:
        row = object_value(item)
        if str(row.get("product_gate") or "") != "product_tcp_media_listener_firewall_verified":
            continue
        if row.get("product_gate_proven") is True and str(row.get("status") or "") == "pass":
            return True
    return False


def generic_websocket_capability_present(websocket_gate: dict[str, Any]) -> bool:
    return generic_websocket_capability_state(websocket_gate) != "absent"


def generic_websocket_capability_state(websocket_gate: dict[str, Any]) -> str:
    qcl079_items = [
        object_value(item)
        for item in list_value(websocket_gate.get("items"))
        if item_is_generic_websocket(object_value(item))
    ]
    qcl079_items = [
        item
        for item in qcl079_items
        if str(item.get("status") or "") not in {"", "missing", "unknown", "skipped"}
    ]
    if any(
        str(item.get("promotion_state") or "") in {"promoted", "promoted_with_warnings"}
        or (
            str(item.get("kind") or "") == "connectivity_promotion_gate"
            and str(item.get("status") or "") == "pass"
        )
        for item in qcl079_items
    ):
        return "proven"
    if qcl079_items:
        return "candidate"
    for row_id in list_value(websocket_gate.get("source_row_ids")):
        text = str(row_id).lower()
        if "qcl-079" in text or "qcl079" in text or "websocket_generic" in text:
            return "candidate"
        if "generic" in text:
            return "candidate"
    return "absent"


def item_is_generic_websocket(item: dict[str, Any]) -> bool:
    row_id = str(item.get("row_id") or "").lower()
    return (
        str(item.get("probe_id") or "") == "QCL-079"
        or "qcl-079" in row_id
        or "qcl079" in row_id
        or "websocket_generic" in row_id
    )


def add_detail_tokens(tokens: set[str], details: dict[str, Any]) -> None:
    for key in (
        "transport_kind",
        "family",
        "protocol",
        "protocol_role",
        "payload_class",
        "route",
        "route_id",
        "owner",
        "network_provider",
        "endpoint_direction",
        "peer_class",
        "name",
    ):
        add_coverage_token(tokens, details.get(key))
    for key in (
        "product_gate",
        "topology_owner",
        "topology_network_provider",
        "topology_endpoint_direction",
        "topology_transport_family",
    ):
        add_coverage_token(tokens, object_value(details.get("observed")).get(key))


def product_gate_details(details: dict[str, Any]) -> dict[str, Any]:
    observed = object_value(details.get("observed"))
    product_gate = str(observed.get("product_gate") or details.get("product_gate") or "")
    if not product_gate:
        return {}
    return {
        "product_gate": product_gate,
        "product_gate_proven": observed.get("product_gate_proven") is True
        or details.get("product_gate_proven") is True,
    }


def add_coverage_token(tokens: set[str], value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    normalized = text.lower().replace("-", "_").replace(" ", "_")
    for separator in ("/", ":", ";", ",", "->"):
        normalized = normalized.replace(separator, " ")
    for token in normalized.split():
        if token:
            tokens.add(token)


def family_tokens(tokens: set[str]) -> set[str]:
    families: set[str] = set()
    for token in tokens:
        if "websocket" in token:
            families.add("websocket")
        if "tcp_binary" in token:
            families.add("tcp_binary")
        elif "tcp" in token:
            families.add("tcp")
        if "osc_udp" in token:
            families.add("osc_udp")
        elif "udp" in token:
            families.add("udp")
        if "lsl" in token:
            families.add("lsl")
        if "zeromq" in token:
            families.add("zeromq")
        if "bluetooth_rfcomm" in token or "rfcomm" in token:
            families.add("bluetooth_rfcomm")
        elif "bluetooth_gatt" in token or "ble_gatt" in token or "gatt" in token:
            families.add("bluetooth_gatt")
        elif "bluetooth" in token:
            families.add("bluetooth")
        if "adb_forward" in token:
            families.add("adb_forward")
        if "adb_wifi" in token or "adb.tcpip" in token:
            families.add("adb_wifi")
        if "wifi_direct" in token:
            families.add("wifi_direct")
        if "local_only_hotspot" in token:
            families.add("local_only_hotspot")
    return families


def topology_tokens(details: dict[str, Any]) -> set[str]:
    topologies: set[str] = set()
    for key in ("owner", "network_provider", "endpoint_direction", "peer_class"):
        value = str(details.get(key) or "").strip()
        if value:
            topologies.add(value.lower().replace("-", "_").replace(" ", "_"))
    return topologies


def probe_id_from_row_id(row_id: str) -> str:
    for token in row_id.replace(".", " ").split():
        if token.startswith("QCL-"):
            return token
    return ""


def coverage_state(values: set[str], *, limit: int = 12) -> str:
    if not values:
        return "not_included"
    sorted_values = sorted(values)
    visible_values = sorted_values[:limit]
    suffix = "" if len(sorted_values) <= limit else f", +{len(sorted_values) - limit} more"
    return ", ".join(visible_values) + suffix


def transport_coverage_status(items: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("status") or "unknown") for item in items}
    if statuses & {"fail", "blocked", "rejected", "missing"}:
        return "warn"
    if statuses & {"candidate", "planned", "skipped", "unknown"}:
        return "candidate"
    if statuses & {"warn", "usable_with_warnings"}:
        return "warn"
    return "pass"


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def row(
    row_id: str,
    section: str,
    kind: str,
    label: str,
    status: str,
    source: dict[str, Any],
    *,
    authority_owner: str,
    evidence: str = "",
    notes: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "section": section,
        "kind": kind,
        "label": label,
        "status": status or "unknown",
        "authority_owner": authority_owner,
        "evidence_tier": "",
        "source_artifact": source.get("source_id"),
        "source_path": source.get("path"),
        "source_schema": source.get("schema"),
        "required": False,
        "evidence": evidence,
        "notes": notes,
        "issue_count": 0,
        "issue_codes": [],
        "metrics": {},
        "details": details or {},
    }

