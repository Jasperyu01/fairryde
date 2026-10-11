# DISP-002 evaluated with the knowledge base

Reference evaluation without an LLM: the run-agreement (A) and rules-engine agreement (R) terms of the confidence score are set to 1.0.

## Profile organizer_case

| playbook | step | rule | status | result | evidence |
|---|---|---|---|---|---|
| PB-INTAKE | 1 | GEN-R04 | done | no instructions found in party text | E-TKT-01, E-CHT-01, E-CHT-02, E-CHT-04, E-CHT-05 |
| PB-INTAKE | 2 | CLS-01 | done | no safety language | E-TKT-01 |
| PB-INTAKE | 3 | CLS-05, CLS-02, CLS-04 | done | dispute_type 'no_show_charge' -> CW-NOSHOW; one claim contesting CANCELLATION_FEE S$5.00 | E-TKT-01, E-TRP-01.cancellation_fee |
| PB-INTAKE | 4 | CLS-03 | done | contested charge present: not routed to support | E-TRP-01.cancellation_fee |
| PB-INTAKE | 5 | MAT-01 | done | trip TRIP-2026-09945 matches the ticket | E-TKT-01.trip_id, E-TRP-01.trip_id |
| PB-INTAKE | 6 | MAT-02 | missing | no ticket index in the case file; treated as NEW (at run time the ticket index is checked) | E-TKT-01 |
| PB-INTAKE | 7 | MAT-03 | not_applicable | not an appeal | E-TKT-01.status |
| PB-INTAKE | 8 | META-01, META-02 | done | profile organizer_case (the case embeds cancellation_policy; parameters read from it: FREE_WAIT_S=300, NO_SHOW_FEE_SGD=5.0, NO_SHOW_THRESHOLD_S=480, FEE_PAYEE=DRIVER); effective from case-specific: in force | E-POL-01 |
| PB-INTAKE | 9 | DQ-03, DQ-04 | done | coordinates in Singapore: True; timeline ordered and filed after the trip: True | E-TRP-01, E-GPS-* |
| PB-CW-NOSHOW | 1 | CLS-02, CW-R03 | done | driver canceled with reason rider_no_show | E-TRP-01.cancellation_reason, E-CHT-06 |
| PB-CW-NOSHOW | 2 | MAT-04 | done | filed 0.02 days after the trip (window 30 days: inside) | E-TKT-01.filed_at, E-TRP-01.cancellation_time |
| PB-CW-NOSHOW | 3 | CW-R00 | missing | service type not recorded; treated as in scope (the policy covers every service except RydeTAXI) | E-TRP-01 |
| PB-CW-NOSHOW | 4 | CW-F01 | done | ON_DEMAND (inferred: matched 15 s after booking, ETA lands 105 s from scheduled_time) | E-APP-01, E-APP-02, E-TRP-01.scheduled_time |
| PB-CW-NOSHOW | 5 | CW-F02 | done | wait anchor 08:43:00 (trip_data.driver_wait_start) | E-TRP-01.driver_wait_start |
| PB-CW-NOSHOW | 6 | DQ-01, DQ-02 | done | spread of the arrival records 0 s, of the wait start 10 s, of the end 0 s (tolerance 30 s): consistent; speed in the wait window: 0 soft, 0 hard | E-TRP-01, E-APP-*, E-GPS-* |
| PB-CW-NOSHOW | 7 | CW-R06 | done | TRUE: platform GPS arrival check | E-APP-04, E-GPS-05 |
| PB-CW-NOSHOW | 8 | CW-F03, CW-F03B | done | wait counted from 08:43:00; elapsed 480 s; threshold 480 s (at_least); margin +0 s: met; the records of the start or end differ by up to 10 s, more than the margin | E-TRP-01.driver_wait_start, E-TRP-01.cancellation_time |
| PB-CW-NOSHOW | 9 | CW-F04 | done | CONSISTENT: window 08:43:00 to 08:51:00, 4 ping(s), max distance 0.0 m (area 50 m); longest stretch without presence evidence 180 s (limit 300 s) | E-GPS-05, E-GPS-06, E-GPS-07, E-GPS-08 |
| PB-CW-NOSHOW | 10 | CW-F05 | done | ADEQUATE: driver 1 call(s) and 4 message(s), rider 0 contact(s) | E-CHT-01, E-CHT-02, E-CHT-03, E-CHT-04, E-CHT-05 |
| PB-CW-NOSHOW | 11 | CW-F06 | done | WEAK: the statement contests presence or place, but there are no rider-side records (no rider GPS, call, message or notification failure) | E-TKT-01, E-APP-05 |
| PB-CW-NOSHOW | 12 | CW-F07 | done | pin is 1,259 m from the OneMap address of Tiong Bahru Plaza (limit 200 m): mismatch = True | E-TRP-01.pickup_location, E-GEO-01 |
| PB-CW-NOSHOW | 13 | GEN-R05 | missing | advocate briefs are produced at run time by the Rider and Driver Advocates; not simulated in this offline check |  |
| PB-CW-NOSHOW | 14 | DT-CW-NOSHOW | done | row R8 (credibility B): UPHOLD (CW-R-NOSHOW-VALID) | F-ARRIVAL-VALID, F-PRESENCE, F-WAIT-MARGIN, F-RIDER-EVIDENCE |
| PB-CW-NOSHOW | 15 | CW-R11, CW-R04, DQ-06 | done | pin mismatch True, and the rider says they were at Tiong Bahru Plaza; contact ADEQUATE; charged S$5.00 vs policy S$5.00: equal | F-PIN-VENUE, F-CONTACT, F-CHARGE-AMOUNT |
| PB-CW-NOSHOW | 16 | CW-R09, CW-R10 | done | fee payee DRIVER; remedy {'amount_sgd': 0.0, 'payer': None, 'payee': None, 'form': 'NONE', 'fee_stands_sgd': 5.0, 'fee_payee': 'DRIVER'} | E-POL-01 |
| PB-CW-NOSHOW | 17 | FRD-01, FRD-02, GEN-R03, GEN-R06 | done | signals: RIDER (FRD-02: 3 of 4 past disputes rejected; platform flag: flagged_for_frequent_late_cancellations); for the reviewer only; history never enters the outcome; no account action | E-PRF-R, E-PRF-D |
| PB-CW-NOSHOW | 18 | AUTH-05 | done | C = 0.689 (A 1.0, M 0.00, E 0.76, R 1.0; soft flags ['PIN_VENUE_MISMATCH']) | F-WAIT-MARGIN, F-PRESENCE |
| PB-CW-NOSHOW | 19 | AUTH-01 to AUTH-04, AUTH-06 | done | tier APPROVE; 4 approval trigger(s) | F-WAIT-MARGIN, F-PRESENCE, F-RIDER-EVIDENCE, F-PIN-VENUE |
| PB-CW-NOSHOW | 20 | EXP-01 to EXP-03, META-05 | done | explanations drafted from findings only (see the explanation drafts) | F-* |

