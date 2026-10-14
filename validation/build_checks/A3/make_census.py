"""Write validation/round2/census.csv (A3, FX4): one row per element of every rule rated B or C after A2, plus the new rule
CW-F04B and FC-R07 (Jasper's decision of 14 Oct). Builder's judgment (DEP: D); this script only writes the table."""
import csv
import sys

OUT = sys.argv[1]
COLS = ["rule", "label_before", "element", "source", "element_label", "counts_toward_label", "label_after", "note"]
R = []


def rule(rid, before, after, rows):
    for el, src, lab, counts, note in rows:
        R.append({"rule": rid, "label_before": before, "element": el, "source": src, "element_label": lab,
                  "counts_toward_label": counts, "label_after": after, "note": note})


rule("CLS-01", "C", "D", [
    ("Safety content in any free text of the case gets its own SE claim, whatever else the ticket contains",
     "RYDE-15395890865561 (Ryde Code of Conduct, driver article edited 2026-04-10), item 5: 'We have a zero-tolerance approach to any form of misconduct or inappropriate behavior between drivers and passengers.'; IND-BENCHMARK-NOTES (research note 02: Lyft, Grab and DiDi handle safety incidents separately)",
     "C", "yes", "The conduct norm is Ryde's (A); handling it as a separate claim whatever the ticket says is other platforms' practice (C)."),
    ("The SE claim is decided by a human",
     "AUTH-03 (GOV-IMDA-AGENTIC: 'Organisations should define significant checkpoints or action boundaries that require human approval, especially before sensitive actions are executed.')",
     "B", "yes", "Same norm as AUTH-03 (B); industry practice (C) agrees."),
    ("What counts as safety language: assault, harassment, threats, unsafe driving, accident, injury, intoxication",
     "FAIRRYDE (FairRyde's list; no Ryde or outside source defines the trigger)",
     "D", "yes", "The trigger itself is FairRyde's word list. Step A4 (FX6) replaces it with a definition with examples; it stays FairRyde's design."),
    ("Severity S0 or S1", "FAIRRYDE (FairRyde's severity scale in taxonomy.yaml)", "D", "yes", ""),
])

rule("CW-F02B", "C", "C", [
    ("Ryde profile only (organizer cases use driver_wait_start, CW-F02)", "META-01 (profile choice)", "n/a", "no",
     "Scope pointer: which profile the rule serves, not part of its norm."),
    ("For an ADVANCE booking with an early driver, the wait starts at the later of the arrival and scheduled_time",
     "IND-GRAB-ADVANCE: 'Your driver will arrive early and wait for you for up to 15 minutes starting from the indicated pickup time.'; IND-BOLT-SCHEDULED: 'The scheduled wait time of 5 minutes will be counted only from the scheduled start of the ride.'",
     "C", "yes", "Ryde's rider policy is silent on early drivers; FairRyde fills the gap with other platforms' published practice, which is what C means. Not a FairRyde extension of a Ryde condition."),
    ("The conflict with Ryde's older driver text (it counts from the arrival) is recorded",
     "RYDE-23575142762393 (driver article, 2023-10-02): 'You arrived at the pickup location and the customer was not present within 3 minutes of your arrival.'",
     "B", "no", "Documents the conflict; the rule does not rest on it. FX9 (not done in A3): the 2024 driver pages RYDE-20244064619161 and RYDE-33362932998937 also count from 'I'm Here' and could be added to the note."),
])

