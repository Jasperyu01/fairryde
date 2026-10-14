"""Reference evaluation of PB-FC-SURGE under profile organizer_v2_1 (policy v2.1 Sections 3, 6 and 7) on DISP-003 and its variants.

A surge dispute: the final fare is above the upfront quote because the surge multiplier rose between the quote and the start of the trip.
Policy v2.1 Section 3.3 settles it by one fact, whether the rider was notified in the app (Section 3.2), once the amounts show that the
difference is the surge and nothing else (Section 3.4). Same limits as engine_route.py: no LLM (A and R are 1.0), a verification tool for the
knowledge base, and the organizer's own analysis blocks are removed by case_adapter.prepare() before this module sees the case.
"""
from __future__ import annotations

import copy
import math
import re

import case_adapter
import engine_noshow as E
import policy_v21 as P21
from kbload import KB, ORGANIZER_PROFILE


def _num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _r2(x: float) -> float:
    return round(x + 1e-9, 2)


def has_surge_evidence(case: dict) -> bool:
    """CLS-05: a fare_dispute is a surge dispute when the case carries a surge record or a surge multiplier in the fare breakdown."""
    fb = case.get("fare_breakdown") or {}
    return bool(case.get("surge_pricing_log")) or any(isinstance(v, dict) and "surge_multiplier" in v for v in fb.values())


def notice_valid(log: dict, start: str | None) -> tuple[bool | None, str]:
    """Section 3.2: an in-app notification before or at the point of pickup. True, False, or None when the record says notified but not how or when."""
    flag = log.get("rider_notified")
    if flag is None or isinstance(flag, str) and not flag.strip():
        return None, "the surge record does not say whether the rider was notified"
    if str(flag).strip().lower() in ("false", "no", "0"):
        return False, "the platform's surge record says the rider was not notified"
    method, ts = str(log.get("notification_method") or "").lower(), log.get("notification_timestamp")
    if not method and not ts:
        return None, "the record says notified, without the method or the time"
    if method and not re.search(r"app|push|notification", method):
        return False, f"the notification method ({log.get('notification_method')}) is not an in-app notification (Section 3.2)"
    if ts and start and E.T(ts) > E.T(start):
        return False, "the notification came after the trip started (Section 3.2: before or at the point of pickup)"
    return True, "an in-app notification before the trip started"