Findings:

| finding | value | unit | status | rule | basis | parameters |
|---|---|---|---|---|---|---|
| F-FILING-WINDOW | 0.02 | days | established | MAT-04 | E-TKT-01.filed_at, E-TRP-01.cancellation_time | WAIVER_WINDOW_DAYS |
| F-BOOKING-TYPE | ON_DEMAND |  | inferred | CW-F01 | E-APP-01, E-APP-02, E-TRP-01.scheduled_time | BOOKING_INFER_MATCH_S, BOOKING_INFER_ETA_S |
| F-WAIT-ANCHOR | 2026-09-13T08:43:00+08:00 |  | established | CW-F02 | E-TRP-01.driver_wait_start | WAIT_ANCHOR_FIELD |
| F-TS-CONSISTENCY | {'arrival': 0, 'start': 10, 'end': 0} | s | established | DQ-01 | E-TRP-01, E-APP-*, E-GPS-*, E-CHT-* | TS_TOLERANCE_S |
| F-ARRIVAL-VALID | TRUE |  | established | CW-R06 | E-APP-04, E-GPS-05 | ARRIVAL_GEOFENCE_M, TS_TOLERANCE_S, PING_MAX_GAP_S, LEFT_MIN_OUTSIDE_S, SPEED_MAX_KMH |
| F-WAIT-ELAPSED | 480.0 | s | established | CW-F03 | E-TRP-01.driver_wait_start, E-TRP-01.cancellation_time |  |
| F-WAIT-MARGIN | 0.0 | s | established | CW-F03 | E-TRP-01.driver_wait_start, E-TRP-01.cancellation_time | NO_SHOW_THRESHOLD_S, THRESHOLD_COMPARISON, BOUNDARY_BAND_S |
| F-PRESENCE | CONSISTENT |  | established | CW-F04 | E-GPS-05, E-GPS-06, E-GPS-07, E-GPS-08 | ARRIVAL_GEOFENCE_M, PING_MAX_GAP_S, LEFT_MIN_OUTSIDE_S, SPEED_MAX_KMH, TS_TOLERANCE_S |
| F-SPEED-CONSISTENCY | {'soft_segments': 0, 'hard_segments': 0, 'data_error_stretches': 0, 'window': 'wait'} |  | established | DQ-02 | E-GPS-* | SPEED_RATIO_SOFT, SPEED_MAX_KMH |
| F-CONTACT | ADEQUATE |  | established | CW-F05 | E-CHT-01, E-CHT-02, E-CHT-03, E-CHT-04, E-CHT-05 | CONTACT_MIN_CALLS, CONTACT_MIN_MESSAGES |
| F-RIDER-EVIDENCE | WEAK |  | read | CW-F06 | E-TKT-01 | ARRIVAL_GEOFENCE_M, PIN_VENUE_MAX_M |
| F-PIN-VENUE | 1259 | m | established | CW-F07 | E-TRP-01.pickup_location, E-GEO-01 | PIN_VENUE_MAX_M |
| F-CHARGE-AMOUNT | {'charged': 5.0, 'policy': 5.0, 'status': 'equal'} | SGD | established | DQ-06 | E-TRP-01.cancellation_fee, E-POL-01 | NO_SHOW_FEE_SGD, MONEY_TOLERANCE_SGD |