rule("CW-F04", "B", "B", [
    ("The fee requires the driver to be at the pick-up location according to GPS",
     "RYDE-4407754403353 (rider article, edited 2026-02-26): 'Is at the pick-up location according to GPS data'",
     "B", "yes", "Reading it as covering the S$6.61 no-show fee is the META-04 resolution of the fee-name conflict, an interpretation, so B (as in v0.1)."),
    ("... during the waiting the fee pays for: from the confirmed wait start until the threshold is reached, or the cancellation or boarding if earlier; leaving after the threshold does not count",
     "RYDE-4407754403353 (2026-02-26): 'Is at the pick-up location according to GPS data' AND 'Has waited for more than 3 mins'; RYDE-23534478435353 (main policy page, edited 2026-02-26): 'The driver presses \"I'm Here\", waits for > 3 minutes for the rider to arrive at the pick-up point and cancels the trip (Rider NO SHOW and no trip completion)'",
     "B", "yes", "Reading the article's two joined conditions as presence for the wait, ending where the main page's 'waits for > 3 minutes ... and cancels' ends, interprets Ryde text (B). Check round 2 (GRD-01): 'at the pick-up point' in the main page belongs to the rider, not to where the driver waits."),
    ("Pings sorted by time; outside stretches after the driver is first seen inside; GPS outliers (shorter than LEFT_MIN_OUTSIDE_S and followed by an inside ping) set aside; a stretch with no later inside ping is never an outlier on duration",
     "FAIRRYDE (open item D24)", "D", "moved", "Moved to CW-F04B (FairRyde's presence logic, D)."),
    ("Data errors: a stretch implying more than SPEED_MAX_KMH is set aside and flagged GPS_DATA_ERROR (DQ-02, gate G1)",
     "FAIRRYDE (open item D24)", "D", "moved", "Moved to CW-F04B."),
    ("The approach: pings before the driver is first seen inside are never outliers on duration",
     "FAIRRYDE (open item D24)", "D", "moved", "Moved to CW-F04B."),
    ("Window edges: outside pings within TS_TOLERANCE_S of the window end (and of the start, for the approach) do not count as leaving",
     "FAIRRYDE (open item D24)", "D", "moved", "Moved to CW-F04B."),
    ("The values LEFT, SPARSE (a gap longer than PING_MAX_GAP_S), CONSISTENT and UNKNOWN (no window, no ping in it, or no confirmed arrival and no inside ping)",
     "FAIRRYDE (open items D18, D24, D26)", "D", "moved", "Moved to CW-F04B. Ryde states the condition, not how pings settle it."),
    ("GPS_AMBIGUOUS when the pings cannot settle whether the driver left",
     "FAIRRYDE (AUTH-02 trigger 11)", "D", "moved", "Moved to CW-F04B."),
    ("Parameters ARRIVAL_GEOFENCE_M, PING_MAX_GAP_S, LEFT_MIN_OUTSIDE_S, SPEED_MAX_KMH, TS_TOLERANCE_S",
     "reference_data.yaml (FAIRRYDE, D, with plausible ranges)", "D", "no",
     "Rated separately as parameters (credibility_principle) and tested case by case by the sensitivity test (decisive_definition clause 2); listed under CW-F04B in v0.2."),
])

rule("CW-F04B", "(new)", "D", [
    ("FairRyde's presence logic: the outlier, data-error, approach and window-edge rules and the values LEFT, SPARSE, CONSISTENT, UNKNOWN and GPS_AMBIGUOUS (moved from CW-F04 and shared with CW-R06's outlier step; GPS_AMBIGUOUS covers both window edges since check round 2)",
     "FAIRRYDE (open items D18, D24, D26)", "D", "yes", "Split out of CW-F04 by FX4."),
    ("F-GPS-LOGIC: true when the logic, not the pings alone, makes the driver count as arrived and present (a ping set aside that could change the presence, in the window, or the arrival, one that would otherwise have been CW-R06's moment ping; an outside ping in the window not counted as leaving; an arrival confirmed only by a later ping, CW-F03B; SPARSE; GPS_AMBIGUOUS)",
     "FAIRRYDE (FX4, step A3)", "D", "yes", "Feeds DT-CW-NOSHOW input gps_logic_decides (rows R8 and R11)."),
    ("A fee upheld while F-GPS-LOGIC is true, or would be true with a CW-F04B parameter at an end of its plausible range, needs human approval (tier APPROVE), never AUTO: no-show fees through rows R9 and R11 (D, clauses 2 and 3), waiting fees through AUTH-02 trigger 12",
     "FAIRRYDE-DECISIONS (Jasper, open item D29, 2026-10-11)", "D", "yes", "Implements D29; waiting fees have no decision table (D31), so the rule text and AUTH-02 carry it."),
])