def evaluate(kb: KB, case_in: dict, profile: str | None = None, overrides: dict | None = None, force: dict | None = None) -> E.Trace:
    """force: {"notified": True | False} to test another reading of the notification record (decisive test)."""
    case, _reference = case_adapter.prepare(case_in)
    profile = profile or ORGANIZER_PROFILE
    force = force or {}
    tr = E.Trace(profile, overrides)
    tr.case_type = "FC-SURGE"

    def P(name):
        e = kb.param(name, profile, overrides)
        if e is None:
            raise KeyError(name)
        tr.params_used[name] = {"value": e.get("value"), "credibility": e.get("credibility"), "plausible_range": e.get("plausible_range"), "flag_only": e.get("flag_only", False)}
        return e.get("value")

    tk, t, fare, log = case["dispute_ticket"], case["trip_data"], case.get("fare_breakdown") or {}, case.get("surge_pricing_log") or {}
    chat = case.get("chat_logs") or []
    gps = sorted(case.get("gps_telemetry") or [], key=lambda g: E.T(g["timestamp"]))
    cht = lambda c: f"E-CHT-{chat.index(c) + 1:02d}"
    pb = "PB-FC-SURGE"
    tm = P("MONEY_TOLERANCE_SGD")

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
    surge_case = has_surge_evidence(case)
    code = kb.resolve("TX-CASE", tk["dispute_type"])
    tr.claim_type = code if (code != "FC-SURGE" or surge_case) else "FC-FAREMISMATCH"
    tr.step("PB-INTAKE", 3, "CLS-05, CLS-02, CLS-04", f"dispute_type {tk['dispute_type']!r} -> {tr.claim_type}"
            + ("" if surge_case else " (a fare_dispute with no surge record and no surge multiplier in the fare breakdown is not a surge dispute)")
            + "; one claim contesting the final fare against the upfront quote" + ("; a safety claim is added as the primary claim" if hits else ""), ["E-TKT-01", "E-PAY-01"])
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

    # ---------------- PB-FC-SURGE
    q, a = fare.get("upfront_quote") or {}, fare.get("actual_fare") or {}
    q_tot, a_tot = _num(q.get("total")), _num(a.get("total"))
    q_sub, a_sub = _num(q.get("surgeable_subtotal")), _num(a.get("surgeable_subtotal"))
    q_sur, a_sur = _num(q.get("surge_amount")), _num(a.get("surge_amount"))
    q_mult_fb, a_mult_fb = _num(q.get("surge_multiplier")), _num(a.get("surge_multiplier"))
    q_mult, s_mult = _num(log.get("quote_time_surge")), _num(log.get("trip_start_surge"))
    quote_trip, actual_trip, diff_trip = _num(t.get("upfront_quote")), _num(t.get("actual_fare")), _num(t.get("fare_difference"))
    comp = fare.get("comparison") or {}
    tr.amount_at_stake = abs(diff_trip if diff_trip is not None else ((a_tot - q_tot) if None not in (a_tot, q_tot) else 0.0))
    notes = []

    # 1 DQ-05 fare arithmetic: the figures of the three records agree, and each surge amount is the surge on the surgeable subtotal only (Section 3.5)
    complete = None not in (q_tot, a_tot, q_sub, a_sub, q_sur, a_sur, q_mult, s_mult)
    diff = _r2(a_tot - q_tot) if None not in (a_tot, q_tot) else None
    surge_diff = _r2(a_sur - q_sur) if None not in (a_sur, q_sur) else None
    if complete:
        for tag, tot, sub, sur, mult in (("quote", q_tot, q_sub, q_sur, q_mult), ("actual fare", a_tot, a_sub, a_sur, s_mult)):
            if abs(sur - sub * (mult - 1)) > tm:
                notes.append(f"the {tag} surge amount {sur:.2f} is not the surgeable subtotal {sub:.2f} times the surge above 1.0 ({mult})")
            if sur - (tot - sub) > tm:
                notes.append(f"the {tag} surge amount is more than the part of the fare above the surgeable subtotal")
        if (q_mult_fb is not None and abs(q_mult_fb - q_mult) > 1e-9) or (a_mult_fb is not None and abs(a_mult_fb - s_mult) > 1e-9):
            notes.append("the surge multipliers in the fare breakdown and in the surge record differ")
        if quote_trip is not None and abs(quote_trip - q_tot) > tm or actual_trip is not None and abs(actual_trip - a_tot) > tm:
            notes.append("the quote or the final fare differs between the trip record and the fare breakdown")
        if diff_trip is not None and abs(diff_trip - diff) > tm:
            notes.append(f"the stated fare difference {diff_trip:.2f} is not final fare minus quote {diff:.2f}")
        if comp.get("total_difference") is not None and abs(float(comp["total_difference"]) - diff) > tm:
            notes.append("the comparison block's total difference is not final fare minus quote")
        if comp.get("surge_amount_difference") is not None and abs(float(comp["surge_amount_difference"]) - surge_diff) > tm:
            notes.append("the comparison block's surge difference is not the difference of the surge amounts")
    figures_ok = complete and not notes
    if complete and not figures_ok:
        tr.flag("FIGURES_DISAGREE")
    tr.finding("F-FARE-FIGURES", {"quote": q_tot, "final_fare": a_tot, "difference": diff, "surge_difference": surge_diff, "consistent": bool(figures_ok)}, "SGD",
               basis=["E-TRP-01", "E-PAY-01"], rule="DQ-05", params=["MONEY_TOLERANCE_SGD"], status="established" if figures_ok else ("contested" if complete else "unknown"))
    tr.path("DQ-05")
    tr.step(pb, 1, "DQ-05", (f"quote {q_tot} and final fare {a_tot}: difference {diff}; surge amounts {q_sur} and {a_sur}: difference {surge_diff}; " if complete else "the fare breakdown or the surge record is incomplete; ")
            + ("the figures agree and each surge amount is the surge on the surgeable subtotal" if figures_ok else "NOT consistent (" + "; ".join(notes or ["a required figure is missing"]) + ")"), ["E-TRP-01", "E-PAY-01", "E-SRG-01"])

    # 2 FC-F07: did the surge multiplier rise between the quote and the start of the trip? (Section 3.1, 3.3)
    increased = None if None in (q_mult, s_mult) else s_mult > q_mult + 1e-9
    start = t.get("start_time")
    activated = log.get("surge_activated_at")
    timeline_ok = True if not (activated and start) else E.T(activated) <= E.T(start)
    if increased and not timeline_ok:
        notes.append("the surge was activated after the trip started, so it should not be in the fare (Appendix A: the surge in effect at trip start)")
    tr.finding("F-SURGE-CHANGE", {"quote_time": q_mult, "trip_start": s_mult, "increased": increased, "activated_at": activated}, basis=["E-SRG-01"], rule="FC-F07", status="established" if increased is not None else "unknown")
    tr.path("FC-F07")
    tr.step(pb, 2, "FC-F07", (f"surge {q_mult}x at quote time, {s_mult}x at trip start" + (f"; activated {activated[11:19]}, before the trip started at {start[11:19]}" if activated and start and timeline_ok else "")
                              if increased is not None else "the surge record does not give both multipliers"), ["E-SRG-01"])

    # 3 FC-F08: was the rider notified in the app before or at the point of pickup? (Section 3.2) A platform record, tier A.
    valid, why = notice_valid(log, start)
    notified = force.get("notified", valid)
    tr.finding("F-SURGE-NOTICE", notified, basis=["E-SRG-01"] + [cht(c) for c in chat if c["sender"] == "rider" and c["type"] == "message"], rule="FC-F08",
               status="established" if valid is not None and "notified" not in force else "read")
    tr.path("FC-F08")
    tr.step(pb, 3, "FC-F08", why + ("" if "notified" not in force else f" (forced reading: {force['notified']})"), ["E-SRG-01"])

    # 4 FC-R14: is the difference the surge and nothing else? (Section 3.4)
    solely = None
    if complete:
        solely = (diff is not None and surge_diff is not None and abs(diff - surge_diff) <= tm and abs(a_sub - q_sub) <= tm and abs((a_tot - a_sub - a_sur) - (q_tot - q_sub - q_sur)) <= tm)
    tr.finding("F-SURGE-SOLELY", solely, basis=["E-PAY-01"], rule="FC-R14", params=["MONEY_TOLERANCE_SGD"], status="established" if solely is not None else "unknown")
    tr.path("FC-R14")
    tr.step(pb, 4, "FC-R14", ("the difference equals the surge amounts' difference, the surgeable subtotal is unchanged and the rest of the fare (booking fee) is unchanged: attributable solely to the surge multiplier (Section 3.4)"
                              if solely else "the difference is not only the surge (or the fare is incomplete)") if complete else "not assessable: the fare breakdown is incomplete", ["E-PAY-01"])

    # 5 FC-R15: the Section 3.3 table
    if tr.findings.get("_discrimination") or tr.findings.get("_safety"):
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["SE-R-HUMAN-DECIDES"]
        tr.secondary_claims = [{"claim": "FARE_ABOVE_QUOTE", "amount_sgd": tr.amount_at_stake, "proposed_outcome": None}]
        tr.path("CLS-01", "SE-R01")
        tr.step(pb, 5, "CLS-01, SE-R01", "the complaint contains safety content: the whole case goes to a person with the case file only (policy v2.1 Section 5.2); no outcome, amount or measure is proposed", ["E-TKT-01"])
    elif tr.policy_gap:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"]
        tr.path("GEN-R07")
        tr.step(pb, 5, "FC-R15, GEN-R07", "no written rule applies to this trip date: " + "; ".join(w for _, w in tr.policy_gap), [])
    elif not surge_case:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"]
        tr.path("GEN-R07")
        tr.step(pb, 5, "GEN-R07", "a fare dispute with no surge record is a fare mismatch (FC-FAREMISMATCH), which has no written rule in this version: a person decides", ["E-TKT-01"])
    elif not complete or increased is None:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["FC-R-INSUFFICIENT-DATA"]
        tr.flag("RECORDS_MISSING")
        tr.path("FC-R12")
        tr.step(pb, 5, "FC-R12", "a figure of the fare breakdown or the surge record is missing: no adverse finding, a person decides", ["E-PAY-01", "E-SRG-01"])
    elif not figures_ok or not timeline_ok:
        tr.outcome, tr.reasons = "ESCALATE_HUMAN", ["GEN-R-DATA-INCONSISTENT"]
        tr.path("GEN-R02")
        tr.step(pb, 5, "FC-R15, GEN-R02", "the records disagree (" + "; ".join(notes) + "), so a person decides", ["E-PAY-01", "E-SRG-01"])
    else:
        tr.path("FC-R15")
        if not increased:
            if diff <= tm:
                tr.outcome, tr.reasons, row = "UPHOLD", ["FC-R-SURGE-NOT-HIGHER"], "the surge did not rise and the fare is not above the quote: the quoted fare, or the lower fare, applies; nothing to refund"
            else:
                tr.outcome, tr.reasons, row = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"], "the final fare is above the quote but the surge did not rise: the difference is not a surge matter, and Section 3 has no rule for it"
                tr.path("GEN-R07")
        elif notified is True:
            tr.outcome, tr.reasons, row = "UPHOLD", ["FC-R-SURGE-NOTIFIED"], "the surge rose and the rider was notified in the app: the higher fare applies, no refund"
        elif notified is None:
            tr.outcome, tr.reasons, row = "ESCALATE_HUMAN", ["FC-R-INSUFFICIENT-DATA"], "the surge rose and the record does not settle whether the rider was notified"
            tr.flag("RECORDS_MISSING")
        elif not solely:
            tr.outcome, tr.reasons, row = "ESCALATE_HUMAN", ["GEN-R-POLICY-GAP"], ("the surge rose and the rider was not notified, but the difference is not only the surge: Section 3.4 makes the full "
                                                                                    f"differential refundable only when it is, so a person decides (the surge part is S${surge_diff:.2f})")
            tr.path("GEN-R07")
            tr.attach = {"surge_part_sgd": surge_diff, "information_only": True}
        else:
            tr.outcome, tr.reasons, row = "FULL_REFUND", ["FC-R-SURGE-UNNOTIFIED"], "the surge rose between the quote and the start of the trip and the rider was not notified: full refund of the surge differential (actual fare minus quote)"
        if tr.outcome == "FULL_REFUND":
            tr.remedy = {"amount_sgd": _r2(diff), "payer": "PLATFORM", "payee": "RIDER", "form": P("REMEDY_FORM"), "attribution": "surge_differential"}
        else:
            tr.remedy = {"amount_sgd": 0.0 if tr.outcome == "UPHOLD" else None, "payer": None, "payee": None, "form": "NONE" if tr.outcome == "UPHOLD" else None}
        tr.matrix_row = row
        tr.step(pb, 5, "FC-R15", row + (f"; refund S${tr.remedy['amount_sgd']:.2f} to the original payment method" if tr.outcome == "FULL_REFUND" else ""), ["E-SRG-01", "E-PAY-01"])
    if tr.outcome == "ESCALATE_HUMAN" and not tr.remedy:
        tr.remedy = {"amount_sgd": None, "payer": None, "payee": None, "form": None, "provisional": "decided by a human"}

    # 6 precedent search (Section 7, GEN-R08)
    tr.precedents = P21.match_precedents(kb, "FC-SURGE", {"surge_increased": bool(increased), "rider_notified": notified is True, "difference_solely_surge": bool(solely)})
    tr.step(pb, 6, "GEN-R08", "precedents: " + ("; ".join(f"{p['section']} ({p['case_id']}) {'aligned' if p['aligned'] else 'distinguished on ' + ', '.join(p['differs'])}: {p['outcome']} S${p['refund_amount_sgd']:.2f}" for p in tr.precedents) or "none"), [])
    tr.step(pb, 7, "GEN-R05", "advocate briefs are produced at run time by the Rider and Driver Advocates; not simulated in this offline check", [], status="missing")

    # 7 confidence (AUTH-05): no numeric threshold decides the case, so M is 1
    req = {"E-TKT-01": True, "E-TRP-01": True, "E-PAY-01 (fare breakdown)": bool(fare), "E-SRG-01 (surge record)": bool(log)}
    soft = [f for f in tr.flags if f in E.SOFT_FLAGS]
    tr.confidence = P21.composite_confidence(kb, profile, 1.0, req, soft)
    tr.step(pb, 8, "AUTH-05", f"C = {tr.confidence['C']:.3f} (A 1.0, M 1.00, E {tr.confidence['E']:.2f}, R 1.0; soft flags {soft})", ["E-PAY-01"])
    tr.margin, tr.spread_max, tr.deviation_km = 0, 0, None
    return tr