Outcome **UPHOLD** via R8; reasons ['CW-R-NOSHOW-VALID', 'CW-R-PIN-AMBIGUOUS']; remedy {'amount_sgd': 0.0, 'payer': None, 'payee': None, 'form': 'NONE', 'fee_stands_sgd': 5.0, 'fee_payee': 'DRIVER'}; flags ['BOOKING_TYPE_INFERRED', 'BOUNDARY_MARGIN', 'MARGIN_WITHIN_SPREAD', 'NO_RIDER_EVIDENCE', 'PIN_VENUE_MISMATCH', 'FRAUD_SIGNAL', 'GENERIC_ASSUMPTION_USED']

Sensitivity test (decisive definition, clause 2):

| parameter | value | plausible range | credibility | at low end | at high end | decisive | path rules using it |
|---|---|---|---|---|---|---|---|
| BOOKING_INFER_MATCH_S | 60 | [30, 120] | D | 30 -> UPHOLD (R8) | 120 -> UPHOLD (R8) | no |  |
| BOOKING_INFER_ETA_S | 120 | [60, 300] | D | 60 -> UPHOLD (R8) | 300 -> UPHOLD (R8) | no |  |
| TS_TOLERANCE_S | 30 | [5, 60] | D | 5 -> UPHOLD (R8) | 60 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| ARRIVAL_GEOFENCE_M | 50 | [10, 100] | D | 10 -> UPHOLD (R8) | 100 -> UPHOLD (R8) | no | CW-R06, CW-F04, CW-F06 |
| PING_MAX_GAP_S | 300 | [60, 420] | D | 60 -> ESCALATE_HUMAN (R10) | 420 -> UPHOLD (R8) | yes (outcome changes) | CW-F04 |
| LEFT_MIN_OUTSIDE_S | 60 | [30, 120] | D | 30 -> UPHOLD (R8) | 120 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| SPEED_MAX_KMH | 120 | [100, 150] | D | 100 -> UPHOLD (R8) | 150 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| CONTACT_MIN_CALLS | 1 | [1, 2] | D | 1 -> UPHOLD (R8) | 2 -> UPHOLD (R8) | no |  |
| CONTACT_MIN_MESSAGES | 2 | [1, 3] | D | 1 -> UPHOLD (R8) | 3 -> UPHOLD (R8) | no |  |
| PIN_VENUE_MAX_M | 200 | [100, 500] | D | 100 -> UPHOLD (R8) | 500 -> UPHOLD (R8) | no | CW-F06 |
| MONEY_TOLERANCE_SGD | 0.01 | [0.0, 0.05] | D | 0.0 -> UPHOLD (R8) | 0.05 -> UPHOLD (R8) | no |  |
| RIDER_ABUSE_MIN_DISPUTES | 3 | [2, 5] | D | 2 -> UPHOLD (R8) | 5 -> UPHOLD (R8) | no |  |
| RIDER_ABUSE_REJECT_SHARE_MIN | 0.5 | [0.4, 0.8] | D | 0.4 -> UPHOLD (R8) | 0.8 -> UPHOLD (R8) | no |  |

Reading test (decisive definition, clause 1):

| rule | reading | other reading | outcome under the other reading | changes |
|---|---|---|---|---|
| CW-F06 | WEAK | NONE | UPHOLD | False |

Confidence {'A': 1.0, 'M': 0.0, 'E': 0.757, 'R': 1.0, 'C': 0.689, 'assumed': ['A = 1.0 (no LLM runs in this check)', 'R = 1.0 (no LLM Judge in this check)'], 'soft_flags': ['PIN_VENUE_MISMATCH'], 'evidence_present': {'E-TKT-01': True, 'E-TRP-01': True, 'E-APP-* (driver_assigned, driver_arrived, wait_timer_started, cancellation_fee_applied)': True, 'E-GPS-* during the wait': True, 'E-CHT-* (calls and messages)': True, 'E-POL-01 (policy object or profile)': True, 'rider-side records (required because the rider contests presence)': False}}

