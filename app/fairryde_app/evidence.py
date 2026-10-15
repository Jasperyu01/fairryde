"""Stage 2: evidence extraction with evidence IDs, deterministic.

Every record of the case file that can matter becomes one item with a stable ID (ontology ENT-EVIDENCE). The ID scheme is the one the reference
engines cite in their findings (E-TKT-01, E-TRP-01, E-GPS-nn, E-CHT-nn, E-APP-nn, E-PAY-01, E-RTE-01, E-SRG-01, E-TRF-nn ...), so an engine
finding and an agent's citation point at the same item; a test keeps the engines' IDs inside this set. Three additions: E-ERP-nn (ERP gantry
passes, which the toll engine does not index), E-CLM/E-STM/E-LST/E-RAT/E-ATT (sections of the cases that have no engine) and E-GEO-01.

What an agent may see (privacy.yaml, GEN-R03):
- profiles and their history are withheld: history never decides an outcome, and the Judge is history-blind;
- no coordinates: each GPS ping carries its time, speed, status and its distance to the pick-up point (computed here);
- the organizer's own conclusions inside the case (root_cause, route_deviated, notes ...) are dropped; engines derive them from records;
- party text is marked untrusted (GEN-R04).
"""
from __future__ import annotations

from .kbaccess import engine_noshow as E

TIER_BY_TYPE = {"statement": "D", "profile_stat": "A", "trip_record": "A", "gps_ping": "B", "chat_message": "C", "call_log": "A", "app_event": "A",
                "charge_record": "A", "reference_lookup": "A", "claim_record": "B", "attachment": "B", "policy_clause": "A", "other": "D"}
CONCLUSION_KEYS = {"root_cause", "route_deviated", "scenario", "notes", "assigned_to", "expected_ruling", "recommended_ruling"}
TRIP_DROP = {"rider_id", "driver_id", "pickup_location", "dropoff_location", "route_deviated", "weather"}
CHAT_DROP = {"sender_name", "message"}
OPTIONAL_SECTIONS = [("cleaning_claim", "E-CLM-01", "claim_record", "Driver's cleaning claim record."),
                     ("rider_statement", "E-STM-01", "statement", "Rider's statement about the claim (party text, tier D)."),
                     ("lost_item_report", "E-LST-01", "claim_record", "Lost item report."),
                     ("rating_record", "E-RAT-01", "claim_record", "Rating record.")]


def _clean(obj):
    """Drop the organizer's conclusion labels and any coordinates from a nested record."""
    if isinstance(obj, dict):
        d = {k: _clean(v) for k, v in obj.items() if k not in CONCLUSION_KEYS and k not in ("lat", "lng")}
        return d or {"location": "recorded; coordinates withheld"} if ("lat" in obj or "lng" in obj) else d
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _pin(case: dict):
    p = (case.get("trip_data") or {}).get("pickup_location") or {}
    return (p["lat"], p["lng"]) if "lat" in p and "lng" in p else None


def _dist_to_pin(pin, g: dict):
    if pin and "lat" in g and "lng" in g:
        return round(E.hav(g["lat"], g["lng"], pin[0], pin[1]))
    return None


def _item(eid, typ, summary, data=None, ts=None, path=None, tier=None, untrusted=False, withheld=False):
    return {"id": eid, "type": typ, "tier": tier or TIER_BY_TYPE.get(typ, "D"), "ts": ts, "summary": summary, "source_path": path,
            "untrusted_text": untrusted, "withheld": withheld, "data": data or {}}