def reading_tests(kb: KB, case: dict, profile: str, base: E.Trace) -> list[dict]:
    """Decisive test clause 1 for the one reading in a surge case: the platform's notification record. Only a record that is not a plain yes or no is read."""
    log = case.get("surge_pricing_log") or {}
    valid, _ = notice_valid(log, case["trip_data"].get("start_time"))
    if valid is not None:
        return []
    out = []
    for alt in (True, False):
        t2 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, force={"notified": alt})
        out.append({"rule": "FC-F08", "reading": "the notification record cannot be read", "other_reading": f"notified: {alt}", "outcome_other": t2.outcome, "changes": t2.outcome != base.outcome})
    return out


def decide_tier(kb: KB, tr: E.Trace, reads: list[dict], case: dict) -> dict:
    profile = tr.profile
    fraud = P21.fraud_flag_count(case)
    triggers, gates, decisive = [], [], []
    if tr.findings.get("_discrimination") or tr.findings.get("_safety"):
        return {"tier": "HUMAN", "decisive": [], "gates": ["G4 safety content"], "runtime_only_gates": [], "favoured_party": None, "section6": None,
                "triggers": ["safety content: the AI agent may only prepare a case file (policy v2.1 Section 5.2); no outcome, amount or measure is proposed (CLS-01, SE-R01)"]}
    sec6 = None
    if tr.outcome == "ESCALATE_HUMAN":
        tier = "HUMAN"
        triggers.append("FairRyde has no ruling to approve (AUTH-06): " + ", ".join(tr.reasons))
    else:
        sec6 = P21.ruling_path(kb, profile, category="fare_dispute", value=tr.amount_at_stake, confidence=tr.confidence["C_effective"], fraud_flags=fraud)
        tier = sec6["tier"]
        if tier != "AUTO":
            triggers += sec6["reasons"]
    for r in reads:
        if r["changes"]:
            decisive.append((r["rule"], f"reading as {r['other_reading']} gives {r['outcome_other']}"))
    if decisive:
        triggers.append("decisive: " + "; ".join(f"{r} ({w})" for r, w in decisive))
    if tr.fraud:
        triggers.append("fraud signal on " + ", ".join(w for w, _ in tr.fraud))
    for f, why in (("RECORDS_MISSING", "records missing"), ("FIGURES_DISAGREE", "the figures in the case file disagree (DQ-05)")):
        if f in tr.flags:
            triggers.append(why)
    if "FIGURES_DISAGREE" in tr.flags:
        gates.append("G1 data inconsistency")
    favoured = {"FULL_REFUND": "RIDER", "UPHOLD": "DRIVER"}.get(tr.outcome)
    if favoured and favoured in tr.injection_authors:
        triggers.append(f"instruction injected by the party the outcome favors ({favoured})")
    if tr.outcome != "ESCALATE_HUMAN" and tier == "AUTO" and (triggers or gates):
        tier = "APPROVE"
    return {"tier": tier, "decisive": decisive, "triggers": triggers, "gates": gates, "favoured_party": favoured, "section6": sec6,
            "runtime_only_gates": ["G2 rule conflict", "G3 history-aware vs history-blind Judge", "G7 citation and number verification", "G8 Judge runs vs rules engine"]}


def run(kb: KB, case: dict, profile: str | None = None) -> dict:
    base = evaluate(kb, copy.deepcopy(case), profile)
    canon, _ = case_adapter.prepare(case)
    reads = reading_tests(kb, canon, base.profile, base) if base.outcome != "ESCALATE_HUMAN" else []
    tier = decide_tier(kb, base, reads, canon)
    base.step("PB-FC-SURGE", 9, "AUTH-07, AUTH-01 to AUTH-04, AUTH-06", f"tier {tier['tier']}" + (f"; {len(tier['triggers'])} reason(s)" if tier["triggers"] else ""), ["E-PAY-01"])
    base.step("PB-FC-SURGE", 10, "EXP-01 to EXP-03, META-05", "explanations drafted from findings only (see the explanation drafts)", ["F-*"])
    return {"trace": base, "sensitivity": [], "readings": reads, "tier": tier, "case": canon}