Tier **APPROVE**; decisive [('CW-F04', 'outcome changes when PING_MAX_GAP_S moves within [60, 420]')]; triggers ['decisive: CW-F04 (outcome changes when PING_MAX_GAP_S moves within [60, 420])', 'fraud signal on RIDER (3 of 4 past disputes rejected; platform flag: flagged_for_frequent_late_cancellations) (symmetric trigger; the detail is for the reviewer, not for the parties)', 'margin +0 s within the boundary band, and the records disagree by up to 10 s', 'fee upheld, pin far from Tiong Bahru Plaza and the rider says they were there']; gates []; runtime-only gates not evaluated here: ['G2 rule conflict', 'G3 history-aware vs history-blind Judge', 'G7 citation and number verification', 'G8 Judge runs vs rules engine']

Explanation drafts (EXP-01 to EXP-03):

* Rider: Outcome: the S$5.00 cancellation fee stands. It goes to the driver, as compensation for the wait (CW-R09). This is a provisional decision; a Ryde staff member checks it before it takes effect. GPS confirms the driver's arrival at the pick-up pin (E-APP-04, E-GPS-05). Every driver GPS point from 08:43:00 to 08:51:00 is at the pick-up pin, and the longest stretch without a point at the pin is 180 seconds (E-GPS-05 to E-GPS-08). The wait lasted 480 seconds, from 08:43:00 to 08:51:00; the policy for this trip requires at least 480 seconds (E-TRP-01). The wait reached the limit exactly, and the records of the start or end of the wait differ by up to 10 seconds (the app's wait timer started at 08:43:10). The driver called 1 time and sent 4 messages during the wait (E-CHT-01 to E-CHT-05). Rules that decided the outcome: CW-R03 No-show cancellation fee is valid (the policy attached to this trip; credibility A); CW-R06 Arrival counts only if GPS shows the driver at the pick-up point (Ryde policy; credibility B); CW-F04 Driver presence at the pick-up point (Ryde policy; credibility B; decisive for the approval step). Also used: MAT-04 Rider waiver filing window (Ryde policy; credibility A); CW-R00 Cancellation policy scope (Ryde policy; credibility B); CW-F02 Wait anchor (organizer cases and on-demand trips) (the policy attached to this trip; credibility A); CW-F03 Elapsed wait and margin (the policy attached to this trip; credibility A); CW-F06 Rider counter-evidence strength (FairRyde assumption; credibility D); CW-R11 Pin and venue mismatch (FairRyde assumption; credibility D). There is no GPS trace from your phone and no call or message from you in the trip record. The pick-up pin is about 1,259 m from the address of Tiong Bahru Plaza; if you waited at the venue entrance you may not have been at the pin. Account history was used only to decide whether a person reviews this case; it did not affect the outcome. Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: the longest allowed gap between driver GPS points (300 seconds), used by CW-F04. If you disagree, you can ask for a human review through RydeHELP.
* Driver: Outcome: the S$5.00 cancellation fee stands. It goes to the driver, as compensation for the wait (CW-R09). This is a provisional decision; a Ryde staff member checks it before it takes effect. GPS confirms the driver's arrival at the pick-up pin (E-APP-04, E-GPS-05). Every driver GPS point from 08:43:00 to 08:51:00 is at the pick-up pin, and the longest stretch without a point at the pin is 180 seconds (E-GPS-05 to E-GPS-08). The wait lasted 480 seconds, from 08:43:00 to 08:51:00; the policy for this trip requires at least 480 seconds (E-TRP-01). The wait reached the limit exactly, and the records of the start or end of the wait differ by up to 10 seconds (the app's wait timer started at 08:43:10). The driver called 1 time and sent 4 messages during the wait (E-CHT-01 to E-CHT-05). Rules that decided the outcome: CW-R03 No-show cancellation fee is valid (the policy attached to this trip; credibility A); CW-R06 Arrival counts only if GPS shows the driver at the pick-up point (Ryde policy; credibility B); CW-F04 Driver presence at the pick-up point (Ryde policy; credibility B; decisive for the approval step). Also used: MAT-04 Rider waiver filing window (Ryde policy; credibility A); CW-R00 Cancellation policy scope (Ryde policy; credibility B); CW-F02 Wait anchor (organizer cases and on-demand trips) (the policy attached to this trip; credibility A); CW-F03 Elapsed wait and margin (the policy attached to this trip; credibility A); CW-F06 Rider counter-evidence strength (FairRyde assumption; credibility D); CW-R11 Pin and venue mismatch (FairRyde assumption; credibility D). The pick-up pin is about 1,259 m from the address of Tiong Bahru Plaza, which was noted. Account history was used only to decide whether a person reviews this case; it did not affect the outcome. Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: the longest allowed gap between driver GPS points (300 seconds), used by CW-F04. If you disagree, you can ask for a human review through RydeHELP.
* Numbers registered: {'amount': 'S$5.00', 'anchor': '08:43:00', 'start': '08:43:00', 'window_end': '08:51:00', 'end': '08:51:00', 'elapsed_s': '480', 'threshold_s': '480', 'driver_calls': '1', 'driver_messages': '4', 'pin_venue_m': '1,259', 'max_gap_s': '180', 'margin_s': '0', 'spread_s': '10', 'timer': '08:43:10', 'param_PING_MAX_GAP_S': '300'}; unmatched numbers: none