rule("CW-R00", "B", "B", [
    ("The cancellation and waiting policy applies to all service types except RydeTAXI",
     "RYDE-4407761313305 (rider article, edited 2024-03-18): 'Cancellation Policy applies to all Service Types * in the Ryde app and is executed on a service level, not driver level.' and '*All services except RydeTAXI'",
     "B", "yes", "Ryde's own words; older than 12 months, so B."),
    ("A RydeTAXI cancellation-fee dispute has no written rule and is escalated", "GEN-R07 (policy gap, rated D on its own card)", "D", "no",
     "Pointer to GEN-R07, which carries its own label; the only outcome is escalation (tier HUMAN), so it never lets a case be decided automatically. Unlike FC-R00, the exclusion itself is Ryde's text."),
])

rule("CW-R06", "B", "B", [
    ("An arrival indication is valid only if GPS shows the driver at the pick-up location",
     "RYDE-4407754403353 (rider article, edited 2026-02-26): 'Drivers are only allowed to indicate arrival and impose the Waiting Time Fee only if he/she:' and 'Is at the pick-up location according to GPS data'",
     "B", "yes", "Read as covering the no-show fee by the META-04 resolution (interpretation), so B."),
    ("Otherwise no fee (FALSE: no GPS confirmation from the arrival to the cancellation, with remaining pings)",
     "RYDE-4407754403353: 'Otherwise, you will not be charged the $6.61 Waiting Time Fee if any of the above are not fulfilled.'",
     "B", "yes", "This clause is one side of the META-04 fee-name conflict, so it cannot count toward A."),
    ("Confirmed at the arrival by the platform's own recorded GPS arrival check",
     "ORG-DISP002: 'Driver GPS within 10m of pickup point. Speed 0 km/h. Auto-arrival confirmed.'", "A", "yes", "Organizer data."),
    ("Confirmed at the arrival by the moment ping (the last remaining ping from PING_MAX_GAP_S before to TS_TOLERANCE_S after the arrival) inside ARRIVAL_GEOFENCE_M",
     "RYDE-4407754403353 ('according to GPS data', read at the moment of the indication); look-back, tolerance and radius are FAIRRYDE parameters (D)",
     "B", "yes", "Reading Ryde's GPS condition at the moment of the indication; the parameters are rated separately and tested by the sensitivity test."),
    ("GPS outliers are set aside before the check", "FAIRRYDE (CW-F04B, open item D24)", "D", "delegated",
     "Delegated to CW-F04B: when a set-aside ping would otherwise have been CW-R06's moment ping (or lies in the window), F-GPS-LOGIC is true and an upheld fee falls in row R11 (D). Setting aside removes evidence of absence, so a FALSE found after it is also FALSE on the pings alone, except a data error (gate G1, approval)."),
    ("TRUE with ARRIVAL_UNCONFIRMED: confirmed only by a later ping", "FAIRRYDE (CW-F03B, open item D26)", "D", "delegated",
     "Delegated to CW-F03B (D): F-GPS-LOGIC is true (row R11 for an upheld fee); a short-wait waiver (R6, A) that rests on the moved start is caught by CW-F03B's start test, not by the row rating."),
    ("CONTESTED when the platform check is contradicted", "GEN-R02, DQ-01 (FAIRRYDE, D)", "D", "delegated", "Row R2 is rated D."),
    ("UNKNOWN when there is no arrival indication or no remaining ping from the arrival on", "GEN-R01 (D)", "D", "delegated", "Row R3 is rated D."),
])

rule("CW-R08", "C", "D", [
    ("A driver later than the assignment ETA plus DRIVER_LATE_GRACE_S makes the rider's cancellation fee waivable",
     "IND-BENCHMARK-NOTES (research note 02: 'A late driver forfeits the fee almost everywhere: Grab (ETA plus 3 minutes), Gojek (ETA plus 5 minutes), Bolt ..., DiDi ..., Lyft scheduled ...')",
     "C", "yes", "Other platforms' practice; Ryde publishes no such rule."),
    ("A driver not moving toward the pick-up point makes it waivable",
     "FAIRRYDE (no local source: the round 1 reviewer found it on Grab's page, but research note 02 does not carry it)",
     "D", "yes", "Unsourced in the KB, so FairRyde's until a source is added (open item, A3). With a source it would be C again."),
    ("'Assignment ETA' for an advance booking", "not defined", "n/a", "no", "Wording gap (FX9), not changed in A3."),
    ("Parameter DRIVER_LATE_GRACE_S", "reference_data.yaml (C)", "C", "no", "Rated separately (sensitivity test)."),
])

