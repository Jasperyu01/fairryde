"""Explanation drafts for each party (EXP-01 to EXP-03, META-05, AUTH-00), built only from the trace: findings, evidence IDs,
parameters and the rule cards. No names are used (the parties are "you", "the driver", "the rider"), and every number in the
text is registered in numbers_used and checked afterwards (EXP-03)."""
from __future__ import annotations

import re
from datetime import datetime

SRC_WORDS = {"ORGANIZER": "the organizer's policy", "RYDE_POLICY": "Ryde policy", "RYDE_TOU": "Ryde Terms of Use",
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
ID_RE = re.compile(r"\bDISP-\d+(?:-\d+)?\b|\bv\d+\.\d+\b|\b(?:[A-Z]{1,4}-)+[A-Z]?\d+[A-Z]?(?:\.[a-z_]+)?\b|\bR\d+\b"
                   r"|\b(?:Sections?|Precedents?)\s+\d+(?:\.\d+)?(?:(?:\s*,\s*|\s+and\s+|\s+to\s+)\d+(?:\.\d+)?)*")      # clause numbers of policy v2.1 are identifiers, not quantities
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


QUOTE_RE = re.compile(r'"([^"]+)"|\u201c([^\u201d]+)\u201d')


def clause_quotes(kb) -> set:
    """The verbatim clause quotes on the rule cards (EXP-02): the only quoted text whose numbers EXP-03 exempts."""
    return {" ".join(str(s["quote"]).split()) for r in kb.rules.values() for s in r.get("sources") or [] if s.get("quote")}


def exp03_check(text: str, allowed: set, quotes: set | None = None) -> list[str]:
    """Numbers in the text that are not registered values (identifiers such as CW-R03 or E-GPS-05 are removed first). A span
    in double quotes is exempt only when it is a verbatim clause quote from a rule card with at least three words (EXP-03,
    A4); any other quoted span, such as a bare quoted number, is checked like the rest of the text."""
    def exempt(m):
        span = " ".join((m.group(1) or m.group(2)).split())
        words = re.findall(r"[A-Za-z]{2,}", span)            # a quote of a clause has words; a bare quoted number or amount is not one
        return " " if len(words) >= 3 and any(span in q for q in quotes) else m.group(0)
    if quotes:
        text = QUOTE_RE.sub(exempt, text)
    return [n for n in NUM_RE.findall(ID_RE.sub(" ", text)) if n not in allowed]


def noshow(kb, run: dict) -> dict:
    t, tier, case = run["trace"], run["tier"], run["case"]
    if t.findings.get("_safety"):          # AUTH-03, SE-R01: no automatic decision and no finding of fault; either party may have raised it (CLS-01)
        msg = ("The case includes a safety concern, so a Ryde staff member will review the whole case and decide it. "
               "FairRyde makes no automatic decision here, and the trip records have been preserved for the review.")
        return {"rider": msg, "driver": msg, "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
    if t.reclassified_to:                  # CLS-06
        what = {"CW-RIDERCANCEL": "the trip record shows that the rider canceled, so this is a rider cancellation fee case and is handled as one",
                "CW-OTHER": "the trip record shows a cancellation that was not a driver's no-show cancellation, so a Ryde staff member will handle it"}
        msg = f"This claim is not about a driver's no-show cancellation: {what.get(t.reclassified_to, 'it is handled under another case type')}."
        return {"rider": msg, "driver": msg, "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
    if t.outcome == "REQUEST_INFO":        # CLS-06: the record does not settle who canceled
        msg = ("The trip record does not settle who canceled the trip, so FairRyde makes no decision on the fee yet. "
               "Ryde will check the trip record, and the case is decided once it shows who canceled.")
        return {"rider": msg, "driver": msg, "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
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
        span = f"the counted wait ({start} to {wend})" if wend else "the counted wait"
        edge = (f"{e} point away from the pin within {tl} seconds of the start or end of {span} was not counted as leaving, because records of the "
                f"same moment can differ by that much" if n_edge == 1 else
                f"{e} points away from the pin within {tl} seconds of the start or end of {span} were not counted as leaving, because records of "
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
        w0, w1 = [(datetime.fromisoformat(x) if x else None) for x in (pd.get("window") or [None, None])]
        for i_a, a in enumerate(amb):
            in_window = bool(a.get("first_out_t") and w0 and w1 and w0 <= datetime.fromisoformat(a["first_out_t"]) <= w1)
            if a["kind"] == "gap" and in_window:  # set aside inside the counted wait: already stated in the sentence about the points set aside
                continue
            if a["kind"] == "gap":
                why.append(f"a point away from the pin{', ' + a['first_out_id'] + ',' if a.get('first_out_id') else ''} lies between points at the pin "
                           f"{N(f'amb_gap_s_{i_a}', int(a['s']))} seconds apart, so the car may have been away longer than that point shows")
            elif a["kind"] == "end" and a.get("last_in") and w1 and wend:
                before_s = int((w1 - datetime.fromisoformat(a["last_in"])).total_seconds())
                why.append(f"the last point at the pin was at {N(f'amb_last_in_{i_a}', _hms(a['last_in']))}, {N(f'amb_before_end_{i_a}', before_s)} seconds "
                           f"before the counted wait ended at {wend}, and the next point{', ' + a['first_out_id'] + ',' if a.get('first_out_id') else ''} "
                           f"is away from the pin")
            elif a["kind"] == "start":
                why.append(f"the counted wait starts at {start}, but the last point before it, {a['last_out_id']} at "
                           f"{N(f'amb_last_out_{i_a}', _hms(a['last_out']))}, is away from the pin, and no point shows the car back at the pin until "
                           f"more than {N('tol_s', int(P['TS_TOLERANCE_S']['value']))} seconds into the counted wait")
            elif a["kind"] == "single":
                why.append("the departure rests on a single point")
            elif a["kind"] == "single_false":
                why.append("only one GPS point follows the arrival mark")
        facts.append("The GPS points therefore cannot settle whether the driver left the pick-up point during the wait." if not why else
                     "The GPS points cannot settle whether the driver left the pick-up point during the wait (" + "; ".join(dict.fromkeys(why)) + ").")
    merits = t.outcome == "UPHOLD" and reason == "CW-R-NOSHOW-VALID"
    after_out = pd.get("after_window_outside_ids") or []
    unsettled = {a.get("first_out_id") for a in amb if a["kind"] in ("gap", "end")}
    if merits and after_out and wend and not (unsettled & set(after_out)):
        facts.append(f"After the counted wait ended at {wend}, the driver's GPS was away from the pick-up pin{paren(after_out)}; "
                     f"the fee pays for the wait up to that point, so this is not counted as leaving.")
    gl = getattr(t, "gps_logic_detail", None) or {}
    if merits and f.get("F-GPS-LOGIC", {}).get("value"):           # CW-F04B, decision D29: say what the points alone do not show
        why = []
        if gl.get("set_aside_ids"):
            one = len(gl["set_aside_ids"]) == 1
            why.append(f"{'a point' if one else 'points'} away from the pin {'was' if one else 'were'} set aside as "
                       f"{'an outlier or a data error' if one else 'outliers or data errors'}{paren(gl['set_aside_ids'])}")
        if gl.get("not_counted_ids"):
            one = len(gl["not_counted_ids"]) == 1
            why.append(f"{'a point' if one else 'points'} away from the pin near the start or end of the counted wait "
                       f"{'was' if one else 'were'} not counted as leaving{paren(gl['not_counted_ids'])}")
        if "later_confirmation" in (gl.get("why") or []):
            why.append("GPS confirmed the driver at the pick-up pin only after the arrival mark")
        if "sparse" in (gl.get("why") or []):
            why.append("the GPS points leave part of the wait without a point at the pin")
        if why:                                 # GPS_AMBIGUOUS alone is already explained in the sentence above
            facts.append("So whether the driver arrived and stayed at the pick-up point rests on how FairRyde reads the GPS points, not on the "
                         "points alone: " + "; ".join(why) + ".")
    if no_wait:
        pass
    elif reason == "GEN-R-POLICY-GAP":          # no written policy applies, so no limit is quoted
        facts.append(f"The wait lasted {elapsed} seconds, from {start} to {end} (E-TRP-01).")
    elif t.wait_start and datetime.fromisoformat(case["trip_data"]["cancellation_time"]) < t.wait_start:
        facts.append(f"The driver cancelled at {end}, before the free wait began at {start}; the policy for this trip requires {cmp_words} {thr} seconds (E-TRP-01).")
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
        form = {"WALLET_VOUCHER": "as a Ryde wallet voucher", "ORIGINAL_PAYMENT_METHOD": "to your original payment method"}.get(t.remedy.get("form"), "")
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
    rcd = getattr(t, "rider_contact_detail", None) or {}
    rider_contact_ids, outside_ids = list(rcd.get("readings", {})), rcd.get("outside_ids") or []
    gps_line = (" The GPS points from your phone in the trip record do not show you at the pick-up point during the wait."
                if case.get("rider_gps_telemetry") else " There is no GPS trace from your phone in the trip record.")
    if rider_ev == "STRONG":
        rider_records = ""
    elif not rider_contact_ids and not outside_ids and not rcd.get("before_arrival_ids") and not rcd.get("before_arrival_gps_ids"):
        rider_records = gps_line + " There is no call or message from you in the trip record."
    else:
        rider_records = gps_line
        if rcd.get("late_ids"):
            one = len(rcd["late_ids"]) == 1
            rider_records += (f" Your {'message' if one else 'messages'} during the wait ({_ids(rcd['late_ids'])}) said you were running late or still on"
                              f" your way, so {'it does' if one else 'they do'} not show you at the pick-up point.")
        calls = [i for i in rcd.get("unclear_ids", []) if case["chat_logs"][int(i.split("-")[-1]) - 1]["type"] == "call"]
        unclear_msgs = [i for i in rcd.get("unclear_ids", []) if i not in calls]
        if calls:
            rider_records += f" The trip record shows that you called the driver ({_ids(calls)}) but not what was said."
        if unclear_msgs:
            one = len(unclear_msgs) == 1
            rider_records += (f" Your {'message' if one else 'messages'} ({_ids(unclear_msgs)}) {'does' if one else 'do'} not clearly say"
                              " whether you were at the pick-up point.")
        merits = not (t.reasons and t.reasons[0] in ("CW-R-OUT-OF-WINDOW", "GEN-R-POLICY-GAP"))
        when = "before the driver marked arrival" if (t.arrival_detail or {}).get("t_arr") else "before the wait started"
        clear = rcd.get("before_arrival_clear_ids") or []
        maybe = [i for i in rcd.get("before_arrival_ids") or [] if i not in clear]
        if clear and merits:
            one = len(clear) == 1
            rider_records += (f" Your {'message' if one else 'messages'} sent {when} ({_ids(clear)})"
                              f" {'says' if one else 'say'} you were already at the pick-up point; this was counted as evidence for your side.")
        if maybe and merits:
            one = len(maybe) == 1
            rider_records += (f" Your {'message' if one else 'messages'} sent {when} ({_ids(maybe)})"
                              f" may show where you were; {'it was' if one else 'they were'} counted as evidence for your side.")
        gw = rcd.get("before_arrival_gps_where") or {}
        if gw and merits:
            places = sorted({"the pick-up pin" if w == "pin" else f"{t.venue_name}" for w in gw.values()})
            rider_records += (f" Your phone's GPS shows you at {' and '.join(places)} {when}"
                              f" ({_ids(list(gw))}); this was counted as evidence for your side.")
        if outside_ids:
            one = len(outside_ids) == 1
            rider_records += (f" Your {'call or message' if one else 'calls or messages'} outside the wait ({_ids(outside_ids)})"
                              f" {'was' if one else 'were'} not used to judge where you were during the wait.")
    miss_r = miss_common + rider_records
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
            elif "rider's call, message or GPS" in why:
                what = ("calls, messages and phone GPS" if "E-RGPS" in why and "E-CHT" in why else
                        "phone GPS" if "E-RGPS" in why else "calls or messages")
                items.append(f"how the rider's {what} {'was' if what == 'phone GPS' else 'were'} read ({rid})")
            elif "reading" in why:
                items.append(f"how the rider's statement was read ({rid})")
        generic = " Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: " + "; ".join(dict.fromkeys(items)) + "."
    review = " If you disagree, you can ask for a human review through RydeHELP."

    rider = " ".join([out_r, status] + facts) + " " + rules_txt + " " + miss_r.strip() + pin_note + history + generic + review
    driver = " ".join([out_d, status] + facts) + " " + rules_txt + " " + miss_common + pin_note_d + history + generic + review
    rider, driver = re.sub(r"\s+", " ", rider).strip(), re.sub(r"\s+", " ", driver).strip()
    allowed = set(nums.values())
    quotes = clause_quotes(kb)
    unmatched = sorted(set(exp03_check(rider, allowed, quotes) + exp03_check(driver, allowed, quotes)))
    return {"rider": rider, "driver": driver, "numbers_used": nums, "tier": tier["tier"], "exp03_unmatched": unmatched}


# ---------------------------------------------------------------------------------------------- organizer_v2_1 (KB v0.3)
def _status(tier: dict, outcome: str) -> str:
    if outcome == "ESCALATE_HUMAN":
        return ""
    return {"AUTO": "This decision was made automatically.",
            "APPROVE": "This is a recommended decision; a Ryde staff member reviews it before it takes effect.",
            "HUMAN": "A Ryde staff member decides this case."}.get(tier["tier"], "")


def _prec_line(t, N) -> str:
    p = next((x for x in getattr(t, "precedents", []) if x["aligned"]), None)
    if not p:
        return ""
    return (f"Precedent {p['section'].split()[-1]} ({p['case_id']}) ruled the same way on the same key facts, a refund of {N('prec_amount', p['refund_amount_sgd'], 'S${:.2f}')}.")


def _reference_numbers(kb, t) -> set:
    """Reference-data values of the profile (S$10, 50, 80%, 95%, 2.0 km ...) and the confidence terms of the trace: the other numbers EXP-03 allows."""
    out = set()
    for e in kb.profiles.get(t.profile, {}).values():
        v = e.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            forms = {str(v), f"{v:.1f}", f"{v:.2f}", f"{v:.0f}"}
            out |= forms | {f"S${x}" for x in forms} | ({f"{v * 100:.0f}"} if 0 < v <= 1 else set())
    c = getattr(t, "confidence", None) or {}
    for k in ("C", "C_effective", "E", "M"):
        if isinstance(c.get(k), (int, float)):
            out |= {f"{c[k]:.2f}", f"{c[k]:.3f}"}
    return out


def _finish(kb, run, nums, rider, driver):
    t, tier = run["trace"], run["tier"]
    rider, driver = re.sub(r"\s+", " ", rider).strip(), re.sub(r"\s+", " ", driver).strip()
    allowed = set(nums.values()) | _reference_numbers(kb, t)
    quotes = clause_quotes(kb)
    unmatched = sorted(set(exp03_check(rider, allowed, quotes) + exp03_check(driver, allowed, quotes)))
    return {"rider": rider, "driver": driver, "numbers_used": nums, "tier": tier["tier"], "exp03_unmatched": unmatched}


def _sec6_line(tier: dict, N) -> str:
    s6 = tier.get("section6")
    if not s6:
        return ""
    if s6["tier"] == "AUTO":
        return (f"The disputed amount, {N('value', s6['value'], 'S${:.2f}')}, is under {N('final_below', 10, 'S${}')}, so the AI ruling is final (Section 6.1)."
                if s6["band"] == "FINAL" and s6["threshold"] is None else "The ruling meets the confidence the policy asks for (Section 6).")
    return "Why a person reviews it: " + " ".join(r.replace("this ruling's confidence", "the confidence of this ruling") for r in s6["reasons"][:1]) + "."


def policy_v21(kb, run: dict) -> dict:
    """Explanation drafts of the three organizer cases, citing policy v2.1 by section (rule EXP-01 to EXP-03, AUTH-00). Numbers are registered as in noshow()."""
    t, tier, case = run["trace"], run["tier"], run["case"]
    kind = getattr(t, "case_type", None) or "CW-NOSHOW"
    if kind == "CW-NOSHOW":
        base = noshow(kb, run)
        if t.findings.get("_safety") or t.reclassified_to or t.outcome == "REQUEST_INFO":
            return base
        nums = dict(base["numbers_used"])

        def N(key, value, fmt="{}"):
            nums[key] = fmt.format(value)
            return nums[key]
        cd = t.contact_detail
        extra = []
        if t.reasons and t.reasons[0] == "CW-R-NOCONTACT-VOID":
            extra.append(f"Under Section 2.3 the driver must send at least {N('min_msgs', 1)} chat message and make at least {N('min_calls', 1)} call before cancelling for a no-show; the trip record shows "
                         f"{N('calls_v', int(cd['driver_calls']))} calls and {N('msgs_v', int(cd['driver_messages']))} messages, so the fee is voided (Precedent 7.3).")
        elif t.outcome == "UPHOLD":
            extra.append(f"Under Section 2.3 the driver had to send at least one chat message and make at least one call before cancelling; the trip record shows {N('calls_v', int(cd['driver_calls']))} call "
                         f"and {N('msgs_v', int(cd['driver_messages']))} messages, so the obligation was met. Precedent 7.3 voided a fee where the driver had made no contact, which is not the case here.")
        wait = f"Section 2.1 counts the free wait from the scheduled pickup time and Section 2.2 sets the fee at {N('fee_v', 5, 'S${:.2f}')}."
        s6 = _sec6_line(tier, N)
        add = " ".join(x for x in [wait] + extra + [s6] if x)
        rider, driver = base["rider"] + " " + add, base["driver"] + " " + add
        return _finish(kb, run, nums, rider, driver)
    nums = {}

    def N(key, value, fmt="{}"):
        s_ = fmt.format(value)
        nums[key] = s_
        return s_
    f, P = t.findings, t.params_used
    status = _status(tier, t.outcome)
    review = " If you disagree, you can ask for a human review through RydeHELP."
    history = " Account history did not affect the outcome."
    if t.findings.get("_safety"):
        msg = ("The case includes a safety concern, so a Ryde staff member will review the whole case and decide it. FairRyde prepares the case file only and proposes no outcome, "
               "amount or measure (Section 5.2).")
        return {"rider": msg, "driver": msg, "numbers_used": {}, "tier": tier["tier"], "exp03_unmatched": []}
    if kind == "FC-ROUTE":
        dev = f["F-DEVIATION-KM"]["value"]
        fare_fig = f["F-FARE-FIGURES"]["value"]
        facts = []
        if dev is not None:
            t_ = t.params_used.get("DEVIATION_TOLERANCE_KM", {}).get("value", 1.0)
            facts.append(f"The recorded trip distance is {N('actual_km', run['case']['trip_data'].get('actual_distance_km'))} km and the recommended route is {N('rec_km', run['case']['optimal_route']['estimated_distance_km'])} km, "
                         f"a deviation of {N('dev_km', dev)} km; Section 1.3 allows {N('tol_km', t_)} km without a refund (E-TRP-01, E-RTE-01).")
        justified = f["F-JUSTIFIED"]
        if justified["basis"]:
            facts.append(f"The traffic data shows an incident on the road of the recommended route during the trip ({_ids(justified['basis'])}), so the reroute had a traffic reason (Section 1.4).")
        elif justified["status"] != "unknown":
            facts.append("The traffic data shows no incident on the roads of the recommended route during the trip, so the reroute has no traffic justification (Section 1.4).")
        nd = getattr(t, "notice_detail", {"on_time": [], "unclear": [], "late": []})
        if f["F-NOTICE"]["value"] == "NO":
            facts.append("No message or call from the driver before or at the point of deviation told the rider about the route change and the reason" + (f" ({_ids(f['F-NOTICE']['basis'])})" if f["F-NOTICE"]["basis"] else "") + "; Section 1.2 requires it.")
        elif f["F-NOTICE"]["value"] == "YES":
            facts.append(f"The driver told the rider about the route change before or at the deviation ({_ids(nd['on_time'])}), as Section 1.2 requires.")
        else:
            facts.append(f"A driver message or call before the deviation may have told the rider ({_ids(nd['unclear'])}), but its words do not settle it.")
        amt = t.remedy.get("amount_sgd") if t.remedy else None
        if t.outcome in ("PARTIAL_REFUND", "FULL_REFUND"):
            tolls = fare_fig.get("excess_tolls")
            tail = (f" The tolls of {N('tolls', tolls, 'S${:.2f}')} for the longer route pass through at cost and are not refunded." if tolls else "")
            out_r = f"Outcome: you are eligible for a refund of {N('amount', amt, 'S${:.2f}')}, the fare charged for the extra distance, to your original payment method (Section 1.3)."
            out_d = f"Outcome: {N('amount_d', amt, 'S${:.2f}')}, the fare charged for the extra distance, is refunded to the rider (Section 1.3)."
            if t.outcome == "PARTIAL_REFUND":
                out_d += " The reroute was accepted as justified by traffic, so the tolls and the rest of the fare stand; the refund is for the missing notice to the rider."
            facts.append(tail.strip())
        elif t.outcome == "UPHOLD":
            out_r = out_d = "Outcome: no refund is due under Section 1.3."
        else:
            out_r = out_d = "Outcome: a Ryde staff member will decide this case, because " + ("no written rule covers it" if "GEN-R-POLICY-GAP" in t.reasons else "the records do not settle it") + "."
        facts.append(_prec_line(t, N))
        facts.append(_sec6_line(tier, N) if tier["tier"] == "AUTO" else "Why a person reviews it: " + (tier["section6"]["reasons"][0] if tier.get("section6") else "; ".join(tier["triggers"][:1])) + ".")
        rules = "Rules used: " + "; ".join(_rule_label(kb, r, t.profile, {d[0] for d in tier["decisive"]}) for r in dict.fromkeys(list(t.rules_on_path) + list(t.rules_used)) if r in kb.rules) + "."
        generic = ""
        if "GENERIC_ASSUMPTION_USED" in t.flags:
            generic = " Part of this decision rests on FairRyde's way of matching a traffic incident to the recommended route, which the policy does not define (FC-F06B)."
        text = " ".join(x for x in [out_r, status] + facts if x)
        textd = " ".join(x for x in [out_d, status] + facts if x)
        return _finish(kb, run, nums, text + " " + rules + history + generic + review, textd + " " + rules + history + generic + review)
    # FC-SURGE
    sc = f["F-SURGE-CHANGE"]["value"]
    fig = f["F-FARE-FIGURES"]["value"]
    facts = []
    if sc.get("increased") is not None:
        facts.append(f"The surge multiplier was {N('q_mult', sc['quote_time'], '{:.1f}')}x at quote time and {N('s_mult', sc['trip_start'], '{:.1f}')}x at the start of the trip (E-SRG-01); "
                     f"the quote of {N('quote', fig['quote'], 'S${:.2f}')} was binding at the multiplier in effect when it was given (Section 3.1) and the final fare is {N('final', fig['final_fare'], 'S${:.2f}')}.")
    notice = f["F-SURGE-NOTICE"]["value"]
    if notice is False:
        facts.append("The platform's surge record shows that the rider was not notified in the app before the trip started (Section 3.2).")
    elif notice is True:
        facts.append("The platform's surge record shows that the rider was notified in the app before the trip started (Section 3.2).")
    if f["F-SURGE-SOLELY"]["value"] and sc.get("increased"):
        facts.append(f"The difference of {N('diff', fig['difference'], 'S${:.2f}')} is entirely the surge: the surgeable subtotal is unchanged and the booking fee is exempt from surge (Sections 3.4 and 3.5).")
    if t.outcome == "FULL_REFUND":
        amt = t.remedy["amount_sgd"]
        out_r = f"Outcome: you are eligible for a refund of the surge differential, {N('amount', amt, 'S${:.2f}')}, to your original payment method (Section 3.3)."
        out_d = f"Outcome: the surge differential, {N('amount_d', amt, 'S${:.2f}')}, is refunded to the rider because the rider was not notified (Section 3.3)."
    elif t.outcome == "UPHOLD":
        out_r = out_d = "Outcome: the final fare stands and no refund is due (Section 3.3)."
    else:
        out_r = out_d = "Outcome: a Ryde staff member will decide this case, because " + ("no written rule covers it" if "GEN-R-POLICY-GAP" in t.reasons else "the records do not settle it") + "."
    facts.append(_prec_line(t, N))
    facts.append(_sec6_line(tier, N) if tier["tier"] == "AUTO" else "Why a person reviews it: " + (tier["section6"]["reasons"][0] if tier.get("section6") else "; ".join(tier["triggers"][:1])) + ".")
    rules = "Rules used: " + "; ".join(_rule_label(kb, r, t.profile, {d[0] for d in tier["decisive"]}) for r in dict.fromkeys(list(t.rules_on_path) + list(t.rules_used)) if r in kb.rules) + "."
    text = " ".join(x for x in [out_r, status] + facts if x)
    textd = " ".join(x for x in [out_d, status] + facts if x)
    return _finish(kb, run, nums, text + " " + rules + history + review, textd + " " + rules + history + review)