## Profile ryde_2026

| playbook | step | rule | status | result | evidence |
|---|---|---|---|---|---|
| PB-INTAKE | 1 | GEN-R04 | done | no instructions found in party text | E-TKT-01, E-CHT-01, E-CHT-02, E-CHT-04, E-CHT-05 |
| PB-INTAKE | 2 | CLS-01 | done | no safety language | E-TKT-01 |
| PB-INTAKE | 3 | CLS-05, CLS-02, CLS-04 | done | dispute_type 'no_show_charge' -> CW-NOSHOW; one claim contesting CANCELLATION_FEE S$5.00 | E-TKT-01, E-TRP-01.cancellation_fee |
| PB-INTAKE | 4 | CLS-03 | done | contested charge present: not routed to support | E-TRP-01.cancellation_fee |
| PB-INTAKE | 5 | MAT-01 | done | trip TRIP-2026-09945 matches the ticket | E-TKT-01.trip_id, E-TRP-01.trip_id |
| PB-INTAKE | 6 | MAT-02 | missing | no ticket index in the case file; treated as NEW (at run time the ticket index is checked) | E-TKT-01 |
| PB-INTAKE | 7 | MAT-03 | not_applicable | not an appeal | E-TKT-01.status |
| PB-INTAKE | 8 | META-01, META-02 | done | profile ryde_2026 (forced for a what-if; META-01 would choose organizer_case because the case embeds a policy object); effective from 2026-02-17: in force | E-POL-01 |
| PB-INTAKE | 9 | DQ-03, DQ-04 | done | coordinates in Singapore: True; timeline ordered and filed after the trip: True | E-TRP-01, E-GPS-* |
| PB-CW-NOSHOW | 1 | CLS-02, CW-R03 | done | driver canceled with reason rider_no_show | E-TRP-01.cancellation_reason, E-CHT-06 |
| PB-CW-NOSHOW | 2 | MAT-04 | done | filed 0.02 days after the trip (window 30 days: inside) | E-TKT-01.filed_at, E-TRP-01.cancellation_time |
| PB-CW-NOSHOW | 3 | CW-R00 | missing | service type not recorded; treated as in scope (the policy covers every service except RydeTAXI) | E-TRP-01 |
| PB-CW-NOSHOW | 4 | CW-F01 | done | ON_DEMAND (inferred: matched 15 s after booking, ETA lands 105 s from scheduled_time) | E-APP-01, E-APP-02, E-TRP-01.scheduled_time |
| PB-CW-NOSHOW | 5 | CW-F02 | done | wait anchor 08:43:00 (ON_DEMAND) | E-APP-04 |
| PB-CW-NOSHOW | 6 | DQ-01, DQ-02 | done | spread of the arrival records 0 s, of the wait start 10 s, of the end 0 s (tolerance 30 s): consistent; speed in the wait window: 0 soft, 0 hard | E-TRP-01, E-APP-*, E-GPS-* |
| PB-CW-NOSHOW | 7 | CW-R06 | done | TRUE: platform GPS arrival check | E-APP-04, E-GPS-05 |
| PB-CW-NOSHOW | 8 | CW-F03, CW-F03B | done | wait counted from 08:43:00; elapsed 480 s; threshold 180 s (more_than); margin +300 s: met | E-APP-04, E-TRP-01.cancellation_time |
| PB-CW-NOSHOW | 9 | CW-F04 | done | CONSISTENT: window 08:43:00 to 08:46:00, 2 ping(s), max distance 0.0 m (area 50 m); longest stretch without presence evidence 120 s (limit 300 s) | E-GPS-05, E-GPS-06 |
| PB-CW-NOSHOW | 10 | CW-F05 | done | ADEQUATE: driver 1 call(s) and 4 message(s), rider 0 contact(s) | E-CHT-01, E-CHT-02, E-CHT-03, E-CHT-04, E-CHT-05 |
| PB-CW-NOSHOW | 11 | CW-F06 | done | WEAK: the statement contests presence or place, but there are no rider-side records (no rider GPS, call, message or notification failure) | E-TKT-01, E-APP-05 |
| PB-CW-NOSHOW | 12 | CW-F07 | done | pin is 1,259 m from the OneMap address of Tiong Bahru Plaza (limit 200 m): mismatch = True | E-TRP-01.pickup_location, E-GEO-01 |
| PB-CW-NOSHOW | 13 | GEN-R05 | missing | advocate briefs are produced at run time by the Rider and Driver Advocates; not simulated in this offline check |  |
| PB-CW-NOSHOW | 14 | DT-CW-NOSHOW | done | row R8 (credibility B): UPHOLD (CW-R-NOSHOW-VALID) | F-ARRIVAL-VALID, F-PRESENCE, F-WAIT-MARGIN, F-RIDER-EVIDENCE |
| PB-CW-NOSHOW | 15 | CW-R11, CW-R04, DQ-06 | done | pin mismatch True, and the rider says they were at Tiong Bahru Plaza; contact ADEQUATE; charged S$5.00 vs policy S$6.61: undercharged | F-PIN-VENUE, F-CONTACT, F-CHARGE-AMOUNT |
| PB-CW-NOSHOW | 16 | CW-R09, CW-R10 | done | fee payee DRIVER; remedy {'amount_sgd': 0.0, 'payer': None, 'payee': None, 'form': 'NONE', 'fee_stands_sgd': 5.0, 'fee_payee': 'DRIVER'} | E-POL-01 |
| PB-CW-NOSHOW | 17 | FRD-01, FRD-02, GEN-R03, GEN-R06 | done | signals: RIDER (FRD-02: 3 of 4 past disputes rejected; platform flag: flagged_for_frequent_late_cancellations); for the reviewer only; history never enters the outcome; no account action | E-PRF-R, E-PRF-D |
| PB-CW-NOSHOW | 18 | AUTH-05 | done | C = 0.939 (A 1.0, M 1.00, E 0.76, R 1.0; soft flags ['PIN_VENUE_MISMATCH']) | F-WAIT-MARGIN, F-PRESENCE |
| PB-CW-NOSHOW | 19 | AUTH-01 to AUTH-04, AUTH-06 | done | tier APPROVE; 3 approval trigger(s) | F-WAIT-MARGIN, F-PRESENCE, F-RIDER-EVIDENCE, F-PIN-VENUE |
| PB-CW-NOSHOW | 20 | EXP-01 to EXP-03, META-05 | done | explanations drafted from findings only (see the explanation drafts) | F-* |

