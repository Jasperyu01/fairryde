"""Explanation drafts for each party (EXP-01 to EXP-03, META-05, AUTH-00), built only from the trace: findings, evidence IDs,
parameters and the rule cards. No names are used (the parties are "you", "the driver", "the rider"), and every number in the
text is registered in numbers_used and checked afterwards (EXP-03)."""
from __future__ import annotations

import re
from datetime import datetime

SRC_WORDS = {"ORGANIZER": "the policy attached to this trip", "RYDE_POLICY": "Ryde policy", "RYDE_TOU": "Ryde Terms of Use",
             "REGULATION": "Singapore regulation", "GOV_GUIDANCE": "official guidance",
             "INDUSTRY": "industry practice, a generic assumption", "FAIRRYDE": "FairRyde assumption", "INTERNAL_STANDARD": "FairRyde method"}
PARAM_WORDS = {
    "PING_MAX_GAP_S": "the longest allowed gap between driver GPS points ({v} seconds)",
    "ARRIVAL_GEOFENCE_M": "the {v} m radius around the pick-up pin",
    "TS_TOLERANCE_S": "the {v}-second tolerance between timestamps in different records",
    "LEFT_MIN_OUTSIDE_S": "the {v} seconds a driver must be away from the pin before it counts as leaving",
    "PIN_VENUE_MAX_M": "the {v} m allowed between the pin and the named venue",
    "BOOKING_INFER_MATCH_S": "the {v}-second matching time used to infer an immediate booking",
    "BOOKING_INFER_ETA_S": "the {v}-second ETA tolerance used to infer an immediate booking",
    "SPEED_MAX_KMH": "the {v} km/h limit that marks GPS data errors",
}
ID_RE = re.compile(r"\b(?:[A-Z]{1,4}-)+[A-Z]?\d+[A-Z]?(?:\.[a-z_]+)?\b|\bR\d+\b")
NUM_RE = re.compile(r"S\$\d+(?:\.\d+)?|\d{1,2}:\d{2}:\d{2}|\d[\d,]*(?:\.\d+)?")