rule("FC-F01", "B", "B", [
    ("RydeTAXI fares are METERED",
     "RYDE-30741244296217 (rider article, edited 2025-07-17): 'Fares quoted for our services are generally fixed, except for RydeTAXI.'",
     "B", "yes", "Older than 12 months and one side of the META-04 fare-basis conflict."),
    ("Every other service is FIXED_AT_BOOKING",
     "RYDE-30741244296217 (same); RYDE-360004075214 (RydeX article, edited 2024-10-08): 'All fares are fixed at the time of booking but does not include toll charges such as ERP.'",
     "B", "yes", "Same conflict; driver pages describe earnings by distance and time (META-04)."),
    ("RECALCULATED when a destination edit was accepted",
     "RYDE-50798691815449 (rider article, edited 2025-10-09): 'Once the driver accepts, your trip fare will be recalculated, and your route will be updated to the new destination'; RYDE-51399796192921 (2025-10-10): 'If the driver accepts your edit destination request, a $3.00 add/edit destination fee will apply.'",
     "A", "yes", "A3 adds the recalculation quote (the cited fee article does not say the fare is recalculated)."),
])

rule("FC-F03", "C", "D", [
    ("Congestion, an incident or a closure on the recommended route justifies a deviation",
     "LTA-PDVL-OFFENCES (PDVL offense list as at 1 Apr 2023): 'Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct route'",
     "B", "yes", "Reading congestion and closures as 'reasonable cause' interprets the regulation (B), verified for PDVL drivers only."),
    ("... for every driver (FairRyde does not check whether a taxi driver on RydeX or a carpool driver without a PDVL served the trip)",
     "FAIRRYDE (open item D35, item 3)", "D", "yes", "The PDVL duty extended to other drivers."),
    ("A route the rider agreed with the driver before the trip",
     "RYDE-4412121982745 (rider article, edited 2024-10-01): 'If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you go.'",
     "B", "yes", ""),
    ("... or requested or agreed during the trip before the deviation, including avoiding ERP at the rider's request",
     "FAIRRYDE (Ryde's text covers agreement 'before you go')", "D", "yes", "Check round 1 (SG-6): extends the agreement before the trip to requests during it."),
    ("The route the driver's GPS navigation showed as the fastest or most efficient, for a fixed fare",
     "RYDE-4412121982745: 'hence the driver may decide to take the most efficient route according to GPS.'; RYDE-4412122016153 (driver article, 2023-06-16): 'So you may decide to take the fastest or most efficient route based on your GPS.'",
     "B", "yes", "Both articles give the permission because 'The trip fare is fixed based on pick-up and drop-off points'."),
    ("... applied to ERP claims (FC-R08) and to fares that are not fixed (FC-R03)", "FAIRRYDE (open item D35, item 4)", "D", "yes",
     "Extends a permission Ryde states for a fixed fare to situations where the route changes the amount."),
    ("The GPS justification needs the trip's navigation record; a driver's bare statement does not establish it", "FAIRRYDE (open item D36)", "D", "yes", "FairRyde's evidence rule."),
    ("An in-app navigation reroute justifies a deviation",
     "IND-DIDI-DETOUR: '司机采用 App 导航，导致的乘客投诉绕路，视为司机履约，不承担违约责任'", "C", "yes", "Other platform's terms."),
])

rule("FC-R01", "B", "B", [
    ("A FIXED_AT_BOOKING fare charged as quoted: the longer route did not change what the rider paid for the trip, so no fare refund",
     "RYDE-4412121982745 (2024-10-01): 'The trip fare is fixed based on pick-up and drop-off points, hence the driver may decide to take the most efficient route according to GPS.'; RYDE-30741244296217 (2025-07-17, META-04 side)",
     "B", "yes", ""),
    ("A fixed fare excludes ERP (except RydeSEND), so ERP the longer route caused is a separate charge that FC-R01 never decides",
     "RYDE-360004075214 (2024-10-08): 'All fares are fixed at the time of booking but does not include toll charges such as ERP.'; RYDE-115000772653 (2024-04-19): 'For all services apart from RydeSEND, ERP charges are excluded from the fares.'",
     "B", "yes", ""),
    ("The deviation is recorded as driver-conduct information only", "FAIRRYDE (round 1 finding: no source or label)", "D", "no",
     "Records information and decides nothing; A3 labels it in the FAIRRYDE source note."),
    ("The ERP of a longer route is opened as its own FC-TOLL claim without the rider naming it, only for a fixed fare charged as quoted",
     "FAIRRYDE (open item D35, item 2; kept by Jasper on 2026-10-14)", "D", "no",
     "A classification step (CLS-02 secondary claim) that sets no amount; the claim is decided by FC-R08 (D). Not a condition of the no-refund norm."),
])