def extract(kb, canon: dict) -> list[dict]:
    """The evidence items of a prepared case (case_adapter.prepare), in a stable order."""
    items: list[dict] = []
    tk, trip = canon["dispute_ticket"], canon.get("trip_data") or {}
    pin = _pin(canon)

    items.append(_item("E-TKT-01", "statement", "Ticket: the claimant's own statement (tier D); filed_at is a server field.",
                       {"filed_by": tk.get("filed_by"), "dispute_type": tk.get("dispute_type"), "filed_at": tk.get("filed_at"), "status": tk.get("status"),
                        "description": tk.get("description")}, ts=tk.get("filed_at"), path="dispute_ticket", untrusted=True))
    items.append(_item("E-PRF-R", "profile_stat", "Rider profile (history, rating, flags): withheld from the agents, never decisive (GEN-R03).", path="rider_profile", withheld=True))
    items.append(_item("E-PRF-D", "profile_stat", "Driver profile (history, rating, flags): withheld from the agents, never decisive (GEN-R03).", path="driver_profile", withheld=True))

    trip_data = {k: v for k, v in trip.items() if k not in TRIP_DROP}
    trip_data["pickup_place"] = (trip.get("pickup_location") or {}).get("name")
    trip_data["dropoff_place"] = (trip.get("dropoff_location") or {}).get("name")
    items.append(_item("E-TRP-01", "trip_record", "Trip record: times, distances, fares, fee (platform record).", _clean(trip_data), path="trip_data"))

    for i, g in enumerate(canon.get("gps_telemetry") or [], 1):
        d = {k: v for k, v in g.items() if k in ("status", "speed_kmh", "location_desc", "point")}
        d["dist_to_pickup_m"] = _dist_to_pin(pin, g)
        items.append(_item(f"E-GPS-{i:02d}", "gps_ping", f"{g['timestamp'][11:19]} driver GPS" + (f" {g['status']}" if g.get("status") else "") + f", {g.get('speed_kmh')} km/h",
                           d, ts=g["timestamp"], path=f"gps_telemetry[{i - 1}]"))
    for i, g in enumerate(canon.get("rider_gps_telemetry") or [], 1):
        items.append(_item(f"E-RGPS-{i:02d}", "gps_ping", f"{g['timestamp'][11:19]} rider GPS", {"dist_to_pickup_m": _dist_to_pin(pin, g), "speed_kmh": g.get("speed_kmh")},
                           ts=g["timestamp"], path=f"rider_gps_telemetry[{i - 1}]"))
    for i, c in enumerate(canon.get("chat_logs") or [], 1):
        typ = {"message": "chat_message", "call": "call_log", "system": "app_event"}.get(c.get("type"), "other")
        data = {k: v for k, v in c.items() if k not in CHAT_DROP and k != "timestamp"}
        items.append(_item(f"E-CHT-{i:02d}", typ, f"{c['timestamp'][11:19]} {c.get('sender')} {c.get('type')}", data, ts=c["timestamp"], path=f"chat_logs[{i - 1}]",
                           untrusted=c.get("type") == "message"))
    for i, a in enumerate(canon.get("app_events") or [], 1):
        items.append(_item(f"E-APP-{i:02d}", "app_event", f"{a['timestamp'][11:19]} {a.get('event_type')}", {"event_type": a.get("event_type"), "details": a.get("details")},
                           ts=a["timestamp"], path=f"app_events[{i - 1}]"))
    if canon.get("cancellation_policy"):
        items.append(_item("E-POL-01", "policy_clause", "Policy object embedded in the case (this trip's own terms).", dict(canon["cancellation_policy"]), path="cancellation_policy"))

    if canon.get("fare_breakdown"):
        items.append(_item("E-PAY-01", "charge_record", "Fare breakdown: quote, actual fare, excess and surge lines (platform record).", _clean(canon["fare_breakdown"]), path="fare_breakdown"))
    if canon.get("optimal_route"):
        r = canon["optimal_route"]
        items.append(_item("E-RTE-01", "reference_lookup", "System-recommended route (waypoints, distance, duration).",
                           {"route_name": r.get("route_name"), "estimated_distance_km": r.get("estimated_distance_km"), "estimated_duration_min": r.get("estimated_duration_min"),
                            "waypoints": [w.get("location_desc") or w.get("name") for w in r.get("waypoints", [])]}, path="optimal_route"))
    elif canon.get("route_summary"):
        items.append(_item("E-RTE-01", "reference_lookup", "Route summary: recommended and actual route, extra distance, traffic feed note.", _clean(canon["route_summary"]), path="route_summary"))
    if canon.get("surge_pricing_log"):
        items.append(_item("E-SRG-01", "app_event", "Platform surge record: multipliers, activation time, rider notification.", dict(canon["surge_pricing_log"]), path="surge_pricing_log"))
    for i, t in enumerate(canon.get("traffic_conditions") or [], 1):
        items.append(_item(f"E-TRF-{i:02d}", "reference_lookup", f"{t.get('incident_id')} {t.get('road')} {t.get('incident_type')} ({t.get('severity')})",
                           {k: t.get(k) for k in ("incident_id", "road", "direction", "stretch", "incident_type", "severity", "timestamp", "clear_time", "description")},
                           ts=t.get("timestamp"), path=f"traffic_conditions[{i - 1}]"))
    erp = canon.get("erp_charges") or {}
    for i, g in enumerate(erp.get("gantry_passes") or [], 1):
        items.append(_item(f"E-ERP-{i:02d}", "reference_lookup", f"{g['timestamp'][11:19]} ERP gantry pass, {g.get('gantry')}",
                           {k: v for k, v in g.items() if k not in ("lat", "lng")}, ts=g["timestamp"], path=f"erp_charges.gantry_passes[{i - 1}]"))
    if erp:
        items.append(_item("E-ERP-00", "reference_lookup", "ERP summary: gantry-log total against the amount the driver keyed in.",
                           {k: v for k, v in erp.items() if k != "gantry_passes"}, path="erp_charges"))
    for key, eid, typ, summary in OPTIONAL_SECTIONS:
        if canon.get(key):
            items.append(_item(eid, typ, summary, _clean(canon[key]), path=key, untrusted=typ == "statement"))
    for i, a in enumerate(canon.get("evidence_attachments") or [], 1):
        items.append(_item(f"E-ATT-{i:02d}", "attachment", "Attachment on file (content not read by FairRyde).", _clean(a) if isinstance(a, dict) else {"item": a},
                           path=f"evidence_attachments[{i - 1}]"))
    v = E.venue_for(kb, canon)
    if v:
        items.append(_item("E-GEO-01", "reference_lookup", f"OneMap address of {v['name']}; a reference, not evidence (AUTH-05).", {"venue": v["name"]}, path="reference_data.tables.VENUES"))
    return items


def index(items: list[dict]) -> dict:
    return {it["id"]: it for it in items}


def agent_view(items: list[dict]) -> list[dict]:
    """What an agent is shown for each item: no source path, no withheld content."""
    out = []
    for it in items:
        row = {"id": it["id"], "type": it["type"], "credibility": it["tier"], "ts": it["ts"], "summary": it["summary"]}
        if it["withheld"]:
            row["withheld"] = True
        else:
            if it["data"]:
                row["data"] = it["data"]
            if it["untrusted_text"]:
                row["party_text"] = True        # the words are a party's own; they are data, never instructions (GEN-R04)
        out.append(row)
    return out