def _hms(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M:%S")


def _id_parts(i: str):
    m = re.match(r"^(.*-)(\d+)$", i)
    return (m.group(1), int(m.group(2))) if m else (i, -1)


def _ids(ids: list[str]) -> str:
    """Evidence IDs grouped by kind and sorted by number; three or more consecutive IDs become 'E-GPS-05 to E-GPS-08'."""
    uniq = sorted({i for i in ids if i}, key=_id_parts)
    out, run = [], []

    def flush():
        out.extend([f"{run[0]} to {run[-1]}"] if len(run) >= 3 else run)
    for i in uniq:
        (p0, n0), (p1, n1) = (_id_parts(run[-1]) if run else ("", -9)), _id_parts(i)
        if run and p0 == p1 and n1 >= 0 and n1 == n0 + 1:
            run.append(i)
        else:
            flush()
            run = [i]
    flush()
    return ", ".join(out)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _rule_label(kb, rid: str, profile: str, decisive: set) -> str:
    """Source words for the rule's weakest essential element: a C rule shows its industry source, a D rule its FairRyde source."""
    r = kb.rules[rid]
    cred = r["credibility"]
    srcs = [s for s in r["sources"] if s.get("profile") in (None, "", profile)] or r["sources"]
    want = {"C": "INDUSTRY", "D": "FAIRRYDE"}.get(cred)
    pick = next((s for s in srcs if s["type"] == want), srcs[0])
    words = SRC_WORDS.get(pick["type"], pick["type"])
    if cred in ("C", "D") and pick["type"] not in ("INDUSTRY", "FAIRRYDE"):
        words += ", extended by FairRyde"
    return f"{rid} {r['name']} ({words}; credibility {cred}" + ("; decisive for the approval step" if rid in decisive else "") + ")"


def exp03_check(text: str, allowed: set) -> list[str]:
    """Numbers in the text that are not registered values (identifiers such as CW-R03 or E-GPS-05 are removed first)."""
    return [n for n in NUM_RE.findall(ID_RE.sub(" ", text)) if n not in allowed]


def noshow(kb, run: dict) -> dict:
    t, tier, case = run["trace"], run["tier"], run["case"]
    if t.reclassified_to:
        msg = f"This claim is not a driver no-show cancellation, so it is handled under {t.reclassified_to}."
        return {"rider": msg, "driver": msg, "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
    if t.findings.get("_safety"):          # AUTH-03, SE-R01: no automatic decision and no finding of fault
        msg = ("Your report includes a safety concern, so a Ryde staff member will review the whole case and decide it. "
               "FairRyde makes no automatic decision here, and the trip records have been preserved for the review.")
        return {"rider": msg, "driver": "The rider's report includes a safety concern, so a Ryde staff member will review the whole case and decide it. "
                "FairRyde makes no automatic decision here.", "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
    f, P = t.findings, t.params_used
    nums = {}

    def N(key, value, fmt="{}"):
        s = fmt.format(value)
        nums[key] = s
        return s

    amount = N("amount", f["F-CHARGE-AMOUNT"]["value"]["charged"], "S${:.2f}")
    anchor = N("anchor", _hms(f["F-WAIT-ANCHOR"]["value"]))
    start = N("start", t.wait_start.strftime("%H:%M:%S")) if t.wait_start else anchor
    win = pd_win = (t.presence_detail or {}).get("window") or [None, None]
    wend = N("window_end", _hms(win[1])) if win[1] else None
    end = N("end", _hms(case["trip_data"]["cancellation_time"]))
    elapsed = N("elapsed_s", int(f["F-WAIT-ELAPSED"]["value"]))
    thr = N("threshold_s", int(P["NO_SHOW_THRESHOLD_S"]["value"]))
    cmp_words = "at least" if P["THRESHOLD_COMPARISON"]["value"] == "at_least" else "more than"
    cd = t.contact_detail
    calls, msgs = N("driver_calls", cd["driver_calls"]), N("driver_messages", cd["driver_messages"])
    pin_m = f.get("F-PIN-VENUE", {}).get("value")
    pin_txt = N("pin_venue_m", pin_m, "{:,}") if pin_m is not None else None
    arrival, presence, rider_ev = f["F-ARRIVAL-VALID"]["value"], f["F-PRESENCE"]["value"], f["F-RIDER-EVIDENCE"]["value"]
    pd = t.presence_detail
    gps_ids = f["F-PRESENCE"]["basis"]
    arr_ids = f["F-ARRIVAL-VALID"]["basis"]
    decisive = {d[0] for d in tier["decisive"]}

    # facts, in the order of the playbook
    reason = t.reasons[0] if t.reasons else ""
    facts = []
    ad = t.arrival_detail or {}
    no_wait = ad.get("t_arr") is None and int(f["F-WAIT-ELAPSED"]["value"]) == 0     # no arrival indication: no wait to describe
    paren = lambda ids: f" ({_ids(ids)})" if ids else ""
    if arrival == "TRUE" and "ARRIVAL_UNCONFIRMED" in t.flags:
        t_arr = N("arrival", _hms(ad["t_arr"]))
        t_conf = N("confirmed", _hms(ad["t_confirm"]))
        facts.append(f"GPS did not confirm the driver at the pick-up pin when arrival was marked at {t_arr}; the first confirmation is at {t_conf}, "
                     + ("so the wait counts from then" if t_conf == start else f"and the wait counts from {start}")
                     + paren(arr_ids) + ".")
    elif arrival == "TRUE":
        facts.append(f"GPS confirms the driver's arrival at the pick-up pin{paren(arr_ids)}.")
        if t.wait_start_from == "arrival":
            facts.append(f"The trip record starts the wait at {anchor}, before the driver's arrival at {start}, so the wait counts from the arrival.")
    elif arrival == "FALSE":
        facts.append("GPS placed the car in the pick-up area only for a moment after the driver marked arrival, then outside it until the cancellation"
                     if ad.get("brief_inside") else
                     "The driver marked arrival, but no GPS point from then until the cancellation places the car in the pick-up area")
        facts[-1] += paren(arr_ids) + "."
    elif arrival == "CONTESTED":
        facts.append(f"The platform's arrival check and the driver's GPS disagree about the arrival{paren(arr_ids)}.")
    elif ad.get("t_arr") is None:
        facts.append("The trip record has no arrival indication from the driver"
                     + (", so no wait can be counted." if no_wait else f", although it records a wait start at {anchor}."))
    else:
        facts.append("There is no GPS record that confirms the driver's arrival.")
    n_out = pd.get("outliers") or 0
    ok_ = pd.get("outlier_kinds") or {}
    parts = []
    if ok_.get("brief"):
        nb, lm = ok_["brief"], N("left_min_s", int(P["LEFT_MIN_OUTSIDE_S"]["value"]))
        parts.append(f"{N('outliers_brief', nb)} GPS point{'' if nb == 1 else 's'} away from the pin {'was' if nb == 1 else 'were'} set aside as "
                     f"{'an outlier' if nb == 1 else 'outliers'}: away for at most {lm} seconds between points at the pin")
    if ok_.get("error"):
        ne = ok_["error"]
        parts.append(f"{N('outliers_error', ne)} point{'' if ne == 1 else 's'} implying an impossible speed {'was' if ne == 1 else 'were'} "
                     f"set aside as {'a data error' if ne == 1 else 'data errors'}")
    if ok_.get("ambiguous"):
        na, gs = ok_["ambiguous"], N("ambiguous_gap_s", int(ok_["ambiguous_gap_s"]))
        parts.append(f"{N('outliers_ambiguous', na)} point{'' if na == 1 else 's'} away from the pin {'was' if na == 1 else 'were'} set aside as "
                     f"{'an outlier' if na == 1 else 'outliers'}, although the points at the pin around {'it' if na == 1 else 'them'} are up to {gs} seconds apart")
    set_aside = "; ".join(parts)
    n_edge = pd.get("edge_outside") or 0
    edge = ""
    if n_edge:
        e, tl = N("edge_outside", n_edge), N("tol_s", int(P["TS_TOLERANCE_S"]["value"]))
        edge = (f"{e} point away from the pin within {tl} seconds of the start or end of the wait was not counted as leaving, because records of the "
                f"same moment can differ by that much" if n_edge == 1 else
                f"{e} points away from the pin within {tl} seconds of the start or end of the wait were not counted as leaving, because records of "
                f"the same moment can differ by that much") + paren(pd.get("edge_ids") or [])
    at_pin_ids = [i for i in gps_ids if i not in (pd.get("edge_ids") or [])]
    tail = "".join(f"; {x}" for x in (set_aside, edge) if x) + "."
    if no_wait or reason == "GEN-R-POLICY-GAP":     # no wait, or no written limit to measure presence against
        pass
    elif presence == "CONSISTENT":
        gap_txt = N("max_gap_s", int(max(pd["gaps_s"]))) if pd.get("gaps_s") else None
        facts.append(f"Every {'other ' if (n_out or n_edge) else ''}driver GPS point from {start} to {wend} is at the pick-up pin"
                     + (f", and the longest stretch without a point at the pin is {gap_txt} seconds" if gap_txt else "") + paren(at_pin_ids) + tail)
    elif presence == "SPARSE":
        facts.append(f"The longest stretch of the wait without a driver GPS point at the pick-up pin is {N('max_gap_s', int(max(pd['gaps_s'])))} seconds, "
                     f"more than the {N('gap_limit_s', int(P['PING_MAX_GAP_S']['value']))} seconds allowed, so presence is only partly shown{paren(at_pin_ids)}"
                     + tail)
    elif presence == "LEFT":
        away = int(pd["longest_outside_s"])
        facts.append("During the wait, the driver's GPS was away from the pick-up pin"
                     + (f" for at least {N('outside_s', away)} seconds" if away else "")
                     + f", up to {N('max_dist_m', round(pd['max_dist_m']), '{:,}')} m away"
                     + (", and no later point shows the car back at the pin" if pd.get("no_return") and not pd.get("left_by_approach") else "")
                     + f"{paren(gps_ids)}.")
    elif pd.get("pings"):
        facts.append(f"No usable driver GPS point during the wait shows the car at the pick-up pin{paren(gps_ids)}" + (f"; {set_aside}." if n_out else "."))
    else:
        facts.append("There are no driver GPS points during the wait.")
    amb = pd.get("ambiguous") or []
    if amb and not no_wait and reason != "GEN-R-POLICY-GAP":
        why = []
        for a in amb:
            if a["kind"] == "gap":                # already stated in the sentence about the points set aside
                continue
            elif a["kind"] == "end":
                why.append(f"the car was first seen away from the pin around the end of the wait, {N('amb_end_s', int(a['s']))} seconds after the last point at the pin")
            elif a["kind"] == "single":
                why.append("the departure rests on a single point")
            elif a["kind"] == "single_false":
                why.append("only one GPS point follows the arrival mark")
        facts.append("The GPS points therefore cannot settle whether the driver left the pick-up point during the wait." if not why else
                     "The GPS points cannot settle whether the driver left the pick-up point during the wait (" + "; ".join(dict.fromkeys(why)) + ").")
    if no_wait:
        pass
    elif reason == "GEN-R-POLICY-GAP":          # no written policy applies, so no limit is quoted
        facts.append(f"The wait lasted {elapsed} seconds, from {start} to {end} (E-TRP-01).")
    else:
        facts.append(f"The wait lasted {elapsed} seconds, from {start} to {end}; the policy for this trip requires {cmp_words} {thr} seconds (E-TRP-01).")
    if "BOUNDARY_MARGIN" in t.flags and not no_wait and reason != "GEN-R-POLICY-GAP":
        mg_i = abs(int(t.margin))
        mg = N("margin_s", mg_i) + (" second" if mg_i == 1 else " seconds")
        if mg_i == 0:
            line = "The wait reached the limit exactly" + ("" if t.dt_env.get("threshold_met") else ", but the policy requires more than the limit")
        else:
            line = (f"The wait met the limit with {mg} to spare" if t.dt_env.get("threshold_met") else f"The wait fell {mg} short of the limit")
        if "MARGIN_WITHIN_SPREAD" in t.flags:
            line += f", and the records of the start or end of the wait differ by up to {N('spread_s', int(t.spread_max))} seconds"
            timer = next((a for a in case["app_events"] if a["event_type"] == "wait_timer_started"), None)
            if timer and _hms(timer["timestamp"]) != anchor:
                line += f" (the app's wait timer started at {N('timer', _hms(timer['timestamp']))})"
        facts.append(line + ".")
    if not no_wait:
        facts.append(f"The driver called {_plural(int(calls), 'time')} and sent {_plural(int(msgs), 'message')} during the wait ({_ids(cd['call_ids'] + cd['message_ids'])})."
                     if cd["call_ids"] or cd["message_ids"] else "The trip record shows no call or message from the driver during the wait.")

    # outcome lines
    if reason == "CW-R-OUT-OF-WINDOW":
        days = N("days_filed", int(f["F-FILING-WINDOW"]["value"]))
        window = N("window_days", int(P["WAIVER_WINDOW_DAYS"]["value"]))
        out_r = f"Outcome: the {amount} fee stands, because the request was filed {days} days after the trip, outside the {window}-day window for waiver requests."
        out_d = f"Outcome: the {amount} fee stands; the rider's request was filed after the waiver window."
        facts = []
    elif t.outcome == "UPHOLD":
        payee = {"DRIVER": "the driver, as compensation for the wait"}.get(t.remedy.get("fee_payee"), "the platform")
        out_r = f"Outcome: the {amount} cancellation fee stands. It goes to {payee} (CW-R09)."
        out_d = f"Outcome: the {amount} cancellation fee stands. It goes to {payee} (CW-R09)."
    elif t.outcome == "WAIVE_FEE":
        form = {"WALLET_VOUCHER": "as a Ryde wallet voucher"}.get(t.remedy.get("form"), "")
        out_r = f"Outcome: you are eligible for a refund of the {amount} cancellation fee {form}.".replace("  ", " ").replace(" .", ".")
        out_d = f"Outcome: the {amount} cancellation fee is waived for the rider."
    else:
        row = next((x for x in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"] if x["row"] == t.dt_row), {})
        why = "no written rule covers this case" if reason == "GEN-R-POLICY-GAP" else row.get("plain", "the facts need a person's judgment").split(", so ")[0]
        out_r = out_d = f"Outcome: a Ryde staff member will decide this case, because {why}."
    status = {"AUTO": "This decision was made automatically.",
              "APPROVE": "This is a provisional decision; a Ryde staff member checks it before it takes effect.",
              "HUMAN": "A Ryde staff member decides this case."}.get(tier["tier"], "")
    if t.outcome == "ESCALATE_HUMAN":
        status = ""

    # rules
    row_rules = []
    for dtr in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"]:
        if dtr["row"] == t.dt_row:
            row_rules = list(dtr.get("rules", []))
    if reason == "CW-R-OUT-OF-WINDOW":
        row_rules = ["MAT-04"]
    elif reason == "GEN-R-POLICY-GAP":
        row_rules = [r for r, _ in t.policy_gap] + ["GEN-R07"]
    others = [r for r in t.rules_on_path + t.rules_used if r not in row_rules]
    rules_txt = ("Rules that decided the outcome: " + "; ".join(_rule_label(kb, r, t.profile, decisive) for r in row_rules) + ". "
                 + ("Also used: " + "; ".join(_rule_label(kb, r, t.profile, decisive) for r in others) + "." if others else ""))

    # missing evidence, history, generic assumptions, review
    missing = [k for k, ok in t.confidence["evidence_present"].items() if not ok and not k.startswith("rider-side")]
    miss_common = ("Missing evidence: " + "; ".join(missing) + "." if missing else "")
    miss_r = miss_common + (" There is no GPS trace from your phone and no call or message from you in the trip record."
                            if rider_ev != "STRONG" else "")
    pin_note = (f" The pick-up pin is about {pin_txt} m from the address of {t.venue_name}; if you waited at the venue entrance you may not have been at the pin."
                if t.pin_mismatch and pin_txt else "")
    pin_note_d = (f" The pick-up pin is about {pin_txt} m from the address of {t.venue_name}, which was noted." if t.pin_mismatch and pin_txt else "")
    history = " Account history was used only to decide whether a person reviews this case; it did not affect the outcome."
    generic = ""
    if "GENERIC_ASSUMPTION_USED" in t.flags:
        items = []
        for srow in run.get("sensitivity", []):
            if srow["decisive"]:
                v = srow["value"]
                words = PARAM_WORDS.get(srow["param"], srow["param"] + " ({v})").format(v=N(f"param_{srow['param']}", v))
                items.append(f"{words}, used by {', '.join(srow['rules_using']) or 'the rules'}")
        for rid, why in tier["decisive"]:
            if rid.startswith("DT-"):
                row = next((x for x in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"] if x["row"] == rid.split()[-1]), {})
                items.append(f"the rule for this situation ({row.get('plain', rid)})")
            elif rid == "CW-F03B":
                items.append("where the wait starts when GPS confirms the driver only after the arrival mark (CW-F03B)" if t.wait_start_from == "ping"
                             else "starting the wait at the confirmed arrival instead of the earlier wait start in the trip record (CW-F03B)")
            elif "reading" in why:
                items.append(f"how the rider's statement was read ({rid})")
        generic = " Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: " + "; ".join(dict.fromkeys(items)) + "."
    review = " If you disagree, you can ask for a human review through RydeHELP."

    rider = " ".join([out_r, status] + facts) + " " + rules_txt + " " + miss_r.strip() + pin_note + history + generic + review
    driver = " ".join([out_d, status] + facts) + " " + rules_txt + " " + miss_common + pin_note_d + history + generic + review
    rider, driver = re.sub(r"\s+", " ", rider).strip(), re.sub(r"\s+", " ", driver).strip()
    allowed = set(nums.values())
    unmatched = sorted(set(exp03_check(rider, allowed) + exp03_check(driver, allowed)))
    return {"rider": rider, "driver": driver, "numbers_used": nums, "tier": tier["tier"], "exp03_unmatched": unmatched}