rule("FC-R02", "B", "D", [
    ("The driver may take the most efficient route according to GPS, for a fixed fare",
     "RYDE-4412122016153 (driver article, 2023-06-16): 'So you may decide to take the fastest or most efficient route based on your GPS.'; RYDE-4412121982745 (rider article, 2024-10-01)",
     "B", "yes", "Both give the reason 'The trip fare is fixed based on pick-up and drop-off points'."),
    ("... on every fare of a route claim (applies_to FC-ROUTE), including RECALCULATED and METERED fares",
     "FAIRRYDE (extension)", "D", "yes",
     "On a fixed fare FC-R01 already decides the claim, so FC-R02 matters where the fare is not fixed: there it extends Ryde's permission."),
    ("A rider's preferred route binds only if agreed before the trip",
     "RYDE-4412121982745: 'If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you go.'",
     "B", "yes", ""),
])

rule("FC-R03", "C", "D", [
    ("The driver must take the shortest and most direct route without reasonable cause",
     "LTA-PDVL-OFFENCES (PDVL offense list as at 1 Apr 2023): 'Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct route'",
     "B", "yes", "Verified for private-hire (PDVL) drivers only; the taxi (TDVL) list was not found."),
    ("... applied to every driver of a RECALCULATED fare without checking the license", "FAIRRYDE (open item D35, item 3)", "D", "yes",
     "A RydeX trip may be served by a taxi driver and a carpool driver may not hold a PDVL."),
    ("A detour is DR at least DETOUR_RATIO_MIN with extra distance at least DETOUR_EXTRA_KM_MIN",
     "IND-DIDI-DETOUR: '实际行驶里程÷腾讯地图里程 ≥120% 且 绕路里程≥3 公里，则判定为绕路'", "C", "yes", "Other platform's published values; the parameters themselves are C."),
    ("Spatial confirmation (FC-F02) and no justification (FC-F03)", "FC-F02 (D), FC-F03 (D)", "D", "no",
     "Inputs from other rules on the path, which carry their own labels."),
    ("A confirmed detour is refunded per FC-R05", "FC-R05 (D; DiDi practice, research note 02)", "D", "no", "Pointer to the remedy rule, which carries its own label."),
])

rule("SE-R02", "B", "B", [
    ("A driver may end a ride in progress for a safety concern or a guideline violation",
     "RYDE-16925196526489 (rider article, edited 2023-04-26): 'The driver may terminate a ride in progress if there is a safety concern or if the rider is violating the community guidelines set by the platform.'",
     "B", "yes", ""),
    ("Examples: abuse, intoxication, illegal activity, unsafe use of the vehicle",
     "RYDE-16925196526489: 'This could include situations where the rider is verbally or physically abusive towards the driver, is intoxicated or engaging in illegal activities, or is not following the driver's instructions for safe and proper use of the vehicle.'",
     "B", "yes", "Quote added in A3."),
    ("... or a breakdown or malfunction that leaves the driver unable to continue the ride safely",
     "RYDE-16925196526489: 'Additionally, a driver may also terminate a ride in progress if their vehicle breaks down or malfunctions, and they are unable to safely continue the ride.'",
     "B", "yes", "Quote added in A3; the statement carries the article's condition since check round 1 (SG-5)."),
])