Findings:

| finding | value | unit | status | rule | basis | parameters |
|---|---|---|---|---|---|---|
| F-FILING-WINDOW | 0.02 | days | established | MAT-04 | E-TKT-01.filed_at, E-TRP-01.cancellation_time | WAIVER_WINDOW_DAYS |
| F-BOOKING-TYPE | ON_DEMAND |  | inferred | CW-F01 | E-APP-01, E-APP-02, E-TRP-01.scheduled_time | BOOKING_INFER_MATCH_S, BOOKING_INFER_ETA_S |
| F-WAIT-ANCHOR | 2026-09-13T08:43:00+08:00 |  | established | CW-F02 | E-APP-04 | WAIT_ANCHOR_FIELD |
| F-TS-CONSISTENCY | {'arrival': 0, 'start': 10, 'end': 0} | s | established | DQ-01 | E-TRP-01, E-APP-*, E-GPS-*, E-CHT-* | TS_TOLERANCE_S |
| F-ARRIVAL-VALID | TRUE |  | established | CW-R06 | E-APP-04, E-GPS-05 | ARRIVAL_GEOFENCE_M, TS_TOLERANCE_S, PING_MAX_GAP_S, LEFT_MIN_OUTSIDE_S, SPEED_MAX_KMH |
| F-WAIT-ELAPSED | 480.0 | s | established | CW-F03 | E-APP-04, E-TRP-01.cancellation_time |  |
| F-WAIT-MARGIN | 300.0 | s | established | CW-F03 | E-APP-04, E-TRP-01.cancellation_time | NO_SHOW_THRESHOLD_S, THRESHOLD_COMPARISON, BOUNDARY_BAND_S |
| F-PRESENCE | CONSISTENT |  | established | CW-F04 | E-GPS-05, E-GPS-06 | ARRIVAL_GEOFENCE_M, PING_MAX_GAP_S, LEFT_MIN_OUTSIDE_S, SPEED_MAX_KMH, TS_TOLERANCE_S |
| F-SPEED-CONSISTENCY | {'soft_segments': 0, 'hard_segments': 0, 'data_error_stretches': 0, 'window': 'wait'} |  | established | DQ-02 | E-GPS-* | SPEED_RATIO_SOFT, SPEED_MAX_KMH |
| F-CONTACT | ADEQUATE |  | established | CW-F05 | E-CHT-01, E-CHT-02, E-CHT-03, E-CHT-04, E-CHT-05 | CONTACT_MIN_CALLS, CONTACT_MIN_MESSAGES |
| F-RIDER-EVIDENCE | WEAK |  | read | CW-F06 | E-TKT-01 | ARRIVAL_GEOFENCE_M, PIN_VENUE_MAX_M |
| F-PIN-VENUE | 1259 | m | established | CW-F07 | E-TRP-01.pickup_location, E-GEO-01 | PIN_VENUE_MAX_M |
| F-CHARGE-AMOUNT | {'charged': 5.0, 'policy': 6.61, 'status': 'undercharged'} | SGD | established | DQ-06 | E-TRP-01.cancellation_fee, E-POL-01 | NO_SHOW_FEE_SGD, MONEY_TOLERANCE_SGD |

