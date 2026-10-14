"""Reference evaluation of PB-FC-ROUTE under profile organizer_v2_1 (policy v2.1 Sections 1, 6 and 7) on DISP-001 and its variants.

Purpose: show that the knowledge base decides the organizer's route deviation sample from the raw records, citing the policy by section. It is a
verification tool for the knowledge base, not the product engine, as engine_noshow.py:
- there is no LLM, so the run-agreement (A) and rules-engine agreement (R) confidence terms are 1.0 and marked;
- the READ part of FC-F05 (did a driver message or call inform the rider of the reroute and the reason? did the rider agree?) is approximated by
  the phrase lists below, and the reading test checks whether the other reading would change the outcome (decisive_definition clause 1);
- the incident-to-route match of FC-F06B is by road name, direction and time, because the sample's incidents carry no coordinates (decision D54).
The organizer's own analysis blocks of the case file (chat_log_analysis, traffic_analysis, evidence_summary, recommended_ruling) are removed by
case_adapter.prepare() before this module sees the case: they hold the conclusions this module has to reach itself.
"""
from __future__ import annotations

import copy
import math
import re

import case_adapter
import engine_noshow as E
import policy_v21 as P21
from kbload import KB, ORGANIZER_PROFILE

# FC-F05 (READ): a driver message informs the rider when it says the route changes AND gives a reason (Section 1.2: "A brief reason ... is
# sufficient"). One of the two alone may inform (UNCLEAR: the reading test applies). Neither is NONE.
NOTICE_CHANGE = re.compile(r"\b(route|detour|divert\w*|alternat\w*|different\s+way|another\s+way|other\s+way|shortcut|via|re-?rout\w*|"
                           r"(?:take|taking|took)\s+(?:the\s+)?(?:\w+\s+)?(?:road|highway|expressway|parkway|ecp|pie|cte|aye|kpe|tpe|bke|sle|mce|kje)|"
                           r"go(?:ing)?\s+(?:through|via|round|around))\b", re.I)
NOTICE_REASON = re.compile(r"\b(traffic|jam\w*|congest\w*|accident|crash\w*|fire|clos(?:ed|ure)|road\s*works?|blocked|queue\w*|standstill|erp)\b", re.I)
RIDER_ACK = re.compile(r"^\W*(?:ok(?:ay|ie)?|k|kk|sure|fine|alright|noted|no\s+problem|go\s+ahead|yes|yep|yeah|thanks?|thank\s+you|thx|ty|can)\b", re.I)
RIDER_OBJECT = re.compile(r"\b(?:why|don'?t|do\s+not|not\s+(?:ok|okay|fine|happy)|stop|go\s+back|wrong\s+way|right\s+way|usual\s+route|please\s+(?:don'?t|stop))\b|\bno\b(?!\s+problem)", re.I)
JUSTIFYING_TYPES_EXCLUDED = {"traffic_flow", "normal", "clear", "free_flow"}      # an incident type that says nothing was wrong
ROAD_CODES = {"PIE", "ECP", "CTE", "AYE", "KPE", "TPE", "BKE", "SLE", "MCE", "KJE"}


def _xy(lat: float, lng: float, lat0: float) -> tuple[float, float]:
    return lng * 111320.0 * math.cos(math.radians(lat0)), lat * 110574.0


def dist_to_polyline_m(p: tuple[float, float], poly: list[tuple[float, float]]) -> float:
    """Metres from a point to a polyline of waypoints (local flat projection; the waypoints are straight-line corners, decision D54)."""
    lat0 = sum(a for a, _ in poly) / len(poly)
    px, py = _xy(*p, lat0)
    best = float("inf")
    for a, b in zip(poly, poly[1:]):
        ax, ay = _xy(*a, lat0)
        bx, by = _xy(*b, lat0)
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def driver_notice_reading(text: str | None) -> str:
    """Offline stand-in for FC-F05's reading of one driver message: INFORMS (route change and reason), UNCLEAR (one of the two) or NONE."""
    t = text or ""
    change, reason = bool(NOTICE_CHANGE.search(t)), bool(NOTICE_REASON.search(t))
    return "INFORMS" if (change and reason) else ("UNCLEAR" if (change or reason) else "NONE")


def road_codes(text: str) -> set:
    """The road names in a text: expressway codes (PIE, ECP ...) and the words before a bracket ('Orchard Road')."""
    codes = {m for m in re.findall(r"\b[A-Z]{3}\b", text or "") if m in ROAD_CODES}
    for m in re.findall(r"\(([^)]*)\)", text or ""):
        codes |= {w.upper() for w in re.findall(r"[A-Za-z]+", m) if w.upper() in ROAD_CODES}
    return codes


