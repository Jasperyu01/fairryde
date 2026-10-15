"""Saved responses for mock mode (app/mock_responses/<case>.json).

These are AUTHORED, not recorded: no API key was available when they were written. DISP-001 to DISP-003 and the safety demo are written by hand in
the exact JSON shape the agents are asked for; the other cases are composed from the deterministic stages (the engine's steps and findings, with
their evidence IDs), so every citation in them is real. Every fixture passes the same verifier as a live answer (tests/test_fixtures.py checks it).
A live run with --record (python -m fairryde_app.cli CASE --live --record) overwrites a fixture with what the model really said.

    python -m fairryde_app.mockgen            # (re)write all fixtures
    python -m fairryde_app.mockgen DISP-001   # one case
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import cases, config, engine_stage, evidence as ev, intake
from .kbaccess import case_adapter, get_kb

NOTE = "Authored fixture (not a recorded model answer). Replace with real answers by running the case live with --record."
REFUND_TYPES = {"PARTIAL_REFUND", "FULL_REFUND", "WAIVE_FEE", "TOLL_REFUND", "GOODWILL_CREDIT"}


def prepare(case_id: str):
    kb = get_kb()
    info = cases.get_info(case_id)
    raw = cases.load_case(case_id)
    cls = intake.classify(kb, raw, case_id, info.profile_override)
    canon, _ = case_adapter.prepare(raw)
    items = ev.extract(kb, canon)
    out = engine_stage.run_engine(kb, raw, cls, canon)
    return kb, info, cls, canon, items, out


def _ev_ids(*lists) -> list[str]:
    seen = []
    for lst in lists:
        for x in lst or []:
            x = str(x).split(".")[0]
            if re.fullmatch(r"E-[A-Z]{3}-(?:\d{2}|[RD])", x) and x not in seen:
                seen.append(x)
    return seen


def _rules_of(kb, rule_field: str) -> list[str]:
    return [r.strip() for r in re.split(r"[,;]| to ", rule_field) if r.strip() in kb.rules]


# ------------------------------------------------------------------ hand-written fixtures
def disp001() -> dict:
    rider = {
        "party": "rider",
        "stance": "The rider is owed a refund of the excess distance fare: the driver went 4.3 km beyond the recommended route and never told the rider about a reroute or why.",
        "requested_outcome": "partial refund of the excess distance fare",
        "brief": ("The recommended PIE route is 20.5 km and the car travelled 24.8 km, a deviation of 4.3 km, far above the 1 km tolerance [E-TRP-01] [E-RTE-01] [Section 1.3]. "
                  "The GPS trace shows the car off the recommended route from the second ping at 13:17 and through Geylang and the East Coast area to Changi [E-GPS-02] [E-GPS-08] [E-GPS-11]. "
                  "Section 1.2 requires the driver to tell the rider in the app chat, or aloud with a call recording, before or at the point of deviation. The only exchange about the route is the "
                  "rider asking at 13:24 whether this was the right way [E-CHT-05], and the driver answering 'Don't worry, I know the way' without naming a reroute or a reason [E-CHT-06]. "
                  "That is not the notice Section 1.2 asks for. The fare rose by S$6.50 and S$3.44 of it is the excess distance fare [E-PAY-01]. Section 1.3 refunds the excess distance fare when "
                  "the rider was not informed of a deviation over 1 km, and Precedent 7.1 did exactly that [Precedent 7.1]."),
        "arguments": [
            {"point": "The deviation is 4.3 km against a recommended route of 20.5 km, over the 1 km tolerance.", "evidence": ["E-TRP-01", "E-RTE-01", "E-GPS-02", "E-GPS-11"],
             "rules": ["FC-F02"], "policy_sections": ["Section 1.3", "Section 1.4"], "precedents": []},
            {"point": "No message or call told the rider about a reroute before or at the deviation; the driver's only reply came after the rider asked and gave no reason.",
             "evidence": ["E-CHT-05", "E-CHT-06"], "rules": ["FC-F05"], "policy_sections": ["Section 1.2"], "precedents": []},
            {"point": "The remedy Section 1.3 gives for an unannounced deviation is the excess distance fare, S$3.44, as in Precedent 7.1.", "evidence": ["E-PAY-01"],
             "rules": ["FC-R13"], "policy_sections": ["Section 1.3"], "precedents": ["Precedent 7.1"]}],
        "weaknesses": [{"point": "The traffic record shows a vehicle fire on the PIE during the trip, so the driver will say the reroute was justified; that limits the remedy to the partial refund.", "evidence": ["E-TRF-01", "E-TRF-02"]}],
        "safety_concern": False}
    driver = {
        "party": "driver",
        "stance": "The reroute was a response to a real incident on the PIE; only the missing notice is at issue, and the refund must stay limited to the excess distance fare.",
        "requested_outcome": "no refund beyond the excess distance fare; tolls and the rest of the fare stand",
        "brief": ("Section 1.1 lets a driver leave the recommended path for real-time traffic. Historical traffic data, which Section 1.4 names as the test, shows a vehicle fire on the PIE eastbound "
                  "from 13:05 to 13:50 with two lanes blocked [E-TRF-01] and heavy congestion at the PIE airport exit from 13:15 to 13:40 [E-TRF-02]; the trip ran 13:15 to 13:52 [E-TRP-01]. "
                  "The ECP was flowing freely [E-TRF-03]. So this is the 'rerouted for traffic' row of Section 1.3, and the rider arrived in 37 minutes against an estimate of 35 [E-TRP-01]. "
                  "When the rider asked, the driver answered within a minute [E-CHT-05] [E-CHT-06]. The only remedy that row gives is a partial refund of the excess distance fare, S$3.44, not the whole "
                  "S$6.50 difference, and the tolls of S$2.22 pass through at cost [E-PAY-01] [Precedent 7.1]."),
        "arguments": [
            {"point": "A vehicle fire and heavy congestion on the PIE overlapped the trip, so the reroute had a traffic justification.", "evidence": ["E-TRF-01", "E-TRF-02", "E-TRP-01"],
             "rules": ["FC-F06B"], "policy_sections": ["Section 1.1", "Section 1.4"], "precedents": []},
            {"point": "The ECP was flowing smoothly, a reasonable alternative to the blocked PIE.", "evidence": ["E-TRF-03"], "rules": ["FC-F06"], "policy_sections": ["Section 1.1"], "precedents": []},
            {"point": "A justified but unannounced reroute earns the excess distance fare only: S$3.44 of the S$6.50 difference; the S$2.22 of tolls passes through at cost.", "evidence": ["E-PAY-01"],
             "rules": ["FC-R13", "FC-R08"], "policy_sections": ["Section 1.3"], "precedents": ["Precedent 7.1"]}],
        "rebuttals": [
            {"to_rider_argument": 1, "reply": "The deviation is not disputed, but Section 1.3 gives no refund for distance alone when the reroute is justified by traffic.", "evidence": ["E-TRF-01"], "rules": [], "policy_sections": ["Section 1.3"]},
            {"to_rider_argument": 2, "reply": "The driver reassured the rider within a minute of the question; the reply did not name the reroute, but the rider was never refused an answer.", "evidence": ["E-CHT-05", "E-CHT-06"], "rules": [], "policy_sections": ["Section 1.2"]},
            {"to_rider_argument": 3, "reply": "Agreed that Precedent 7.1 applies; it also shows the refund stops at the excess distance fare.", "evidence": [], "rules": [], "policy_sections": [], "precedents": ["Precedent 7.1"]}],
        "concessions": [{"point": "No chat message or call before or at the deviation told the rider of the reroute and the reason.", "evidence": ["E-CHT-05", "E-CHT-06"]},
                        {"point": "The deviation of 4.3 km is over the 1 km tolerance.", "evidence": ["E-TRP-01", "E-RTE-01"]}],
        "safety_concern": False}
    judge = {
        "outcome": "PARTIAL_REFUND", "amount_sgd": 3.44, "payer": "PLATFORM", "payee": "RIDER", "confidence": 0.9, "tier": "APPROVE",
        "policy_sections": ["Section 1.2", "Section 1.3", "Section 1.4", "Section 6.2", "Precedent 7.1"],
        "rules": ["FC-R13", "FC-F02", "FC-F05", "FC-F06B", "FC-R08"],
        "evidence": ["E-TRP-01", "E-RTE-01", "E-PAY-01", "E-GPS-02", "E-CHT-05", "E-CHT-06", "E-TRF-01", "E-TRF-02"],
        "precedents": ["Precedent 7.1"],
        "reasoning": ("The recorded distance of 24.8 km against the recommended 20.5 km gives a deviation of 4.3 km, above the 1 km tolerance, and the GPS trace confirms the car left the recommended "
                      "route at 13:17 [E-TRP-01] [E-RTE-01] [E-GPS-02]. The traffic data shows a vehicle fire on the PIE eastbound from 13:05 to 13:50 and congestion at the airport exit, so the reroute "
                      "was justified [E-TRF-01] [E-TRF-02] [Section 1.4]. Section 1.2 required notice before or at the point of deviation; the chat holds none, and the driver's reply to the rider's "
                      "question names neither a reroute nor a reason [E-CHT-05] [E-CHT-06]. That is the 'traffic reroute, rider not informed, more than 1 km' row of Section 1.3 [FC-R13]: a partial refund "
                      "of the excess distance fare, S$3.44. The Rider Advocate's argument for more than that has no support in the policy; the Driver Advocate's point that tolls pass through at cost "
                      "stands [FC-R08]. Precedent 7.1 (1.8 km, justified, not informed) ruled the same way and is aligned. Because the deviation exceeds 2 km, Section 6.2 sends the ruling to human review "
                      "with the remedy recommended. Confidence is 0.9: the facts are tier A and B, the one reading in play (matching an incident to the route by road, direction and time) is FairRyde's."),
        "agreement_with_engine": True, "disagreement_note": "",
        "rider_explanation": ("You are eligible for a refund of S$3.44, the fare charged for the extra distance, to your original payment method. The trip was 24.8 km against a recommended route of "
                              "20.5 km, a deviation of 4.3 km, which is more than the 1 km Section 1.3 allows [E-TRP-01] [E-RTE-01]. Traffic data shows a vehicle fire on the PIE during your trip, so the driver "
                              "had a reason to reroute [E-TRF-01], but Section 1.2 required the driver to tell you before or at the point of deviation, and no message or call did [E-CHT-05] [E-CHT-06]. "
                              "That is why Section 1.3 refunds the excess distance fare [FC-R13]; the tolls of S$2.22 pass through at cost and the rest of the fare stands. Because the deviation is more than "
                              "2 km, a Ryde staff member confirms this recommendation before it takes effect (Section 6.2)."),
        "driver_explanation": ("The rider is refunded S$3.44, the fare charged for the extra distance, and the platform pays it. Your reroute was accepted as justified: the traffic data shows a vehicle fire "
                               "on the PIE from 13:05 to 13:50 and congestion at the airport exit [E-TRF-01] [E-TRF-02], so the rest of the fare and the tolls of S$2.22 stand (Section 1.4). The refund is for the "
                               "missing notice: Section 1.2 asks for a chat message or a spoken notice with a short reason before or at the deviation, and the record shows none [E-CHT-05] [E-CHT-06]. "
                               "Precedent 7.1 ruled the same way. Because the deviation is more than 2 km, a Ryde staff member confirms the refund before it takes effect; you can also ask for a human review."),
        "safety_concern": False}
    return {"rider_advocate": rider, "driver_advocate": driver, "judge": judge}


def disp002() -> dict:
    rider = {
        "party": "rider",
        "stance": "The no-show fee should be reversed: the rider says they were at the pick-up lobby, and the driver's pin was 1,259 m from the named venue.",
        "requested_outcome": "reverse the S$5.00 cancellation fee",
        "brief": ("The rider says they were at the Tiong Bahru Plaza lobby on time and never saw the car [E-TKT-01]. The record gives a reason: the pick-up pin where the driver was waiting is 1,259 m "
                  "from Tiong Bahru Plaza itself [E-TRP-01] [E-GEO-01], so a rider waiting at the plaza and a driver waiting at the pin were not in the same place. Section 2.1 asks the driver to wait "
                  "'at the pickup location'; the driver's GPS shows the car stationary at the pin from 08:43 [E-GPS-05] [E-GPS-06], not at the venue the rider named. The free wait ended at 08:50 "
                  "(five minutes from the 08:45 scheduled time) and the driver cancelled at 08:51, one minute later [E-TRP-01]. A one-minute margin leaves little room for a rider who was a few "
                  "hundred metres away [Section 2.1] [Section 2.2]."),
        "arguments": [
            {"point": "The driver waited at a pin 1,259 m from the venue the rider named, so the rider may have been at the venue while the car was at the pin.", "evidence": ["E-TRP-01", "E-GEO-01", "E-GPS-05"],
             "rules": ["CW-R11"], "policy_sections": ["Section 2.1"], "precedents": []},
            {"point": "The cancellation came only one minute after the free wait ended (08:50 to 08:51), a thin margin.", "evidence": ["E-TRP-01", "E-APP-08"], "rules": ["CW-F03"], "policy_sections": ["Section 2.1", "Section 2.2"], "precedents": []}],
        "weaknesses": [{"point": "The rider offers no record of their own position (no rider GPS or call), only the ticket, which is the rider's own statement.", "evidence": ["E-TKT-01"]},
                       {"point": "The driver sent messages and made a call before cancelling, so Precedent 7.3 (no contact at all) is distinguished.", "evidence": ["E-CHT-01", "E-CHT-03", "E-APP-07"]}],
        "safety_concern": False}
    driver = {
        "party": "driver",
        "stance": "The fee stands: the driver arrived on time, stayed at the pin, contacted the rider by message and call, and cancelled only after the free wait.",
        "requested_outcome": "the S$5.00 fee stands",
        "brief": ("The driver's GPS shows the car at the pick-up pin from 08:43, stationary until the cancellation at 08:51 [E-GPS-05] [E-GPS-06] [E-GPS-07] [E-GPS-08], and the app confirmed arrival within 10 m "
                  "and notified the rider [E-APP-04] [E-APP-05]. Section 2.3 requires one message and one call before cancelling. The driver sent four messages and made a call that rang 22 seconds "
                  "[E-CHT-01] [E-CHT-02] [E-CHT-04] [E-CHT-05] [E-CHT-03] [E-APP-07], so Precedent 7.3, where the driver made no contact at all, is distinguished [Precedent 7.3]. The free wait of "
                  "Section 2.1 ran to 08:50 and the driver cancelled at 08:51 [E-TRP-01]; Section 2.2 fixes the fee at S$5.00 and Section 6.2 makes a no-show ruling final. The rider's account is a "
                  "statement with no supporting record of the rider's position [E-TKT-01]."),
        "arguments": [
            {"point": "The driver was at the pin from 08:43 to 08:51 and the app confirmed arrival within 10 m.", "evidence": ["E-GPS-05", "E-GPS-06", "E-GPS-07", "E-GPS-08", "E-APP-04"],
             "rules": ["CW-F04", "CW-R06"], "policy_sections": ["Section 2.1"], "precedents": []},
            {"point": "Section 2.3 was met: messages and a call were sent before the cancellation.", "evidence": ["E-CHT-01", "E-CHT-02", "E-CHT-03", "E-CHT-04", "E-CHT-05", "E-APP-07"],
             "rules": ["CW-R03"], "policy_sections": ["Section 2.3"], "precedents": ["Precedent 7.3"]},
            {"point": "The cancellation followed the free wait and the fee is the fixed S$5.00.", "evidence": ["E-TRP-01", "E-POL-01"], "rules": ["CW-F03"], "policy_sections": ["Section 2.1", "Section 2.2", "Section 6.2"], "precedents": []}],
        "rebuttals": [
            {"to_rider_argument": 1, "reply": "The pin is the designated pick-up location the rider booked; the app told the rider the driver had arrived. The rider's claim to be at the venue is not backed by any record.", "evidence": ["E-APP-05", "E-TKT-01"], "rules": ["CW-R11"], "policy_sections": []},
            {"to_rider_argument": 2, "reply": "The margin is positive: 360 seconds against a 300 second free wait.", "evidence": ["E-TRP-01"], "rules": [], "policy_sections": ["Section 2.1"]}],
        "concessions": [{"point": "The pin is 1,259 m from the named venue, which can explain a rider waiting elsewhere.", "evidence": ["E-TRP-01", "E-GEO-01"]}],
        "safety_concern": False}
    judge = {
        "outcome": "UPHOLD", "amount_sgd": None, "payer": None, "payee": None, "confidence": 0.82, "tier": "APPROVE",
        "policy_sections": ["Section 2.1", "Section 2.2", "Section 2.3", "Section 6.2", "Section 6.3", "Precedent 7.3"],
        "rules": ["CW-R03", "CW-R06", "CW-F04", "CW-F04B", "CW-R11"],
        "evidence": ["E-TRP-01", "E-GPS-05", "E-GPS-06", "E-GPS-07", "E-APP-04", "E-APP-06", "E-APP-08", "E-CHT-01", "E-CHT-03", "E-APP-07", "E-GEO-01", "E-POL-01"],
        "precedents": ["Precedent 7.3"],
        "reasoning": ("The driver was at the pin from 08:43, stationary, and the app confirmed arrival within 10 m [E-GPS-05] [E-GPS-06] [E-APP-04]. The cancellation at 08:51 came 360 seconds after "
                      "the scheduled pick-up time, so the five-minute free wait of Section 2.1 had ended [E-TRP-01]. Section 2.3 is met: the driver sent four messages and made a call that rang 22 seconds "
                      "[E-CHT-01] [E-CHT-03] [E-APP-07], so Precedent 7.3, where the driver made no contact, is distinguished. The fee equals the S$5.00 of Section 2.2 [E-POL-01]. The rider's strongest "
                      "point, that the pin is 1,259 m from the named venue [E-GEO-01], is real, but the pin is the designated pick-up location and the rider offers no record of their own position "
                      "[E-TKT-01]. The upheld fee rests on FairRyde's own GPS presence logic, so the engine applies the D29 confidence penalty. Confidence is 0.82; Section 6.3 raises the threshold to 95%, "
                      "so the ruling goes to human review with the fee upheld as the recommended remedy."),
        "agreement_with_engine": True, "disagreement_note": "",
        "rider_explanation": ("The S$5.00 cancellation fee stands and nothing is refunded. The driver's GPS shows the car at the pick-up pin from 08:43 until the cancellation at 08:51 [E-GPS-05] [E-GPS-08], "
                              "and the free wait of five minutes from the 08:45 scheduled time ended at 08:50 (Section 2.1, Section 2.2). Before cancelling the driver sent messages and made a call, as Section 2.3 "
                              "requires [E-CHT-01] [E-APP-07]; Precedent 7.3 voided a fee where the driver had made no contact at all, which is not the case here. We noted that the pin is 1,259 m from "
                              "Tiong Bahru Plaza [E-GEO-01]; the pin is the pick-up location shown in the booking. A Ryde staff member reviews this recommendation before it takes effect, and you can ask for a "
                              "human review."),
        "driver_explanation": ("The S$5.00 cancellation fee stands and is paid to you as compensation for your time (Section 2.2). Your GPS places you at the pin from 08:43 until you cancelled at 08:51, "
                               "and you messaged and called the rider before cancelling, as Section 2.3 requires [E-GPS-05] [E-CHT-01] [E-APP-07]. The cancellation came after the free wait ended at 08:50 "
                               "(Section 2.1). The pin is 1,259 m from the venue the rider named [E-GEO-01], which is why a Ryde staff member reviews this recommendation before it takes effect."),
        "safety_concern": False}
    return {"rider_advocate": rider, "driver_advocate": driver, "judge": judge}


def disp003() -> dict:
    rider = {
        "party": "rider",
        "stance": "The rider is owed the S$4.50 surge differential: the surge rose after the quote and nobody told the rider.",
        "requested_outcome": "refund of the S$4.50 surge differential",
        "brief": ("The quote was S$12.00 at a 1.0x multiplier and the final fare was S$16.50 at 1.5x [E-PAY-01] [E-TRP-01]. The platform's own surge record shows the multiplier moved to 1.5x at 21:04:30, "
                  "before the trip started at 21:05, and that the rider was not notified, with no method and no time recorded [E-SRG-01]. Section 3.2 requires an in-app notification before or at pickup. "
                  "Section 3.3 gives a full refund of the surge differential, actual fare minus quote, when the rider was not notified, and Section 3.4 confirms the whole S$4.50 is surge: the "
                  "surgeable subtotal is S$9.00 in both fares [E-PAY-01]. Precedent 7.2 refunded the whole differential on the same facts [Precedent 7.2]."),
        "arguments": [
            {"point": "The multiplier rose from 1.0x to 1.5x between the quote and the start of the trip, and the quote is binding at the multiplier in effect when it was given.", "evidence": ["E-SRG-01", "E-PAY-01"],
             "rules": ["FC-F07"], "policy_sections": ["Section 3.1"], "precedents": []},
            {"point": "The surge record shows no notification to the rider, in the app or otherwise.", "evidence": ["E-SRG-01"], "rules": ["FC-F08"], "policy_sections": ["Section 3.2"], "precedents": []},
            {"point": "The whole S$4.50 is attributable to the multiplier, so Section 3.3 refunds it in full, as Precedent 7.2 did.", "evidence": ["E-PAY-01", "E-TRP-01"], "rules": ["FC-R14", "FC-R15"],
             "policy_sections": ["Section 3.3", "Section 3.4"], "precedents": ["Precedent 7.2"]}],
        "weaknesses": [{"point": "The rider only raised the fare at the end of the trip, after riding at the higher price.", "evidence": ["E-CHT-03"]}],
        "safety_concern": False}
    driver = {
        "party": "driver",
        "stance": "Surge pricing and the notification are the platform's, not the driver's; if a refund is due it must not be taken from the driver.",
        "requested_outcome": "no consequence for the driver; any refund paid by the platform",
        "brief": ("The driver does not set the multiplier or send the surge notification; both sit in the platform's surge record [E-SRG-01]. Section 3.2 puts the notification duty on the platform "
                  "('the rider MUST be notified via an in-app notification'), so if the record shows none, the shortfall is the platform's. The driver accepts the figures: S$12.00 quote, S$16.50 final fare, "
                  "a S$4.50 difference that is entirely the surge, with the booking fee exempt under Section 3.5 [E-PAY-01]. The chat shows the rider asked about the fare only after the ride "
                  "[E-CHT-03]. The driver's request is that any refund of the differential be paid by the platform and not recovered from the driver."),
        "arguments": [
            {"point": "The multiplier and the notification are platform functions recorded in the surge log; the driver took no action on either.", "evidence": ["E-SRG-01"], "rules": ["FC-F08"],
             "policy_sections": ["Section 3.2"], "precedents": []},
            {"point": "The rider first raised the fare after the trip ended, so the driver had no chance to explain it during the ride.", "evidence": ["E-CHT-03", "E-TRP-01"], "rules": [], "policy_sections": [], "precedents": []}],
        "rebuttals": [{"to_rider_argument": 1, "reply": "Agreed on the figures; the change of multiplier is the platform's.", "evidence": ["E-SRG-01"], "rules": [], "policy_sections": ["Section 3.1"]},
                      {"to_rider_argument": 2, "reply": "The record says not notified; the driver has no evidence to the contrary.", "evidence": ["E-SRG-01"], "rules": [], "policy_sections": ["Section 3.2"]},
                      {"to_rider_argument": 3, "reply": "Accepted, provided the platform pays it.", "evidence": ["E-PAY-01"], "rules": [], "policy_sections": ["Section 3.3"]}],
        "concessions": [{"point": "The surge record shows the rider was not notified.", "evidence": ["E-SRG-01"]},
                        {"point": "The full S$4.50 difference is the surge.", "evidence": ["E-PAY-01"]}],
        "safety_concern": False}
    judge = {
        "outcome": "FULL_REFUND", "amount_sgd": 4.5, "payer": "PLATFORM", "payee": "RIDER", "confidence": 0.97, "tier": "AUTO",
        "policy_sections": ["Section 3.1", "Section 3.2", "Section 3.3", "Section 3.4", "Section 3.5", "Section 6.1", "Precedent 7.2"],
        "rules": ["FC-F07", "FC-F08", "FC-R14", "FC-R15", "DQ-05"],
        "evidence": ["E-SRG-01", "E-PAY-01", "E-TRP-01", "E-CHT-03"],
        "precedents": ["Precedent 7.2"],
        "reasoning": ("The surge multiplier rose from 1.0x to 1.5x at 21:04:30, before the trip began at 21:05, and the platform's record shows the rider was not notified [E-SRG-01] [E-TRP-01]. "
                      "The quote of S$12.00 is binding at the multiplier in force when it was given (Section 3.1), the final fare is S$16.50, and the S$4.50 difference is the surge alone: the surgeable "
                      "subtotal is S$9.00 in both fares and the booking fee is exempt [E-PAY-01] [Section 3.4] [Section 3.5]. Section 3.3 refunds the whole surge differential when the rider was not "
                      "notified [FC-R15]. Both advocates agree on the facts; the Driver Advocate's point is about who pays, and the notification duty is the platform's. Precedent 7.2 (1.4x, not "
                      "notified, the whole differential refunded) is aligned. The amount is under S$10 and the Section 6 constraint shows no raised threshold, so under Section 6.1 the AI "
                      "ruling is final. Confidence 0.97: the records are tier A and agree."),
        "agreement_with_engine": True, "disagreement_note": "",
        "rider_explanation": ("You are eligible for a refund of the surge differential, S$4.50, to your original payment method. The surge multiplier was 1.0x when you were quoted S$12.00 and 1.5x when "
                              "the trip started, and the platform's record shows you were not notified in the app [E-SRG-01]. Section 3.2 requires that notice, and Section 3.3 refunds the whole "
                              "differential when it is missing; the whole S$4.50 is the surge, so nothing else is adjusted [E-PAY-01]. Precedent 7.2 ruled the same way. This decision was made automatically "
                              "(Section 6.1), and you can ask for a human review through RydeHELP."),
        "driver_explanation": ("The rider is refunded the surge differential, S$4.50, and the platform pays it. The surge multiplier rose from 1.0x to 1.5x before the trip started and the platform's record "
                               "shows the rider was not notified in the app, which Section 3.2 requires [E-SRG-01]. The whole S$4.50 difference is the surge [E-PAY-01] (Section 3.3). Nothing in this decision "
                               "concerns your conduct. This decision was made automatically (Section 6.1); you can ask for a human review through RydeHELP."),
        "safety_concern": False}
    return {"rider_advocate": rider, "driver_advocate": driver, "judge": judge}


def demo_safety() -> dict:
    rider = {"party": "rider",
             "account_summary": ("The rider's ticket says the final fare was S$16.50 against a quote of S$12.00 and that nobody mentioned surge [E-TKT-01]. The rider also says that when they asked the "
                                 "driver about the fare the driver shouted, locked the doors and threatened them, saying they would not get out until they paid, and that they felt unsafe [E-TKT-01]. "
                                 "In the chat the rider asked the driver to open the door and said they wanted to get out [E-CHT-03]. The rider asks for the S$4.50 difference [E-TKT-01]."),
             "evidence": ["E-TKT-01", "E-CHT-03", "E-PAY-01", "E-SRG-01"],
             "open_questions": ["Is there a call recording or in-car video of the exchange after 21:18?", "When did the rider leave the car, and how?"], "safety_concern": True}
    driver = {"party": "driver",
              "account_summary": ("The driver has filed no statement in this case file. The driver's records are the pick-up message at 21:03 [E-CHT-02] and a message at 21:18 that reads 'Pay the full fare "
                                  "first or I will not let you out of this car. Do not test me.' [E-CHT-04]. The GPS shows the car stopped at the drop-off from 21:18 [E-GPS-07]."),
              "evidence": ["E-CHT-02", "E-CHT-04", "E-GPS-07"],
              "open_questions": ["Does the driver want to give an account of the exchange?", "Is there any record of the doors being locked?"], "safety_concern": True}
    judge = {"case_summary": ("Safety case. The rider reports that the driver shouted and threatened them and would not let them out of the car until the fare was paid, and that they felt unsafe [E-TKT-01]. "
                              "A driver message at 21:18:50 reads 'Pay the full fare first or I will not let you out of this car. Do not test me.' [E-CHT-04]. The same ticket also contests the fare: S$16.50 "
                              "charged against a S$12.00 quote, a multiplier that rose from 1.0x to 1.5x, and no recorded notification [E-PAY-01] [E-SRG-01]. The fare claim is recorded as a secondary claim; "
                              "no view is taken on it or on the conduct described."),
             "timeline": [{"ts": "21:02:15", "event": "The rider messages the driver from the pick-up point.", "evidence": ["E-CHT-01"]},
                          {"ts": "21:05:00", "event": "The trip starts; the surge multiplier is 1.5x.", "evidence": ["E-TRP-01", "E-SRG-01"]},
                          {"ts": "21:18:00", "event": "The trip ends at the drop-off.", "evidence": ["E-TRP-01", "E-GPS-07"]},
                          {"ts": "21:18:30", "event": "The rider asks the driver to open the door.", "evidence": ["E-CHT-03"]},
                          {"ts": "21:18:50", "event": "The driver writes that the rider will not be let out until the fare is paid.", "evidence": ["E-CHT-04"]}],
             "disputed_points": [{"point": "What happened inside the car after the trip ended is described only by the rider's ticket and two chat messages; no other record covers it.", "evidence": ["E-TKT-01", "E-CHT-03", "E-CHT-04"]},
                                 {"point": "The fare claim is separate: the records show a multiplier change and no notification, which is for the reviewer to weigh with the rest.", "evidence": ["E-SRG-01", "E-PAY-01"]}],
             "evidence": ["E-TKT-01", "E-CHT-03", "E-CHT-04", "E-PAY-01", "E-SRG-01", "E-TRP-01", "E-GPS-07"],
             "open_questions": ["Is there a call recording or other record from inside the car?", "Has the driver been asked for an account?", "How and when did the rider leave the car?"], "safety_concern": True}
    return {"rider_advocate:case_file": rider, "driver_advocate:case_file": driver, "judge:case_file": judge}


HANDWRITTEN = {"DISP-001": disp001, "DISP-002": disp002, "DISP-003": disp003, "DEMO-SAFETY-01": demo_safety}


# ------------------------------------------------------------------ composed fixtures
def _step_pool(kb, out) -> list[dict]:
    """Steps of the engine, as argument points, each with the evidence IDs it rests on (the findings' basis when the step names none)."""
    fallback = _ev_ids(*[f.get("basis") for f in out["findings"].values()])[:6]
    pool = []
    for s in out["steps"]:
        rules = _rules_of(kb, s["rule"])
        ids = _ev_ids(s.get("evidence")) or fallback
        if ids and rules and any(r in out["rules"] for r in rules) and s["rule"] not in ("GEN-R04", "CLS-01", "MAT-01"):
            pool.append({"point": s["result"][:330], "evidence": ids[:6], "rules": rules[:2], "policy_sections": [], "precedents": []})
    return pool


def compose_ruling(kb, info, cls, items, out) -> dict:
    favoured = "rider" if out["outcome"] in REFUND_TYPES else "driver"
    pool = _step_pool(kb, out) or [{"point": "The record of the trip supports the engine's findings.", "evidence": ["E-TRP-01"], "rules": [], "policy_sections": [], "precedents": []}]
    ticket = {"point": "The ticket is the claimant's own statement and is tier D evidence; the decisive facts come from the platform and GPS records.", "evidence": ["E-TKT-01"], "rules": [], "policy_sections": [], "precedents": []}
    amt = out["amount_sgd"]
    amount_txt = f"S${amt:.2f}" if amt else "no payment"
    cite = lambda pts: " ".join(f"[{i}]" for i in _ev_ids(*[p["evidence"] for p in pts])[:6])
    if favoured == "rider":
        r_args, d_args = pool[:3], [ticket]
        r_stance = f"The rider is entitled to {amount_txt}: the records support the claim."
        d_stance = "The charge should be limited to what the records show; the claim is contestable."
        r_weak = [{"point": "The ticket alone is the rider's own statement.", "evidence": ["E-TKT-01"]}]
        d_conc = [{"point": p["point"][:200], "evidence": p["evidence"]} for p in pool[:2]]
        r_brief = "The records support the rider: " + " ".join(p["point"][:200] for p in r_args[:2]) + " " + cite(r_args)
        d_brief = "The driver contests the claim on the weight of the ticket, which is a statement, but concedes what the records show. " + cite(d_conc and pool[:2])
    else:
        r_args, d_args = [ticket], pool[:3]
        r_stance = "The charge should not stand: the rider's account is not fully answered by the records."
        d_stance = "The charge stands: the platform and GPS records establish the conditions of the rule."
        r_weak = [{"point": p["point"][:200], "evidence": p["evidence"]} for p in pool[:2]]
        d_conc = [{"point": "The rider's statement disputes the charge.", "evidence": ["E-TKT-01"]}]
        r_brief = "The rider says the charge is wrong [E-TKT-01]; the rider's strongest point is the margin and the lack of a rider-side record. " + cite(pool[:2])
        d_brief = "The records establish the conditions of the rule: " + " ".join(p["point"][:200] for p in d_args[:2]) + " " + cite(d_args)
    rider = {"party": "rider", "stance": r_stance, "requested_outcome": "refund" if favoured == "rider" else "reverse the charge", "brief": r_brief, "arguments": r_args, "weaknesses": r_weak, "safety_concern": False}
    driver = {"party": "driver", "stance": d_stance, "requested_outcome": "the charge stands" if favoured == "driver" else "limit the refund", "brief": d_brief, "arguments": d_args,
              "rebuttals": [{"to_rider_argument": 1, "reply": "The platform and GPS records answer this point.", "evidence": pool[0]["evidence"][:3], "rules": [], "policy_sections": []}],
              "concessions": d_conc, "safety_concern": False}
    sections = []
    if cls.profile == "organizer_v2_1":
        basis = kb.expected.get(info.case_id, {}).get("basis_sections") or []
        sections = [re.sub(r" \(.*\)$", "", b) for b in basis if re.match(r"(Section|Precedent) \d", b)]
    else:
        for rid in out["rules"]:
            for s in kb.rules.get(rid, {}).get("sources", []):
                if s.get("doc") in kb.sources and s["doc"] not in sections and s.get("profile") in (None, "", cls.profile):
                    sections.append(s["doc"])
        sections = sections[:3]
    conf = 0.95 if out["engine_tier"] == "AUTO" else 0.86
    exp = out.get("explanations") or {}
    judge = {"outcome": out["outcome"], "amount_sgd": out["amount_sgd"], "payer": out["payer"], "payee": out["payee"], "confidence": conf, "tier": out["engine_tier"],
             "policy_sections": sections, "rules": [r for r in out["rules"] if r in kb.rules][:8], "evidence": _ev_ids(*[p["evidence"] for p in pool])[:10],
             "precedents": ["Precedent " + p["section"].split()[-1] for p in out["precedents"] if p["aligned"]] if cls.profile == "organizer_v2_1" else [],
             "reasoning": "The rules engine's findings match the evidence: " + " ".join(p["point"][:220] for p in pool[:3]) + f" The ruling is {out['outcome']}; confidence {conf} reflects the engine tier {out['engine_tier']}.",
             "agreement_with_engine": True, "disagreement_note": "", "rider_explanation": exp.get("rider", ""), "driver_explanation": exp.get("driver", ""), "safety_concern": False}
    return {"rider_advocate": rider, "driver_advocate": driver, "judge": judge}


def compose_case_file(kb, info, cls, canon, items, out) -> dict:
    by_id = {i["id"]: i for i in items}
    tk = by_id["E-TKT-01"]["data"]
    rider_msgs = [i for i in items if i["id"].startswith("E-CHT") and i["data"].get("sender") == "rider" and i["data"].get("type") == "message"]
    driver_msgs = [i for i in items if i["id"].startswith("E-CHT") and i["data"].get("sender") == "driver" and i["data"].get("type") == "message"]
    first = re.split(r"(?<=[.!?])\s+", tk.get("description") or "")[:2]
    why = "a safety concern" if out["case_file_reason"] == "SAFETY" else "no written rule in code for this claim type (GEN-R07)"
    rider = {"party": "rider", "account_summary": f"The rider's ticket says: \"{' '.join(first)}\" [E-TKT-01]. " + (f"The rider also wrote {len(rider_msgs)} message(s) in the chat [{', '.join(i['id'] for i in rider_msgs[:3])}]." if rider_msgs else "The rider wrote no chat messages."),
             "evidence": _ev_ids(["E-TKT-01"], [i["id"] for i in rider_msgs]), "open_questions": ["What further records exist on the rider's side?"], "safety_concern": out["case_file_reason"] == "SAFETY"}
    driver = {"party": "driver", "account_summary": ("The driver has filed no statement in this case file. " + (f"The driver wrote {len(driver_msgs)} message(s) in the chat [{', '.join(i['id'] for i in driver_msgs[:3])}]." if driver_msgs else "The driver's records are the GPS trace and app events.")),
              "evidence": _ev_ids([i["id"] for i in driver_msgs], ["E-TRP-01"]), "open_questions": ["Does the driver wish to give an account?"], "safety_concern": out["case_file_reason"] == "SAFETY"}
    timeline = [{"ts": (i["ts"] or "")[11:19], "event": i["summary"][:120], "evidence": [i["id"]]} for i in sorted((x for x in items if x["ts"] and x["id"].startswith(("E-APP", "E-CHT"))), key=lambda x: x["ts"])[:8]]
    findings = [{"point": f"{k}: {json.dumps(v.get('value'), ensure_ascii=False)[:160]}", "evidence": _ev_ids(v.get("basis"))} for k, v in list(out["findings"].items())[:3]]
    judge = {"case_summary": f"This case goes to a person because of {why}. The ticket is a claim of type {cls.claim_label or cls.dispute_type_raw} filed by the {cls.filed_by} [E-TKT-01]. The agents gathered the evidence and summarized the accounts; they propose no outcome, amount or measure.",
             "timeline": timeline, "disputed_points": findings, "evidence": _ev_ids(["E-TKT-01", "E-TRP-01"], [i["id"] for i in items if i["id"].startswith(("E-CHT", "E-APP"))][:6]),
             "open_questions": ["Which written rule, if any, applies to this claim?" if out["case_file_reason"] != "SAFETY" else "What further records exist?"], "safety_concern": out["case_file_reason"] == "SAFETY"}
    return {"rider_advocate:case_file": rider, "driver_advocate:case_file": driver, "judge:case_file": judge}


def build_fixture(case_id: str) -> dict:
    kb, info, cls, canon, items, out = prepare(case_id)
    responses = {}
    if case_id in HANDWRITTEN:
        responses.update(HANDWRITTEN[case_id]())
    if out["case_file_only"]:
        for k, v in compose_case_file(kb, info, cls, canon, items, out).items():
            responses.setdefault(k, v)
    else:
        if "judge" not in responses:
            responses.update(compose_ruling(kb, info, cls, items, out))
        for k, v in compose_case_file(kb, info, cls, canon, items, out).items():          # used by the late-safety-flag demo scenario
            responses.setdefault(k, v)
    return {"case_id": case_id, "note": NOTE, "source": "hand-written" if case_id in HANDWRITTEN else "composed from the deterministic stages", "responses": responses}


def write_all(only: list[str] | None = None) -> list[Path]:
    config.MOCK_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for info in cases.list_cases():
        if only and info.case_id not in only:
            continue
        fx = build_fixture(info.case_id)
        p = config.MOCK_DIR / f"{info.case_id}.json"
        p.write_text(json.dumps(fx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in write_all(sys.argv[1:] or None):
        print("wrote", p.relative_to(config.ROOT))