Outcome **UPHOLD** via R8; reasons ['CW-R-NOSHOW-VALID', 'CW-R-PIN-AMBIGUOUS']; remedy {'amount_sgd': 0.0, 'payer': None, 'payee': None, 'form': 'NONE', 'fee_stands_sgd': 5.0, 'fee_payee': 'DRIVER'}; flags ['BOOKING_TYPE_INFERRED', 'NO_RIDER_EVIDENCE', 'PIN_VENUE_MISMATCH', 'CHARGE_AMOUNT_MISMATCH', 'FRAUD_SIGNAL', 'GENERIC_ASSUMPTION_USED']

Sensitivity test (decisive definition, clause 2):

| parameter | value | plausible range | credibility | at low end | at high end | decisive | path rules using it |
|---|---|---|---|---|---|---|---|
| BOOKING_INFER_MATCH_S | 60 | [30, 120] | D | 30 -> UPHOLD (R8) | 120 -> UPHOLD (R8) | no | CW-F01 |
| BOOKING_INFER_ETA_S | 120 | [60, 300] | D | 60 -> UPHOLD (R8) | 300 -> UPHOLD (R8) | no | CW-F01 |
| TS_TOLERANCE_S | 30 | [5, 60] | D | 5 -> UPHOLD (R8) | 60 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| ARRIVAL_GEOFENCE_M | 50 | [10, 100] | D | 10 -> UPHOLD (R8) | 100 -> UPHOLD (R8) | no | CW-R06, CW-F04, CW-F06 |
| PING_MAX_GAP_S | 300 | [60, 420] | D | 60 -> ESCALATE_HUMAN (R10) | 420 -> UPHOLD (R8) | yes (outcome changes) | CW-F04 |
| LEFT_MIN_OUTSIDE_S | 60 | [30, 120] | D | 30 -> UPHOLD (R8) | 120 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| SPEED_MAX_KMH | 120 | [100, 150] | D | 100 -> UPHOLD (R8) | 150 -> UPHOLD (R8) | no | CW-R06, CW-F04 |
| CONTACT_MIN_CALLS | 1 | [1, 2] | D | 1 -> UPHOLD (R8) | 2 -> UPHOLD (R8) | no |  |
| CONTACT_MIN_MESSAGES | 2 | [1, 3] | D | 1 -> UPHOLD (R8) | 3 -> UPHOLD (R8) | no |  |
| PIN_VENUE_MAX_M | 200 | [100, 500] | D | 100 -> UPHOLD (R8) | 500 -> UPHOLD (R8) | no | CW-F06 |
| MONEY_TOLERANCE_SGD | 0.01 | [0.0, 0.05] | D | 0.0 -> UPHOLD (R8) | 0.05 -> UPHOLD (R8) | no |  |
| RIDER_ABUSE_MIN_DISPUTES | 3 | [2, 5] | D | 2 -> UPHOLD (R8) | 5 -> UPHOLD (R8) | no |  |
| RIDER_ABUSE_REJECT_SHARE_MIN | 0.5 | [0.4, 0.8] | D | 0.4 -> UPHOLD (R8) | 0.8 -> UPHOLD (R8) | no |  |

Reading test (decisive definition, clause 1):

| rule | reading | other reading | outcome under the other reading | changes |
|---|---|---|---|---|
| CW-F06 | WEAK | NONE | UPHOLD | False |

Confidence {'A': 1.0, 'M': 1.0, 'E': 0.757, 'R': 1.0, 'C': 0.939, 'assumed': ['A = 1.0 (no LLM runs in this check)', 'R = 1.0 (no LLM Judge in this check)'], 'soft_flags': ['PIN_VENUE_MISMATCH'], 'evidence_present': {'E-TKT-01': True, 'E-TRP-01': True, 'E-APP-* (driver_assigned, driver_arrived, wait_timer_started, cancellation_fee_applied)': True, 'E-GPS-* during the wait': True, 'E-CHT-* (calls and messages)': True, 'E-POL-01 (policy object or profile)': True, 'rider-side records (required because the rider contests presence)': False}}

Tier **APPROVE**; decisive [('CW-F04', 'outcome changes when PING_MAX_GAP_S moves within [60, 420]')]; triggers ['decisive: CW-F04 (outcome changes when PING_MAX_GAP_S moves within [60, 420])', 'fraud signal on RIDER (3 of 4 past disputes rejected; platform flag: flagged_for_frequent_late_cancellations) (symmetric trigger; the detail is for the reviewer, not for the parties)', 'fee upheld, pin far from Tiong Bahru Plaza and the rider says they were there']; gates []; runtime-only gates not evaluated here: ['G2 rule conflict', 'G3 history-aware vs history-blind Judge', 'G7 citation and number verification', 'G8 Judge runs vs rules engine']