def heading_axis(case: dict) -> str | None:
    """'east', 'west', 'north' or 'south': the main direction from the pick-up to the drop-off."""
    t = case["trip_data"]
    dlat = t["dropoff_location"]["lat"] - t["pickup_location"]["lat"]
    dlng = t["dropoff_location"]["lng"] - t["pickup_location"]["lng"]
    if dlat == dlng == 0:
        return None
    return ("east" if dlng > 0 else "west") if abs(dlng) * 111320 * math.cos(math.radians(t["pickup_location"]["lat"])) >= abs(dlat) * 110574 else ("north" if dlat > 0 else "south")


def incident_review(case: dict) -> dict:
    """FC-F06B: the incidents that justify a reroute, and the ones that make the reading unclear. An incident justifies when (1) its road is named on
    the recommended route, (2) its direction, when it names one, is the direction of travel, (3) its window overlaps the trip, and (4) its type and
    severity say something was wrong. 'match' passes all four; 'near_miss' is on the route's road but fails exactly one test; 'weak' matches but names
    no direction. The reading is unclear (a person reads it, the reading test applies) when there is a near miss or a weak match."""
    route = case.get("optimal_route") or {}
    route_text = " ".join([route.get("route_name") or ""] + [w.get("location_desc") or "" for w in route.get("waypoints", [])])
    route_roads = road_codes(route_text)
    t = case["trip_data"]
    t0, t1 = E.T(t["start_time"]), E.T(t["end_time"])
    axis = heading_axis(case)
    out = {"match": [], "near_miss": [], "weak": []}
    for inc in case.get("traffic_conditions") or []:
        if not road_codes(inc.get("road") or "") & route_roads:
            continue
        m_dir = re.match(r"(north|south|east|west)", str(inc.get("direction") or "").lower())
        ok_dir = not (m_dir and axis and m_dir.group(1) != axis)
        s0 = E.T(inc["timestamp"])
        s1 = E.T(inc["clear_time"]) if inc.get("clear_time") else None
        ok_time = not (s0 > t1 or (s1 is not None and s1 < t0))
        ok_type = not (str(inc.get("incident_type") or "").lower() in JUSTIFYING_TYPES_EXCLUDED or str(inc.get("severity") or "").lower() in ("low", "none", ""))
        failed = [n for n, ok in (("direction", ok_dir), ("time", ok_time), ("type", ok_type)) if not ok]
        if not failed:
            out["match"].append(inc)
            if not m_dir:
                out["weak"].append(inc)
        elif len(failed) == 1:
            out["near_miss"].append(inc)
    return out


def matching_incidents(case: dict) -> list[dict]:
    return incident_review(case)["match"]