rule("SE-R04", "B", "B", [
    ("Drivers report accidents through RydeHELP within 1 hour",
     "RYDE-900003838386 (driver article, edited 2023-09-19): 'Report to us swiftly via RydeHelp within 1 hour.'", "B", "yes", ""),
    ("... and make a traffic accident report within 24 hours where the article requires one",
     "RYDE-900003838386: 'Make a traffic accident report within 24 hours when an accident involves injury, death, pedestrian, cyclist, government or foreign vehicles and government property.'",
     "B", "yes", "Quote added in A3; the statement said 'police report', now the article's 'traffic accident report'."),
    ("FairRyde routes accident cases to a human", "AUTH-03 (B)", "B", "yes", "Accidents are safety matters (AUTH-03)."),
])

rule("GEN-R06", "B", "B", [
    ("FairRyde never suspends, holds or deactivates an account",
     "RYDE-TOU Section A s.28: 'modify, suspend or terminate operation of or access to the Platform, or any portion of the Platform (including access to your account and/or the availability of any products or services), for any reason' (A: the power is Ryde's); GOV-IMDA-AGENTIC (B)",
     "B", "yes", "Round 1 reviewer: PASS, B right."),
    ("It may only recommend a human review",
     "GOV-IMDA-AGENTIC: 'Organisations should define significant checkpoints or action boundaries that require human approval, especially before sensitive actions are executed.'",
     "B", "yes", ""),
])

rule("AUTH-03", "B", "B", [
    ("Safety matters and possible criminal conduct are decided by a human",
     "GOV-IMDA-AGENTIC (human approval before sensitive actions); RYDE-15395890865561 (2026-04-10): 'Violations of these guidelines will result in immediate termination and legal action where applicable.'",
     "B", "yes", "Reading safety and crime as sensitive actions applies the guidance (B); deciding rather than approving is stricter and only sends more to people."),
    ("Any account sanction is decided by a human", "RYDE-15395890865561; RYDE-TOU s.28 (via GEN-R06)", "B", "yes", "Sanctions are Ryde's."),
    ("FairRyde only triages", "GOV-IMDA-AGENTIC", "B", "yes", ""),
])

rule("EXP-01", "B", "D", [
    ("Each party receives the outcome, the rules used with source and credibility, and how to ask for a human review",
     "GOV-MGF2 (Model AI Governance Framework, 2nd ed., paras 3.48, 3.51, 3.54); PDPC AI guidelines para 9.5 (research note 07)",
     "B", "yes", "Official guidance on explanations and review requests."),
    ("Marking which rules decided the outcome", "FAIRRYDE", "D", "yes", "Round 1 finding: no source or label."),
    ("Two to four decisive evidence items", "FAIRRYDE", "D", "yes", ""),
    ("What evidence was missing", "FAIRRYDE", "D", "yes", ""),
    ("Whether history was used", "FAIRRYDE (with GEN-R03)", "D", "yes", ""),
    ("Ryde's 30-day limit applies to waiver requests, not to reviews of a FairRyde ruling, so it is not presented as an appeal deadline",
     "FAIRRYDE (reading of MAT-04's window)", "D", "yes", ""),
])

rule("FC-R07", "A", "D", [
    ("An ERP line above the rider's share (FC-R06, computed by FC-F04) is an overstatement",
     "RYDE-115001438614 (driver article, edited 2026-09-02): 'Please key in ERP based on the ERP gantry you passed during the journey.' and the share quotes",
     "A", "yes", "The key-in quote was added to FC-R07's card in check round 1 (SG-10)."),
    ("It raises FRAUD_SIGNAL against the driver; the consequence is for a human",
     "RYDE-115001438614: 'Please bear in mind that if an additional/excessive amount is keyed in, this will be considered fraudulent and drivers will be liable for permanent suspension.'",
     "A", "yes", ""),
    ("The difference is refunded", "FAIRRYDE (Ryde's text only calls the excess fraudulent; open item D35, item 5)", "D", "yes",
     "Jasper decided on 2026-10-14 that FC-R07 is rated D (A2 had left it at A)."),
    ("On a carpool trip the ERP line holds what the rider was charged", "FAIRRYDE (organizer question O15)", "D", "yes", "Named in FC-R07's FAIRRYDE source note since check round 1 (SG-10)."),
    ("Parameter TOLL_TOLERANCE_SGD", "reference_data.yaml (D)", "D", "no", "Rated separately (sensitivity test)."),
])

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    w.writerows(R)
print(len(R), "rows,", len({r['rule'] for r in R}), "rules")