Explanation drafts (EXP-01 to EXP-03):

* Rider: Outcome: the S$5.00 cancellation fee stands. It goes to the driver, as compensation for the wait (CW-R09). This is a provisional decision; a Ryde staff member checks it before it takes effect. GPS confirms the driver's arrival at the pick-up pin (E-APP-04, E-GPS-05). Every driver GPS point from 08:43:00 to 08:46:00 is at the pick-up pin, and the longest stretch without a point at the pin is 120 seconds (E-GPS-05, E-GPS-06). The wait lasted 480 seconds, from 08:43:00 to 08:51:00; the policy for this trip requires more than 180 seconds (E-TRP-01). The driver called 1 time and sent 4 messages during the wait (E-CHT-01 to E-CHT-05). Rules that decided the outcome: CW-R03 No-show cancellation fee is valid (Ryde policy; credibility A); CW-R06 Arrival counts only if GPS shows the driver at the pick-up point (Ryde policy; credibility B); CW-F04 Driver presence at the pick-up point (Ryde policy; credibility B; decisive for the approval step). Also used: MAT-04 Rider waiver filing window (Ryde policy; credibility A); CW-R00 Cancellation policy scope (Ryde policy; credibility B); CW-F02 Wait anchor (organizer cases and on-demand trips) (Ryde policy; credibility A); CW-F01 Booking type (the policy attached to this trip, extended by FairRyde; credibility D); CW-F03 Elapsed wait and margin (Ryde policy; credibility A); CW-F06 Rider counter-evidence strength (FairRyde assumption; credibility D); CW-R11 Pin and venue mismatch (FairRyde assumption; credibility D); DQ-06 Charged amount versus the policy amount (Ryde policy, extended by FairRyde; credibility D). There is no GPS trace from your phone and no call or message from you in the trip record. The pick-up pin is about 1,259 m from the address of Tiong Bahru Plaza; if you waited at the venue entrance you may not have been at the pin. Account history was used only to decide whether a person reviews this case; it did not affect the outcome. Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: the longest allowed gap between driver GPS points (300 seconds), used by CW-F04. If you disagree, you can ask for a human review through RydeHELP.
* Driver: Outcome: the S$5.00 cancellation fee stands. It goes to the driver, as compensation for the wait (CW-R09). This is a provisional decision; a Ryde staff member checks it before it takes effect. GPS confirms the driver's arrival at the pick-up pin (E-APP-04, E-GPS-05). Every driver GPS point from 08:43:00 to 08:46:00 is at the pick-up pin, and the longest stretch without a point at the pin is 120 seconds (E-GPS-05, E-GPS-06). The wait lasted 480 seconds, from 08:43:00 to 08:51:00; the policy for this trip requires more than 180 seconds (E-TRP-01). The driver called 1 time and sent 4 messages during the wait (E-CHT-01 to E-CHT-05). Rules that decided the outcome: CW-R03 No-show cancellation fee is valid (Ryde policy; credibility A); CW-R06 Arrival counts only if GPS shows the driver at the pick-up point (Ryde policy; credibility B); CW-F04 Driver presence at the pick-up point (Ryde policy; credibility B; decisive for the approval step). Also used: MAT-04 Rider waiver filing window (Ryde policy; credibility A); CW-R00 Cancellation policy scope (Ryde policy; credibility B); CW-F02 Wait anchor (organizer cases and on-demand trips) (Ryde policy; credibility A); CW-F01 Booking type (the policy attached to this trip, extended by FairRyde; credibility D); CW-F03 Elapsed wait and margin (Ryde policy; credibility A); CW-F06 Rider counter-evidence strength (FairRyde assumption; credibility D); CW-R11 Pin and venue mismatch (FairRyde assumption; credibility D); DQ-06 Charged amount versus the policy amount (Ryde policy, extended by FairRyde; credibility D). The pick-up pin is about 1,259 m from the address of Tiong Bahru Plaza, which was noted. Account history was used only to decide whether a person reviews this case; it did not affect the outcome. Part of this decision rests on assumptions FairRyde made where Ryde has published nothing: the longest allowed gap between driver GPS points (300 seconds), used by CW-F04. If you disagree, you can ask for a human review through RydeHELP.
* Numbers registered: {'amount': 'S$5.00', 'anchor': '08:43:00', 'start': '08:43:00', 'window_end': '08:46:00', 'end': '08:51:00', 'elapsed_s': '480', 'threshold_s': '180', 'driver_calls': '1', 'driver_messages': '4', 'pin_venue_m': '1,259', 'max_gap_s': '120', 'param_PING_MAX_GAP_S': '300'}; unmatched numbers: none