def evaluate(kb: KB, case_in: dict, profile: str | None = None, overrides: dict | None = None, force: dict | None = None) -> E.Trace:
    """force: {"informed": "YES" | "NO" | "UNCLEAR", "justified": True | False} to test another reading (decisive test, clause 1)."""
    case, _reference = case_adapter.prepare(case_in)
    profile = profile or ORGANIZER_PROFILE
    force = force or {}
    tr = E.Trace(profile, overrides)
    tr.case_type = "FC-ROUTE"

    def P(name):
        e = kb.param(name, profile, overrides)
        if e is None:
            raise KeyError(name)
        info = {"value": e.get("value"), "credibility": e.get("credibility"), "plausible_range": e.get("plausible_range"), "flag_only": e.get("flag_only", False)}
        if e.get("fallback_from"):
            info["source"] = f"{e['fallback_from']} (META-01 fallback)"
        tr.params_used[name] = info
        return e.get("value")

    tk, t, fare = case["dispute_ticket"], case["trip_data"], case.get("fare_breakdown") or {}
    chat = case.get("chat_logs") or []
    gps = sorted(case.get("gps_telemetry") or [], key=lambda g: E.T(g["timestamp"]))
    gps_no = {id(g): i + 1 for i, g in enumerate(case.get("gps_telemetry") or [])}
    gid = lambda g: f"E-GPS-{gps_no[id(g)]:02d}"
    cht = lambda c: f"E-CHT-{chat.index(c) + 1:02d}"
    pb = "PB-FC-ROUTE"

    # ---------------- PB-INTAKE
    filer = kb.resolve("TX-ROLE", tk.get("filed_by")) or "OTHER"
    texts = [(filer, tk.get("description", "") or "")] + [(kb.resolve("TX-ROLE", c["sender"]) or "OTHER", c["content"]) for c in chat if c["type"] == "message"]
    free_text = [x for _, x in texts]
    tr.injection_authors = sorted({who for who, x in texts if any(re.search(p, x, re.I) for p in E.INJECTION_PATTERNS)})
    if tr.injection_authors:
        tr.flag("INJECTION_SUSPECTED")
    tr.step("PB-INTAKE", 1, "GEN-R04", f"instruction-like text from {', '.join(tr.injection_authors)} flagged and ignored" if tr.injection_authors
            else "no instructions found in party text", ["E-TKT-01"] + [cht(c) for c in chat if c["type"] == "message"])
    disc = E.discrimination_hits(free_text)
    hits = sorted(set(E.safety_hits(free_text)) | set(disc))
    tr.findings["_safety"], tr.findings["_discrimination"] = bool(hits), bool(disc)
    tr.step("PB-INTAKE", 2, "CLS-01", f"safety content (offline stand-in for the reading): {hits}" if hits else "no safety content found (offline stand-in for the reading)", ["E-TKT-01"])
    tr.claim_type = kb.resolve("TX-CASE", tk["dispute_type"])
    delta = _num(fare.get("delta", {}).get("total")) if isinstance(fare.get("delta"), dict) else None
    tr.step("PB-INTAKE", 3, "CLS-05, CLS-02, CLS-04",
            f"dispute_type {tk['dispute_type']!r} -> {tr.claim_type}; one claim contesting the fare above the estimate" + ("; a safety claim is added as the primary claim" if hits else ""), ["E-TKT-01", "E-PAY-01"])
    tr.step("PB-INTAKE", 4, "CLS-03", "contested charge present: not routed to support", ["E-PAY-01"])
    trip_ok = tk["trip_id"] == t["trip_id"]
    tr.step("PB-INTAKE", 5, "MAT-01", f"trip {t['trip_id']} {'matches' if trip_ok else 'DOES NOT match'} the ticket", ["E-TKT-01.trip_id", "E-TRP-01.trip_id"])
    tr.relation = "NEW"
    tr.step("PB-INTAKE", 6, "MAT-02", "no ticket index in the case file; treated as NEW (at run time the ticket index is checked)", ["E-TKT-01"], status="missing")
    tr.step("PB-INTAKE", 7, "MAT-03", "not an appeal", ["E-TKT-01.status"], status="not_applicable")
    trip_date = (t.get("end_time") or "")[:10]
    eff = kb.y["reference_data"]["profiles"][profile].get("effective_from")
    eff_ok = eff in (None, "case-specific") or trip_date >= str(eff)
    if not eff_ok:
        tr.policy_gap.append(("META-02", f"the {profile} profile starts on {eff}, after the trip date {trip_date}"))
        tr.path("META-02")
    tr.step("PB-INTAKE", 8, "META-01, META-02", f"profile {profile} (organizer case: policy v2.1 governs); effective from {eff}: " + ("in force" if eff_ok else "NOT in force on the trip date, so there are no values to apply (policy gap)"), [])
    bbox = P("SG_BBOX")
    pts = [(g["lat"], g["lng"]) for g in gps] + [(t["pickup_location"]["lat"], t["pickup_location"]["lng"]), (t["dropoff_location"]["lat"], t["dropoff_location"]["lng"])]
    in_box = all(bbox[0] <= la <= bbox[2] and bbox[1] <= lo <= bbox[3] for la, lo in pts)
    ordered = E.T(tk["filed_at"]) >= E.T(t["end_time"])
    tr.step("PB-INTAKE", 9, "DQ-03, DQ-04", f"coordinates in Singapore: {in_box}; filed after the trip: {ordered}", ["E-TRP-01", "E-GPS-*"])

    # ---------------- PB-FC-ROUTE (organizer_v2_1 branch)
    tol_km = P("DEVIATION_TOLERANCE_KM")
    tm = P("MONEY_TOLERANCE_SGD")
    # 1 DQ-05 and the figures the case states: refund base, excess lines and the difference must agree
    quoted, actual = _num(t.get("estimated_fare")), _num(t.get("actual_fare"))
    est_total, act_total = _num((fare.get("estimated") or {}).get("total")), _num((fare.get("actual") or {}).get("total"))
    exc_dist_fare, exc_tolls = _num(fare.get("excess_distance_fare")), _num(fare.get("excess_tolls"))
    diff = _r2(actual - quoted) if None not in (quoted, actual) else None
    notes = []
    if est_total is not None and quoted is not None and abs(est_total - quoted) > tm:
        notes.append("the estimate in the trip record and in the fare breakdown differ")
    if act_total is not None and actual is not None and abs(act_total - actual) > tm:
        notes.append("the fare in the trip record and in the fare breakdown differ")
    if diff is not None and delta is not None and abs(diff - delta) > tm:
        notes.append(f"the stated difference {delta:.2f} is not actual minus estimate {diff:.2f}")
    if diff is not None and exc_dist_fare is not None and exc_dist_fare - max(diff, 0) > tm:
        notes.append(f"the excess distance fare {exc_dist_fare:.2f} is more than the whole difference {diff:.2f}")
    if diff is not None and exc_dist_fare is not None and exc_tolls is not None and exc_dist_fare + exc_tolls - max(diff, 0) > tm:
        notes.append("the excess distance fare and the excess tolls together are more than the whole difference")
    if (exc_dist_fare is not None and exc_dist_fare < 0) or (exc_tolls is not None and exc_tolls < 0):
        notes.append("an excess line in the fare breakdown is negative")
    figures_ok = not notes
    tr.finding("F-FARE-FIGURES", {"quoted": quoted, "actual": actual, "difference": diff, "excess_distance_fare": exc_dist_fare, "excess_tolls": exc_tolls, "consistent": figures_ok},
               "SGD", basis=["E-TRP-01", "E-PAY-01"], rule="DQ-05", params=["MONEY_TOLERANCE_SGD"], status="established" if figures_ok else "contested")
    tr.path("DQ-05")
    tr.step(pb, 1, "DQ-05", f"fare {actual if actual is not None else '?'} against the estimate {quoted if quoted is not None else '?'}: difference {diff if diff is not None else '?'}; "
            f"excess distance fare {exc_dist_fare}, excess tolls {exc_tolls}: " + ("consistent" if figures_ok else "NOT consistent (" + "; ".join(notes) + ")"), ["E-TRP-01", "E-PAY-01"])

    # 2 FC-F02: deviation = actual route distance minus recommended route distance (Section 1.4)
    route = case.get("optimal_route") or {}
    rec_km = _num(route.get("estimated_distance_km"))
    rec_km_trip = _num(t.get("estimated_distance_km"))
    act_km = _num(t.get("actual_distance_km"))
    wp = [(w["lat"], w["lng"]) for w in route.get("waypoints", [])]
    if rec_km is None:
        rec_km = rec_km_trip
    dev_km = _r2(act_km - rec_km) if None not in (act_km, rec_km) else None
    stated_km = _num(t.get("excess_distance_km"))
    if dev_km is not None and ((rec_km_trip is not None and abs(rec_km_trip - rec_km) > 0.05) or (stated_km is not None and abs(stated_km - dev_km) > 0.05)):
        figures_ok = False
        notes.append("the distances in the case file disagree")
    corr, kmin, excl = P("CORRIDOR_HALF_WIDTH_M"), P("CORRIDOR_MIN_CONSEC_PINGS"), P("ENDPOINT_EXCLUSION_M")
    pick = (t["pickup_location"]["lat"], t["pickup_location"]["lng"])
    drop = (t["dropoff_location"]["lat"], t["dropoff_location"]["lng"])
    off, t_dev, run_len, best_run, off_ids = [], None, 0, 0, []
    if len(wp) >= 2:
        for g in gps:
            d = dist_to_polyline_m((g["lat"], g["lng"]), wp)
            is_off = d > corr
            near_end = min(E.hav(g["lat"], g["lng"], *pick), E.hav(g["lat"], g["lng"], *drop)) <= excl
            off.append((g, round(d), is_off, near_end))
            if is_off and t_dev is None:
                t_dev = E.T(g["timestamp"])           # the first ping beyond the corridor, wherever it is: a notice must come at or before this moment
            if is_off and not near_end:
                run_len += 1
                best_run = max(best_run, run_len)
                off_ids.append(gid(g))
            else:
                run_len = 0
    spatial = best_run >= kmin
    tr.finding("F-DEVIATION-KM", dev_km, "km", basis=["E-TRP-01", "E-RTE-01"], rule="FC-F02", params=["CORRIDOR_HALF_WIDTH_M", "CORRIDOR_MIN_CONSEC_PINGS", "ENDPOINT_EXCLUSION_M", "DEVIATION_TOLERANCE_KM"],
               status="established" if dev_km is not None else "unknown")
    tr.finding("F-DEVIATION-CONFIRMED", spatial, basis=sorted(set(off_ids))[:20] or [], rule="FC-F02", params=["CORRIDOR_HALF_WIDTH_M", "CORRIDOR_MIN_CONSEC_PINGS", "ENDPOINT_EXCLUSION_M"],
               status="established" if wp else "unknown")
    tr.path("FC-F02")
    tr.step(pb, 2, "FC-F02", (f"recorded distance {act_km} km minus recommended route {rec_km} km = {dev_km} km (the tolerance is {tol_km} km); " if dev_km is not None else "distance or recommended route missing; ")
            + (f"spatial confirmation: {best_run} consecutive GPS points beyond {corr} m of the recommended route (needed {kmin}), first beyond it at {t_dev.strftime('%H:%M:%S')}" if wp and t_dev else
               f"spatial confirmation: {best_run} consecutive points beyond the corridor (needed {kmin})" if wp else "no recommended route waypoints"),
            ["E-TRP-01", "E-RTE-01"] + sorted(set(off_ids))[:20], status="done" if dev_km is not None else "missing")

    if not figures_ok:
        tr.flag("FIGURES_DISAGREE")

    # 3 DQ-02 speed consistency (soft) and ping spacing
    vmax, ratio = P("SPEED_MAX_KMH"), P("SPEED_RATIO_SOFT")
    soft = hard = 0
    for a, b in zip(gps, gps[1:]):
        dt_s = (E.T(b["timestamp"]) - E.T(a["timestamp"])).total_seconds()
        d_m = E.hav(a["lat"], a["lng"], b["lat"], b["lng"])
        implied = d_m / dt_s * 3.6 if dt_s > 0 else 0
        reported = ((a.get("speed_kmh") or 0) + (b.get("speed_kmh") or 0)) / 2
        hard += implied > vmax
        soft += reported > ratio * implied and reported > 5
    gaps = [(E.T(b["timestamp"]) - E.T(a["timestamp"])).total_seconds() for a, b in zip(gps, gps[1:])]
    maxgap = P("PING_MAX_GAP_S")
    if soft:
        tr.flag("SPEED_INCONSISTENT")
    if hard:
        tr.flag("GPS_DATA_ERROR")
    if gaps and max(gaps) > maxgap:
        tr.flag("SPARSE_GPS")
    tr.finding("F-SPEED-CONSISTENCY", {"soft_segments": soft, "hard_segments": hard, "longest_gap_s": round(max(gaps)) if gaps else None, "window": "trip"},
               basis=["E-GPS-*"], rule="DQ-02", params=["SPEED_RATIO_SOFT", "SPEED_MAX_KMH", "PING_MAX_GAP_S"])
    tr.step(pb, 3, "DQ-02", f"speed in the trip trace: {soft} soft, {hard} hard segments; longest gap between points {round(max(gaps)) if gaps else '?'} s (limit {maxgap} s)", ["E-GPS-*"])

    # 4 FC-F05: did the driver inform the rider before or at the point of deviation? (READ)
    deviation_exists = dev_km is not None and dev_km > tol_km
    notice = {"on_time": [], "late": [], "unclear": [], "agreed": "NONE", "ack_ids": [], "objection_ids": []}
    informs_ts = None
    for c in chat:
        if c["sender"] != "driver" or c["type"] not in ("message", "call"):
            continue
        ts = E.T(c["timestamp"])
        if c["type"] == "call":
            if t_dev is None or ts <= t_dev:
                notice["unclear"].append(cht(c))               # a call's words are not recorded: Section 1.2 allows a verbal notice only with the recording as evidence
            continue
        r = driver_notice_reading(c["content"])
        on_time = t_dev is None or ts <= t_dev
        if r == "INFORMS":
            (notice["on_time"] if on_time else notice["late"]).append(cht(c))
            if on_time and informs_ts is None:
                informs_ts = ts
        elif r == "UNCLEAR":
            (notice["unclear"] if on_time else notice["late"]).append(cht(c))
    if informs_ts is not None:                                  # Section 1.4: rider acknowledgment confirmed by the chat means the deviation is agreed
        for c in chat:
            if c["sender"] == "rider" and c["type"] == "message" and E.T(c["timestamp"]) > informs_ts:
                if RIDER_OBJECT.search(c["content"]):
                    notice["objection_ids"].append(cht(c))
                elif RIDER_ACK.search(c["content"]):
                    notice["ack_ids"].append(cht(c))
        notice["agreed"] = "NO" if notice["objection_ids"] else ("YES" if notice["ack_ids"] else "NONE")
    informed = "YES" if notice["on_time"] else ("UNCLEAR" if notice["unclear"] else "NO")
    informed = force.get("informed", informed)
    tr.notice_detail = notice
    tr.finding("F-NOTICE", informed, basis=notice["on_time"] + notice["unclear"] + notice["late"] + notice["ack_ids"] + notice["objection_ids"] + (["E-CHT-*"] if not chat else []),
               rule="FC-F05", status="read" if informed != "NO" or notice["late"] else "established")
    tr.finding("F-AGREED", notice["agreed"], basis=notice["ack_ids"] + notice["objection_ids"], rule="FC-F05", status="read" if informs_ts else "not_applicable")
    tr.path("FC-F05")
    tr.step(pb, 4, "FC-F05", {"YES": f"the driver informed the rider before or at the deviation ({', '.join(notice['on_time'])}); rider agreement: {notice['agreed']}",
                              "UNCLEAR": f"a driver message or call before the deviation may have informed the rider ({', '.join(notice['unclear'])}); its words do not settle it",
                              "NO": "no driver message or call before or at the point of deviation tells the rider of a route change"
                              + (f"; later messages ({', '.join(notice['late'])}) came after the deviation began" if notice["late"] else "")}[informed],
            notice["on_time"] + notice["unclear"] + notice["late"], note="READ: judged from the driver's messages and calls")

    # 5 FC-F06 and FC-F06B: traffic justification from the historical traffic data (Section 1.4)
    review = incident_review(case)
    inc = review["match"]
    unclear_j = bool(review["near_miss"] or review["weak"])
    traffic_present = "traffic_conditions" in case
    justified = bool(inc)
    justified = force.get("justified", justified)
    inc_ids = [f"E-TRF-{i:02d}" for i, x in enumerate(case.get("traffic_conditions") or [], 1) if x in inc]
    tr.findings["F-JUSTIFIED"] = {"value": justified, "unit": "", "status": ("read" if unclear_j else "established") if traffic_present else "unknown", "basis": inc_ids, "rule": "FC-F06B", "params": []}
    tr.justification_review = {k: [x["incident_id"] for x in v] for k, v in review.items()}
    tr.path("FC-F06", "FC-F06B")
    tr.step(pb, 5, "FC-F06, FC-F06B", ("traffic data on the route: " + "; ".join(f"{x['incident_id']} {x['incident_type']} ({x['severity']}) on {x['road']} {x.get('direction', '')} from {x['timestamp'][11:16]}"
                                                                              + (f" to {x['clear_time'][11:16]}" if x.get("clear_time") else " (still open)") for x in inc) if inc else
                                      ("no incident on the roads of the recommended route during the trip" if traffic_present else "the case has no traffic data"))
            + ("; an incident on the route's road fails one test (" + ", ".join(i["incident_id"] for i in review["near_miss"]) + ") or names no direction: the reading is unclear" if unclear_j else ""),
            inc_ids, status="done" if traffic_present else "missing", note="the incidents carry no coordinates: matched by road name, direction and time (FC-F06B, D54)")

    # 6 FC-R13: the Section 1.3 matrix, then the amount
    tr.amount_at_stake = max(delta or 0.0, exc_dist_fare or 0.0)
    tr.deviation_km = dev_km
    missing = dev_km is None or exc_dist_fare is None or diff is None
    unconfirmed = deviation_exists and not spatial                      # the distance says detour, the trace does not confirm it (FC-F02)
    no_traffic = deviation_exists and not traffic_present and "justified" not in force
    if tr.findings.get("_discrimination") or tr.findings.get("_safety"):
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["SE-R-HUMAN-DECIDES"]
        tr.secondary_claims = [{"claim": "FARE_ABOVE_ESTIMATE", "amount_sgd": tr.amount_at_stake, "proposed_outcome": None}]
        tr.path("CLS-01", "SE-R01")
        tr.step(pb, 6, "CLS-01, SE-R01", "the complaint contains safety content: the whole case goes to a person with the case file only (policy v2.1 Section 5.2); "
                "no outcome, amount or measure is proposed", ["E-TKT-01"])
    elif tr.policy_gap:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"]
        tr.path("GEN-R07")
        tr.step(pb, 6, "FC-R13, GEN-R07", "no written rule applies to this trip date: " + "; ".join(w for _, w in tr.policy_gap), [])
    elif not figures_ok:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["GEN-R-DATA-INCONSISTENT"]
        tr.path("GEN-R02")
        tr.step(pb, 6, "FC-R13, GEN-R02", "the figures in the case file disagree (" + "; ".join(notes) + "), so a person decides", ["E-TRP-01", "E-PAY-01"])
    elif missing or unconfirmed or no_traffic:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["FC-R-INSUFFICIENT-DATA"]
        tr.flag("RECORDS_MISSING")
        tr.path("FC-R12")
        tr.step(pb, 6, "FC-R12", "the recorded distance, the excess distance fare, the recommended route or the traffic data is missing, or the trace does not confirm the deviation: "
                "no adverse finding, a person decides", ["E-TRP-01", "E-RTE-01", "E-PAY-01"])
    else:
        base = min(exc_dist_fare, max(diff, 0.0))
        if not deviation_exists:
            tr.outcome, tr.reasons, row = "UPHOLD", ["FC-R-DEVIATION-TOLERANCE"], "within tolerance (1 km or less): no refund, whether or not the driver informed the rider or had a traffic reason"
        elif diff <= 0:
            tr.outcome, tr.reasons, row = "UPHOLD", ["FC-R-FIXED-FARE"], "the fare charged is not above the estimate: nothing was charged for the extra distance"
        elif not justified:
            tr.outcome, tr.reasons, row = "FULL_REFUND", ["FC-R-DEVIATION-UNJUSTIFIED"], "no traffic justification and more than 1 km: refund of the excess distance fare (Section 1.3 says 'Full refund', decision D46)"
        elif informed == "YES" and notice["agreed"] == "YES":
            tr.outcome, tr.reasons, row = "UPHOLD", ["FC-R-DEVIATION-AGREED"], "traffic reroute, the rider was informed and agreed: no refund"
        elif informed == "YES":
            tr.outcome, tr.reasons, row = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"], ("the driver informed the rider, but the chat does not confirm that the rider agreed (Section 1.4) "
                                                                                    "and Section 1.3 has no row for that")
            tr.path("GEN-R07")
        else:
            tr.outcome, tr.reasons, row = "PARTIAL_REFUND", ["FC-R-DEVIATION-UNNOTIFIED"], "traffic reroute justified, the rider was not informed and the deviation is more than 1 km: partial refund of the excess distance fare"
        tr.path("FC-R13")
        tr.matrix_row = row
        if tr.outcome in ("PARTIAL_REFUND", "FULL_REFUND"):
            tr.remedy = {"amount_sgd": _r2(base), "payer": "PLATFORM", "payee": "RIDER", "form": P("REMEDY_FORM"), "attribution": "excess_distance_fare"}
            if tr.outcome == "FULL_REFUND":
                tr.path("FC-R13B")
                tr.flag("GENERIC_ASSUMPTION_USED")                  # META-05: FC-R13B is a FairRyde reading (D) and decides the amount
                tr.also.append(f"the whole excess (distance, tolls, time, surge) is S${diff:.2f}; if 'full' means the whole excess the refund would be that amount")
                tr.alternative_amount = diff
        else:
            tr.remedy = {"amount_sgd": 0.0, "payer": None, "payee": None, "form": "NONE"}
        tr.step(pb, 6, "FC-R13", f"{row}" + (f"; refund S${tr.remedy['amount_sgd']:.2f}, the excess distance fare, paid to the original payment method" if tr.outcome in ("PARTIAL_REFUND", "FULL_REFUND") else ""),
                ["F-DEVIATION-KM", "F-NOTICE", "F-JUSTIFIED"])
    if tr.outcome in ("PARTIAL_REFUND", "FULL_REFUND"):
        # 7 FC-R08 and the FC-R01 toll claim: tolls pass through at cost under this profile (decision D47)
        pass_through = P("TOLLS_TREATMENT") == "PASS_THROUGH"
        tr.step(pb, 7, "FC-R08, FC-R01", (f"tolls of S${exc_tolls:.2f} for the longer route pass through at cost: nothing is refunded for them under this profile (DISP-001's recommended ruling says so; D47)"
                                         if pass_through and exc_tolls else "no excess tolls on the fare") , ["E-PAY-01"], status="done")
        tr.use("FC-R08")
    if tr.outcome == "ESCALATE_HUMAN" and not tr.remedy:
        tr.remedy = {"amount_sgd": None, "payer": None, "payee": None, "form": None, "provisional": "decided by a human"}
    if (tr.outcome in ("PARTIAL_REFUND", "FULL_REFUND", "UPHOLD") and tr.reasons[0].startswith("FC-R-DEVIATION")) or tr.outcome in ("PARTIAL_REFUND", "FULL_REFUND"):
        tr.notes.append("The organizer's recommended ruling also lists a driver education notice and a KPI log entry; FairRyde proposes neither (GEN-R06: no action against an account), a reviewer may add them.")

    # 8 precedent search (Section 7, GEN-R08)
    tr.precedents = P21.match_precedents(kb, "FC-ROUTE", {"rider_informed": informed == "YES", "traffic_justified": justified, "deviation_km": dev_km})
    tr.step(pb, 8, "GEN-R08", "precedents: " + ("; ".join(f"{p['section']} ({p['case_id']}) {'aligned' if p['aligned'] else 'distinguished on ' + ', '.join(p['differs'])}: {p['outcome']} S${p['refund_amount_sgd']:.2f}" for p in tr.precedents) or "none"), [])
    tr.step(pb, 9, "GEN-R05", "advocate briefs are produced at run time by the Rider and Driver Advocates; not simulated in this offline check", [], status="missing")

    # 9 confidence (AUTH-05)
    band_km = P("ROUTE_BOUNDARY_BAND_KM")
    M = min(1.0, abs(dev_km - tol_km) / (2 * band_km)) if dev_km is not None and band_km else 1.0
    if dev_km is not None and abs(dev_km - tol_km) <= band_km:
        tr.flag("BOUNDARY_MARGIN")
    req = {"E-TKT-01": True, "E-TRP-01": True, "E-RTE-01 (recommended route)": bool(wp), "E-PAY-01 (fare breakdown)": bool(fare),
           "E-GPS-* (trip trace)": bool(gps), "E-CHT-* (chat logs)": "chat_logs" in case, "E-TRF-* (traffic data)": traffic_present}
    soft = [f for f in tr.flags if f in E.SOFT_FLAGS]
    tr.confidence = P21.composite_confidence(kb, profile, M, req, soft)
    tr.step(pb, 10, "AUTH-05", f"C = {tr.confidence['C']:.3f} (A 1.0, M {M:.2f}, E {tr.confidence['E']:.2f}, R 1.0; soft flags {soft})", ["F-DEVIATION-KM"])
    tr.margin = (dev_km - tol_km) if dev_km is not None else 0
    tr.spread_max = 0
    return tr


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def reading_tests(kb: KB, case: dict, profile: str, base: E.Trace) -> list[dict]:
    """Decisive test clause 1: FC-F05 (informed) and FC-F06B (justified) are readings; another reading that changes the outcome is decisive."""
    out = []
    informed = base.findings["F-NOTICE"]["value"]
    if base.notice_detail["unclear"] or base.notice_detail["on_time"] or informed != "NO":
        alt = "NO" if informed == "YES" else "YES"
        t2 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, force={"informed": alt})
        out.append({"rule": "FC-F05", "reading": f"informed: {informed}", "other_reading": f"informed: {alt}", "outcome_other": t2.outcome, "changes": t2.outcome != base.outcome or t2.reasons != base.reasons})
    elif base.notice_detail["late"]:
        t2 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, force={"informed": "YES"})
        out.append({"rule": "FC-F05", "reading": "informed: NO (the messages came after the deviation began)", "other_reading": "informed: YES", "outcome_other": t2.outcome,
                    "changes": t2.outcome != base.outcome or t2.reasons != base.reasons})
    j = base.findings["F-JUSTIFIED"]["value"]
    if base.findings["F-JUSTIFIED"]["status"] == "read":
        t3 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, force={"justified": not j})
        out.append({"rule": "FC-F06B", "reading": f"traffic justification: {j}", "other_reading": f"traffic justification: {not j}", "outcome_other": t3.outcome,
                    "changes": t3.outcome != base.outcome or t3.reasons != base.reasons})
    return out


def decide_tier(kb: KB, tr: E.Trace, reads: list[dict], case: dict) -> dict:
    profile = tr.profile
    fraud = P21.fraud_flag_count(case)
    triggers, gates, decisive = [], [], []
    if tr.findings.get("_discrimination") or tr.findings.get("_safety"):
        return {"tier": "HUMAN", "decisive": [], "gates": ["G4 safety content"], "runtime_only_gates": [], "favoured_party": None, "section6": None,
                "triggers": ["safety content: the AI agent may only prepare a case file (policy v2.1 Section 5.2); no outcome, amount or measure is proposed (CLS-01, SE-R01)"]}
    if tr.outcome == "ESCALATE_HUMAN":
        sec6 = None
        tier = "HUMAN"
        triggers.append("FairRyde has no ruling to approve (AUTH-06): " + ", ".join(tr.reasons))
    else:
        c_eff = tr.confidence["C_effective"]
        sec6 = P21.ruling_path(kb, profile, category="route_deviation", value=tr.amount_at_stake, confidence=c_eff, fraud_flags=fraud, deviation_km=tr.deviation_km)
        tier = sec6["tier"]
        triggers += sec6["reasons"] if sec6["tier"] != "AUTO" else []
    for r in reads:
        if r["changes"]:
            decisive.append((r["rule"], f"reading as {r['other_reading']} instead of {r['reading']} gives {r['outcome_other']}"))
    if decisive:
        triggers.append("decisive: " + "; ".join(f"{r} ({w})" for r, w in decisive))
    if tr.outcome == "FULL_REFUND":
        triggers.append(f"Section 1.3 says 'Full refund of excess distance fare' and the word is ambiguous (FC-R13B, decision D46): a person confirms the amount; the whole excess "
                        f"(distance, tolls, time, surge), S${getattr(tr, 'alternative_amount', 0):.2f}, is the other reading")
    if tr.fraud:
        triggers.append("fraud signal on " + ", ".join(w for w, _ in tr.fraud))
    for f, why in (("RECORDS_MISSING", "records missing"), ("FIGURES_DISAGREE", "the figures in the case file disagree (DQ-05)")):
        if f in tr.flags:
            triggers.append(why)
    if "GPS_DATA_ERROR" in tr.flags or "FIGURES_DISAGREE" in tr.flags:
        gates.append("G1 data inconsistency")
    favoured = {"PARTIAL_REFUND": "RIDER", "FULL_REFUND": "RIDER", "UPHOLD": "DRIVER"}.get(tr.outcome)
    if favoured and favoured in tr.injection_authors:
        triggers.append(f"instruction injected by the party the outcome favors ({favoured})")
    if tr.outcome != "ESCALATE_HUMAN" and (triggers and tier == "AUTO" or gates and tier == "AUTO"):
        tier = "APPROVE"
    generic = [r for r, _ in decisive if kb.rules.get(r, {}).get("credibility") in ("C", "D")]
    if generic:
        tr.flag("GENERIC_ASSUMPTION_USED")
    return {"tier": tier, "decisive": decisive, "triggers": triggers, "gates": gates, "favoured_party": favoured, "section6": sec6,
            "runtime_only_gates": ["G2 rule conflict", "G3 history-aware vs history-blind Judge", "G7 citation and number verification", "G8 Judge runs vs rules engine"]}


def run(kb: KB, case: dict, profile: str | None = None) -> dict:
    base = evaluate(kb, copy.deepcopy(case), profile)
    canon, _ = case_adapter.prepare(case)
    reads = reading_tests(kb, case, base.profile, base) if base.outcome != "ESCALATE_HUMAN" else []
    tier = decide_tier(kb, base, reads, canon)
    base.step("PB-FC-ROUTE", 11, "AUTH-07, AUTH-01 to AUTH-04, AUTH-06", f"tier {tier['tier']}" + (f"; {len(tier['triggers'])} reason(s)" if tier["triggers"] else ""), ["F-DEVIATION-KM"])
    base.step("PB-FC-ROUTE", 12, "EXP-01 to EXP-03, META-05", "explanations drafted from findings only (see the explanation drafts)", ["F-*"])
    return {"trace": base, "sensitivity": [], "readings": reads, "tier": tier, "case": canon}
