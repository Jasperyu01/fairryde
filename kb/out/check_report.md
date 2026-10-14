# FairRyde knowledge base v0.3: check report

Generated from the YAML source files (knowledge base dated 2026-10-14).

* Rules: 104; vocabularies: 22; TX-CASE leaves: 35; entities: 25; events: 35; playbooks: 12
* Rule sources: 256; VERIFIED 208, NO_QUOTE (design assumption) 41, PARAPHRASE 7
* Credibility: A 32, B 9, C 1, D 62; modes: HARD 86, READ 10, HARD+READ 8
* DISP-002 fields mapped: 59 of 59 leaf paths
* DT-CW-NOSHOW enumeration: {'combinations': 192, 'unique': 192, 'gaps': 0, 'overlaps': 0}
* State machines: {'SM-TRIP': {'states': 12, 'reachable': 12, 'terminal': ['CANCELLED_BY_DRIVER', 'CANCELLED_BY_RIDER', 'CANCELLED_NO_SHOW', 'COMPLETED', 'TERMINATED_MID_TRIP']}, 'SM-CHARGE': {'states': 7, 'reachable': 7, 'terminal': []}, 'SM-TICKET': {'states': 8, 'reachable': 8, 'terminal': ['MERGED']}, 'SM-RULING': {'states': 5, 'reachable': 5, 'terminal': []}}
* Engine self-test: 128/128 variants pass
* ERP rules self-test: 53 ERP cases, the FC-R01 split, gate G3, the A2, A3 and A4 rule-card checks and the census: all pass
* Policy v2.1 self-test (A6): 60/60 pass (the three organizer samples pinned to their expected rulings, one-factor variants, tolls pass-through, regression E01 to E04 and E11, and the reconciliation records)
* Privacy dry run on the organizer cases (counts only): before {'PERSON_NAME': 13, 'PERSON_NAME_TOKEN': 29, 'VEHICLE_PLATE': 5, 'SG_PLATE': 5, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'CARD_TAIL': 1, 'LONG_NUMBER': 0}; after {'PERSON_NAME': 0, 'PERSON_NAME_TOKEN': 0, 'VEHICLE_PLATE': 0, 'SG_PLATE': 0, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'CARD_TAIL': 0, 'LONG_NUMBER': 0}; fragments after 0; clean True
* Leak scan of generated outputs (counts only): {'PERSON_NAME': 0, 'PERSON_NAME_TOKEN': 0, 'VEHICLE_PLATE': 0, 'SG_PLATE': 0, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'CARD_TAIL': 0, 'LONG_NUMBER': 0, 'NAME_FRAGMENTS': 0, 'total': 0}
* Annotation workbook: FairRyde_Annotation_v0.3.xlsx 已生成（没有人工填写过），旧文件备份到 backup/FairRyde_Annotation_v0.3.20261014T143404.xlsx
* Issues: ERROR 0, WARN 0, INFO 7

* DISP-002 under organizer_v2_1: **UPHOLD** (row R8), reasons CW-R-NOSHOW-VALID, CW-R-PIN-AMBIGUOUS, flags NO_RIDER_EVIDENCE, PIN_VENUE_MISMATCH, FRAUD_SIGNAL, GENERIC_ASSUMPTION_USED, confidence 0.939, tier **APPROVE**
* DISP-002 under organizer_case: **UPHOLD** (row R8), reasons CW-R-NOSHOW-VALID, CW-R-PIN-AMBIGUOUS, flags BOOKING_TYPE_INFERRED, BOUNDARY_MARGIN, MARGIN_WITHIN_SPREAD, NO_RIDER_EVIDENCE, PIN_VENUE_MISMATCH, FRAUD_SIGNAL, GENERIC_ASSUMPTION_USED, confidence 0.689, tier **APPROVE**
* DISP-002 under ryde_2026: **UPHOLD** (row R8), reasons CW-R-NOSHOW-VALID, CW-R-PIN-AMBIGUOUS, flags BOOKING_TYPE_INFERRED, NO_RIDER_EVIDENCE, PIN_VENUE_MISMATCH, CHARGE_AMOUNT_MISMATCH, FRAUD_SIGNAL, GENERIC_ASSUMPTION_USED, confidence 0.939, tier **APPROVE**

## Issues

| level | check | item | message |
|---|---|---|---|
| INFO | rule-credibility | CW-R06 | rated B but essential parameter(s) are D: ARRIVAL_GEOFENCE_M=D, TS_TOLERANCE_S=D, PING_MAX_GAP_S=D |
| INFO | rule-credibility | CW-R10 | rated A but essential parameter(s) are D: REMEDY_FORM=D |
| INFO | rule-credibility | CW-R14 | rated A but essential parameter(s) are C: DRIVER_LATE_GRACE_S=C |
| INFO | rule-credibility | FC-R13 | rated A but essential parameter(s) are D: TOLLS_TREATMENT=D, REMEDY_FORM=D |
| INFO | rule-credibility | FC-R14 | rated A but essential parameter(s) are D: MONEY_TOLERANCE_SGD=D |
| INFO | rule-credibility | FC-R15 | rated A but essential parameter(s) are D: MONEY_TOLERANCE_SGD=D, REMEDY_FORM=D |
| INFO | reason-outcome | CW-R-PIN-AMBIGUOUS | outcome field is descriptive: "secondary note; the outcome is unchanged, and human approval is required when the rider's statement places the rider at the named venue (AUTH-02)" |

## Engine self-test (unit tests of the reference engine, not ground truth)

| variant | change | outcome | row | tier | C | result |
|---|---|---|---|---|---|---|
| V01 | DISP-002 as given | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V02 | driver cancels 1 s before the 8-minute threshold | WAIVE_FEE | R6 | APPROVE | 0.693 | pass |
| V03 | driver pings 400 m away during the wait | WAIVE_FEE | R4 | APPROVE | 0.689 | pass |
| V04 | arrival marked while GPS shows the driver 300 m away for a minute after it, no platform GPS check: the wait counts from 08:45 | WAIVE_FEE | R6 | APPROVE | 0.939 | pass |
| V04B | platform GPS check says arrived, but GPS shows the driver 300 m away for 90 s after it | ESCALATE_HUMAN | R2 | HUMAN | 0.689 | pass |
| V04E | arrival marked while the driver stays 300 m from the pin, no platform GPS check | WAIVE_FEE | R1 | APPROVE | 0.689 | pass |
| V04F | platform GPS check says arrived; a single ping at that second is 300 m away, then the driver is at the pin | UPHOLD | R11 | APPROVE | 0.664 | pass |
| V04C | no platform GPS check and no driver pings from arrival on | WAIVE_FEE | R3 | APPROVE | 0.654 | pass |
| V04D | platform GPS check present, no driver pings during the wait | WAIVE_FEE | R5 | APPROVE | 0.654 | pass |
| V05 | rider GPS trace at the OneMap venue during the wait | ESCALATE_HUMAN | R7 | HUMAN | 0.725 | pass |
| V06 | clean baseline: pin at the venue, pings every 30 s, cancel at 08:52, rider without history | UPHOLD | R8 | AUTO | 0.964 | pass |
| V07 | only two driver pings, 8 minutes apart (rider contests) | ESCALATE_HUMAN | R10 | HUMAN | 0.664 | pass |
| V08 | as V07, and the rider's statement does not contest presence, timing or place | UPHOLD | R9 | APPROVE | 0.7 | pass |
| V10 | the reason says rider_cancelled, the system message says the driver canceled: the records disagree, ask for the trip record (CLS-06) | REQUEST_INFO | None | HUMAN | None | pass |
| V11 | V06, and the driver made no call and sent no message | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V12 | instruction injected in the rider's description | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V13 | safety content in the description | UPHOLD | R8 | HUMAN | 0.689 | pass |
| V14 | V06, and the rider was charged S$7.00 against a S$5.00 policy | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V15 | dispute filed 40 days after the trip | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V16 | V06 with driver pings 290 s apart: inside the 300 s limit but outside the plausible range low end | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V17 | the case's own policy object sets the no-show threshold to 10 minutes | WAIVE_FEE | R6 | APPROVE | 0.939 | pass |
| V18 | V06, and the app's wait timer starts 60 s after driver_wait_start (beyond the 30 s tolerance) | UPHOLD | R8 | APPROVE | 0.939 | pass |
| V19 | V06 with a S$15 fee in both the policy object and the trip record (above the automatic limit) | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V20 | no policy object (Ryde profile) and the trip is in January 2026, before the profile's effective date | ESCALATE_HUMAN | R8 | HUMAN | 0.939 | pass |
| V21 | service type RydeTAXI | ESCALATE_HUMAN | R8 | HUMAN | 0.689 | pass |
| V22 | V06 with the cancellation at 08:50 (wait 7 minutes): fee waived automatically | WAIVE_FEE | R6 | AUTO | 0.964 | pass |
| V23 | V22, and the rider (who benefits) injected an instruction | WAIVE_FEE | R6 | APPROVE | 0.964 | pass |
| V24 | V06 with pings every 30 s offset by 15 s: a ping 80 m out 15 s before arrival, and one 150 m out after the cancellation | UPHOLD | R8 | AUTO | 0.964 | pass |
| V25 | V06 with one driver ping 150 m away in the middle of the wait (a GPS outlier): FairRyde's logic sets it aside, so approval (D29) | UPHOLD | R11 | APPROVE | 0.939 | pass |
| V26 | V06, and the driver (who benefits) injected an instruction in a chat message | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V27 | V06 with the cancellation 1 s after the threshold and all records agreeing | UPHOLD | R8 | AUTO | 0.718 | pass |
| V28 | V06 with the cancellation 1 s before the threshold and all records agreeing | WAIVE_FEE | R6 | AUTO | 0.718 | pass |
| V29 | the case's policy object has no no-show threshold: Ryde's 3 minutes apply (META-01 fallback) | UPHOLD | R8 | APPROVE | 0.939 | pass |
| V30-1 | DISP-002 with the GPS array shuffled (seed 1): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V30-2 | DISP-002 with the GPS array shuffled (seed 2): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V30-3 | DISP-002 with the GPS array shuffled (seed 3): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V31 | only one ping inside the wait, 150 m out; pings at the pin 20 s before arrival and 20 s after the cancellation | ESCALATE_HUMAN | R10 | HUMAN | 0.639 | pass |
| V32 | V06 with pings every 5 s and a 10-second jump to 150 m (three pings): a GPS outlier, not a departure; approval (D29) | UPHOLD | R11 | APPROVE | 0.939 | pass |
| V33 | as V32 but the jump is 400 m (implied 288 km/h): a data error, set aside, gate G1 | UPHOLD | R11 | APPROVE | 0.939 | pass |
| V34 | V06, but the driver drives off at 08:51:15, after the 8-minute threshold, and cancels at 08:52 | UPHOLD | R8 | AUTO | 0.964 | pass |
| V35 | Ryde advance booking for 08:45: driver at the pin from 08:38, 150 m away for 45 s at 08:45, then waiting 4 min 15 s | UPHOLD | R11 | APPROVE | 0.914 | pass |
| V36 | V06 with pings at 08:43, 08:46 and 08:48 and one after the cancellation at 08:53:30, which must not matter | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V37 | V06 without the platform check; the first ping at the pin comes 270 s after the arrival indication (CW-F03B decides, so approval) | WAIVE_FEE | R6 | APPROVE | 0.964 | pass |
| V38 | Ryde profile and no arrival indication at all (no driver_arrived event or arrival time) | WAIVE_FEE | R3 | APPROVE | 0.929 | pass |
| V39 | policy object without a threshold and a cancellation exactly 180 s after the anchor: Ryde's 'more than 3 minutes' applies | WAIVE_FEE | R6 | APPROVE | 0.714 | pass |
| V40 | V06 without the system message: the trip record's reason is enough for the precondition | UPHOLD | R8 | AUTO | 0.964 | pass |
| V41 | V06, but the trip record starts the wait at 08:42, 60 s before the confirmed arrival: the wait counts from the arrival | UPHOLD | R8 | APPROVE | 0.939 | pass |
| V42 | V41 with no driver pings during the wait (platform check present) | WAIVE_FEE | R5 | APPROVE | 0.904 | pass |
| V43 | no platform check; at the pin at 08:36 and 08:51:30, and the only ping in between is one 150 m away (an outlier, not evidence) | WAIVE_FEE | R3 | APPROVE | 0.664 | pass |
| V44 | no platform check; GPS at the pin 10 s after the arrival mark, then 150 m away from 08:43:20 until the cancellation | WAIVE_FEE | R1 | APPROVE | 0.689 | pass |
| V45 | V06, but the last ping (08:47) is 400 m away and no later ping shows the driver back: a departure on one ping, so approval | WAIVE_FEE | R4 | APPROVE | 1.0 | pass |
| V46 | no platform check; a ping 60 m out 10 s after the arrival mark (inside the tolerance), at the pin from 08:43:40, cancel 08:51:20 | WAIVE_FEE | R6 | APPROVE | 0.773 | pass |
| V47 | V38 as a recorded advance booking: with no arrival indication there is no wait, so no contact count either | WAIVE_FEE | R3 | APPROVE | 0.929 | pass |
| V48 | DISP-002 with the last ping (08:51:00, at the cancellation) 60 m from the pin and no ping after it: not a departure | UPHOLD | R11 | APPROVE | 0.689 | pass |
| V49 | V06, but the driver is 400 m away from 08:50:30, 30 s before the threshold, and never comes back: leaving counts | WAIVE_FEE | R4 | APPROVE | 1.0 | pass |
| V50 | Ryde on-demand trip (more than 180 s): at the pin until 08:45, 400 m away at 08:46:00 (the threshold moment) and never back | UPHOLD | R11 | APPROVE | 0.881 | pass |
| V51 | V06 with pings every 120 s and one 400 m away at 08:47: set aside as an outlier, but the driver may have been away 240 s | UPHOLD | R11 | APPROVE | 0.975 | pass |
| V52 | V06 with pings every 120 s: away from 08:50:45 (within 30 s of the threshold) until after the cancellation, then back | UPHOLD | R11 | APPROVE | 1.0 | pass |
| V53 | Ryde advance booking for 08:45: away from 08:44:50 to 08:47:40 with no ping in between, back at 08:49: the driver missed the wait | WAIVE_FEE | R4 | APPROVE | 0.939 | pass |
| V54 | V06 at the pin every 20 s until 08:50:20, one ping 100 m out at 08:51:10 (just after the threshold), back at 08:51:30 | UPHOLD | R11 | APPROVE | 1.0 | pass |
| V55 | V06 with pings every 30 s until 08:46 and none after (300 s of silence before the threshold, rider not contesting) | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V56 | V06, and the rider messages 'still getting ready, can wait another 10 min?' (round 1 case E01): an admission, not counter-evidence | UPHOLD | R8 | AUTO | 1.0 | pass |
| V57 | V06, and the rider messages 'Coming!! 1 min, walking over from the MRT' (round 1 case E03) | UPHOLD | R8 | AUTO | 1.0 | pass |
| V58 | V06, and the rider messages 'coming down, 2 min' (the message of round 1 case E07; E07 is a waiting fee, which this engine does not run) | UPHOLD | R8 | AUTO | 1.0 | pass |
| V59 | V06, and the rider messages that they are at the pick-up point and cannot see the car | ESCALATE_HUMAN | R7 | HUMAN | 1.0 | pass |
| V60 | V06, and the rider first says 'coming down, 2 min', then 'I'm here at the lobby, where are you?' before the cancellation | ESCALATE_HUMAN | R7 | HUMAN | 1.0 | pass |
| V61 | V06, and the rider calls the driver during the wait (what was said is not recorded): the other reading decides, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V62 | V06, and the rider's message fits both readings ('I'm here, coming out now'): approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V63 | V06, and the rider only answers 'ok' during the wait | UPHOLD | R8 | AUTO | 1.0 | pass |
| V64 | V06, and the rider messages 'where are you?' only after the cancellation: outside the wait | UPHOLD | R8 | AUTO | 0.964 | pass |
| V65 | V06, and the rider asks 'uncle coming?' during the wait (asking where the driver is contests presence) | ESCALATE_HUMAN | R7 | HUMAN | 1.0 | pass |
| V66 | V06, the driver asks 'Are you at the lobby now?' and the rider answers 'yes': unclear on its own, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V67 | Ryde advance booking for 08:45, driver at the pin from 08:38; rider GPS at the pin at 08:40, after the arrival and before the anchor | ESCALATE_HUMAN | R7 | HUMAN | 1.0 | pass |
| V68 | V06, and the rider messages 'coming down now' at 08:51:30, after the 8-minute threshold and before the cancellation | UPHOLD | R8 | AUTO | 1.0 | pass |
| V69 | V06, and the rider messages 'I'm at the lobby already' at 08:41, after the assignment and before the arrival (D30): approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V70 | V06, and the rider asks 'where are you?' at 08:41, before the driver arrived: not counter-evidence | UPHOLD | R8 | AUTO | 0.964 | pass |
| V71 | V06, and rider GPS at the pick-up at 08:41:30, before the arrival indication (D30): approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V72 | V08 (sparse driver GPS, statement not contesting), and the rider says 'I'm here at the pick-up point' before the arrival (D30) | ESCALATE_HUMAN | R10 | HUMAN | 0.7 | pass |
| V73 | V06, and the rider says 'I'm at the lobby already' at 08:30:05, before the driver was assigned (08:30:15): not counted | UPHOLD | R8 | AUTO | 0.964 | pass |
| V74 | V06, and the rider names the venue before the arrival: 'I'm at Tiong Bahru Plaza' at 08:41 (unclear placement): approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V75 | V06, and the rider sends 'u reach already?' at 08:41, before the arrival: a question, an instruction or an admission, not counted | UPHOLD | R8 | AUTO | 0.964 | pass |
| V76 | V06, and the rider sends 'Pick me up at the lobby' at 08:41, before the arrival: a question, an instruction or an admission, not counted | UPHOLD | R8 | AUTO | 0.964 | pass |
| V77 | V06, and the rider sends '我在路上' at 08:41, before the arrival: a question, an instruction or an admission, not counted | UPHOLD | R8 | AUTO | 0.964 | pass |
| V78 | V06, and the rider calls the driver at 08:41, before the arrival (what was said is not recorded): not counted | UPHOLD | R8 | AUTO | 0.964 | pass |
| V79 | V06, and the rider messages 'down liao, coming' during the wait: placement and admission, so unclear (approval) | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V80 | V06, the driver asks 'Are you at the lobby now?' and the rider answers with a thumbs-up: unclear in context, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V81 | V06, the trip record has the arrival at 08:42:50 and the event at 08:43:00; the rider contests at 08:42:55 (within the tolerance) | ESCALATE_HUMAN | R7 | HUMAN | 0.964 | pass |
| V82 | V69 filed 40 days after the trip: MAT-04 decides, so the D30 message does not change the automatic outcome | UPHOLD | R8 | AUTO | 1.0 | pass |
| V83 | V06 without the driver_assigned event (booking type not recorded): no crash; records missing, so approval | UPHOLD | R8 | APPROVE | 0.929 | pass |
| V84 | V06, and the rider sends 'Already at lobby, where are you?' at 08:41, before the arrival: counted (D30), so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V85 | V06, and the rider sends 'I wait at lobby' at 08:41, before the arrival: counted (D30), so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V86 | V06, and the rider sends 'I'm at TBP now' at 08:41, before the arrival: counted (D30), so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V87 | V06, the driver asks 'Are you at the lobby?' at 08:41 and the rider answers 'yes' before the arrival: counted (D30), so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V88 | V69 with the assignment stamped at 08:44, after the arrival (a data error): the window falls back to the booking, records missing | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V89 | V06, the driver's message asks a question mid-message and the rider answers 'ok' in the wait: unclear in context, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V90 | V06, and the rider messages 'otw down liao' during the wait: an admission, automatic as before A1b | UPHOLD | R8 | AUTO | 1.0 | pass |
| V91 | V08 (sparse driver GPS, statement not contesting), and only rider GPS at the pin at 08:41:30, before the arrival (D33) | ESCALATE_HUMAN | R10 | HUMAN | 0.7 | pass |
| V92 | V06 (the pick-up is a mall), and the rider messages "I'm at the mall already" during the wait: unclear, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V93 | V06, and the rider messages "I'm at the mall already" at 08:41, before the arrival (D30): counted, so approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V94 | V06 without the platform check; GPS first confirms the driver 40 s after the arrival mark, and the wait from then meets the threshold | UPHOLD | R11 | APPROVE | 0.798 | pass |
| V95 | V06, but the driver pulls away 2 s before the threshold (60 m out, within the tolerance of the window end, so not counted): automatic before A3, approval now (D29) | UPHOLD | R11 | APPROVE | 0.964 | pass |
| V96 | V06 without the platform check; a 150 m outlier at 08:42:45 is the last ping before the arrival mark, so without the logic it would be CW-R06's moment ping: R11 (D29) | UPHOLD | R11 | APPROVE | 0.964 | pass |
| V96B | as V96, but pings at the pin follow the outlier before the arrival mark: it could not change the arrival, so automatic | UPHOLD | R8 | AUTO | 0.964 | pass |
| V100 | V96 with the platform's arrival check: an outlier before the indication cannot contradict the check, so automatic | UPHOLD | R8 | AUTO | 0.964 | pass |
| V97 | Ryde advance booking for 08:45, platform check at 08:38, one 150 m outlier at 08:40:15: it can change neither the arrival nor the wait, so the uphold stays automatic | UPHOLD | R8 | AUTO | 0.964 | pass |
| V98 | V06 with the driver 150 m away from 08:46 to 08:48, those pings written in UTC: sorted by instant, a departure (R4) | WAIVE_FEE | R4 | AUTO | 1.0 | pass |
| V99 | V06 with pings 3 m from the pin and one 30 m away: inside the 50 m area, but at the radius's 25 m low end it is an outlier, so the uphold would rest on FairRyde's logic (D29, radius part): approval | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V99B | as V99 with the far ping 20 m away: GPS drift around a parked car, inside the radius even at its 25 m low end (Jasper, 2026-10-14, D39 (g)), so the uphold rests on the pings alone: automatic | UPHOLD | R8 | AUTO | 0.964 | pass |
| V101 | Ryde advance booking for 08:45 with the platform check at 08:38; an outlier 10 s after the indication is the last ping before 08:38:30, so without the logic it would contradict the check: R11 (D29) | UPHOLD | R11 | APPROVE | 0.964 | pass |
| V102 | Ryde on-demand trip: at the pin until 08:45:00, then the next ping (08:46:40, 400 m) comes 40 s after the 3-minute wait ended: the driver may have left before it ended, so approval | UPHOLD | R11 | APPROVE | 1.0 | pass |
| V103 | Ryde advance booking for 08:45: 400 m away from 08:40:20 to 08:44:50 and first back at the pin at 08:45:50: the pings cannot show the driver at the pick-up when the counted wait started, so approval | UPHOLD | R11 | APPROVE | 0.767 | pass |
| V104 | safety content without v0.1's words in the description: 'After that he stopped on the PIE and told me to get out of the car.' | UPHOLD | R8 | HUMAN | 0.689 | pass |
| V105 | safety content without v0.1's words in the description: 'He then drove the wrong way and would not let me out, I felt kidnapped.' | UPHOLD | R8 | HUMAN | 0.689 | pass |
| V106 | safety content without v0.1's words in the description: 'He made racist remarks about me.' | ESCALATE_HUMAN | None | HUMAN | None | pass |
| V107 | rudeness alone in the description: not safety content, the no-show ruling stands as for DISP-002 | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V108 | every record says the rider canceled: a rider cancellation fee case (CW-RIDERCANCEL), not ruled here | None | None | n/a (reclassified to CW-RIDERCANCEL) | None | pass |
| V109 | reason rider_no_show, but the app events record a rider cancellation: the records disagree (CLS-06) | REQUEST_INFO | None | HUMAN | None | pass |
| V110 | no record says who canceled: ask for the trip record, no fee ruling (CLS-06) | REQUEST_INFO | None | HUMAN | None | pass |
| V111 | the driver canceled for another reason (driver_cancelled_other): not a no-show, CW-OTHER (CLS-06) | None | None | n/a (reclassified to CW-OTHER) | None | pass |
| V112 | a rider cancellation with safety content: reclassified, and still a person sees it (CLS-01, gate G4) | None | None | HUMAN | None | pass |
| V113 | cancelled_by 'customer' against reason rider_no_show: the records disagree (CLS-06) | REQUEST_INFO | None | HUMAN | None | pass |
| V114 | an app event spelled rider_canceled against reason rider_no_show: the records disagree | REQUEST_INFO | None | HUMAN | None | pass |
| V115 | a system message 'Trip auto-cancelled' against reason rider_no_show: the records disagree | REQUEST_INFO | None | HUMAN | None | pass |
| V116 | the system canceled and the record gives no reason: CW-OTHER (CLS-06) | None | None | n/a (reclassified to CW-OTHER) | None | pass |
| V117 | the reason written RIDER_NO_SHOW is still a driver's no-show cancellation: as DISP-002 | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V118 | the driver canceled and the record gives no reason: ask for the trip record (CLS-06) | REQUEST_INFO | None | HUMAN | None | pass |
| V119 | a clean automatic uphold, but the rider's message says the driver canceled because of the rider's ethnicity: no proposed outcome, the whole case to a person, the fee a secondary claim (CLS-01, SE-R01) | ESCALATE_HUMAN | None | HUMAN | None | pass |
| V120 | a rider cancellation whose description mentions discrimination: reclassified, and the whole case to a person | None | None | HUMAN | None | pass |

## Entity coverage (ONT.6)

| entity | name | kind | covered by | status |
|---|---|---|---|---|
| ENT-ACCOUNT | Account | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-DISPUTEHISTORY | DisputeHistory | value_object | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-VEHICLE | Vehicle | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-PLATFORM | Platform (Ryde) | business | every case | ok |
| ENT-TRIP | Trip | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-PLACE | Place | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-EVENT | TripEvent | business | DISP-002 | ok (from the case file) |
| ENT-GPSPING | GPSPing | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-COMM | Communication | business | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-CHARGE | Charge | business | DISP-002 | ok (from the case file) |
| ENT-POLICYDOC | PolicyDocument | business | DISP-002 | ok (from the case file) |
| ENT-CLAUSE | PolicyClause | business | DISP-002 | ok (from the case file) |
| ENT-ROUTE | Route | business | DISP-001 | ok (from the case file) |
| ENT-INCIDENT | TrafficIncident | business | DISP-001 | ok (from the case file) |
| ENT-FARE | FareBreakdown | value_object | DISP-001, DISP-003 | ok (from the case file) |
| ENT-SURGE | SurgeEvent | business | DISP-003 | ok (from the case file) |
| ENT-TICKET | DisputeTicket | case | DISP-001, DISP-002, DISP-003 | ok (from the case file) |
| ENT-CLAIM | Claim | case |  | created by the pipeline for every case |
| ENT-EVIDENCE | EvidenceItem | case |  | created by the pipeline for every case |
| ENT-FINDING | Finding | case |  | created by the pipeline for every case |
| ENT-RULING | Ruling | case |  | created by the pipeline for every case |
| ENT-REVIEW | HumanReview | case |  | created when a person reviews a ruling (APPROVE and HUMAN tiers) |
| ENT-PRECEDENT | Precedent | case |  | created only from human-reviewed rulings |
| ENT-ORGREF | OrganizerReference | case | DISP-001 | ok (from the case file) |
| ENT-ARGUMENT | Argument | system_artifact |  | created by the pipeline for every case |

## Rule sources and quote verification

| rule | # | type | doc | doc date | profile | status | where | quote | note |
|---|---|---|---|---|---|---|---|---|---|
| META-01 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Organizer cases are scored against the organizer's expected ruling, computed under the emb |
| META-01 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | All AI dispute resolution agents (Rider Advocate, Driver Advocate, Judge) and human reviewers in the RydeResol |  |
| META-02 | 1 | RYDE_POLICY | RYDE-18229758389017 | 2026-02-26 |  | VERIFIED | corpus body | The increase is due to the platform fee changes effective 17 Feb 2026. |  |
| META-03 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 1. Introduction | These Terms of Service and the Ryde Policies (as defined below) constitute a legally binding agreement ("Agree |  |
| META-03 | 2 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 2. Definitions ("Ryde Policies") | frequently asked questions (FAQs), in-app or website product/service descriptions and information cards |  |
| META-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| META-05 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 用行业通用规则先顶上，并显式标注来源为'通用假设' |  |
| META-05 | 2 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 会让人误以为系统读了合同 |  |
| CLS-01 | 1 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Assault, harassment, or abuse of any kind will not be tolerated. | Ryde Code of Conduct item 5. |
| CLS-01 | 2 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | We have a zero-tolerance approach to any form of misconduct or inappropriate behavior between drivers and pass |  |
| CLS-01 | 3 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Attempted or Actual Physical Assault | Ryde's Code of Conduct list also names 'Verbal or Physical Sexual Harassment', 'Kidnapping |
| CLS-01 | 4 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Kidnapping |  |
| CLS-01 | 5 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Threats and Intimidation |  |
| CLS-01 | 6 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | drivers must not ask overly personal questions, comment on anyone's appearance, or contact passengers after a  |  |
| CLS-01 | 7 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Reckless or dangerous driving that endangers passengers, pedestrians, or other road users is strictly prohibit |  |
| CLS-01 | 8 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Alcohol, drugs, and weapons are not tolerated. |  |
| CLS-01 | 9 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Do not commit crimes. | Ryde Code of Conduct item 6. |
| CLS-01 | 10 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Comments on race, ethnicity, national origin, disability, etc | Driver Performance and Community Standards: errant behavior that disables an account. |
| CLS-01 | 11 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | PARAPHRASE |  |  | Lyft, Grab and DiDi route safety incidents to humans (research note 02). |
| CLS-01 | 12 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | FairRyde's design (step A4, round 1 finding FX6, and A4 check round 1): the definition by  |
| CLS-01 | 13 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | issue rulings, determine fault, or recommend resolutions on safety incidents. |  |
| CLS-01 | 14 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | flag any dispute that contains safety-related keywords or indicators for immediate human escalation, regardles |  |
| CLS-01 | 15 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | automatically escalated to human review |  |
| CLS-02 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 一封邮件/单据涉及多个事件，只选一个会丢信息，全多选又没主次 |  |
| CLS-03 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | The SE exception covers every SE type since step A4 (round 1 finding FX6: a mid-trip eject |
| CLS-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| CLS-05 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | "dispute_type": "no_show_charge" |  |
| CLS-05 | 2 | ORGANIZER | ORG-DISP001 | 2026-09 |  | VERIFIED | sources/organizer/disp001.md | "dispute_type": "route_deviation" |  |
| CLS-05 | 3 | ORGANIZER | ORG-DISP003 | 2026-09 |  | VERIFIED | sources/organizer/disp003.md | "dispute_type": "fare_dispute" |  |
| CLS-06 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | "cancellation_reason": "rider_no_show" |  |
| CLS-06 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | Rider cancels after 3 minutes of matching OR |  |
| CLS-06 | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Taking the canceling party from the records, sending other cancellations to CW-OTHER and a |
| MAT-01 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 关键实体不出现在正文里（靠线程、发件人、上下文推断） |  |
| MAT-02 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | "更新已有任务"比"新建任务"难，需要判断是不是同一件事 |  |
| MAT-02 | 2 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | You can appeal within 24 hours if you disagree with the outcome of your claim with any additional supporting e | Ryde lets drivers appeal a cleaning-claim outcome, so appeals of decided cases exist. |
| MAT-03 | 1 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| MAT-03 | 2 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | You can appeal within 24 hours if you disagree with the outcome of your claim with any additional supporting e | Ryde already lets drivers appeal cleaning-claim outcomes. |
| MAT-04 | 1 | RYDE_POLICY | RYDE-18229758389017 | 2026-02-26 |  | VERIFIED | corpus body | *Requests submitted after 30 days of the trip will not be considered for waivers. |  |
| MAT-04 | 2 | RYDE_POLICY | RYDE-27085468660505 | 2026-09-25 |  | VERIFIED | corpus body | you may submit a fee waiver request via RydeHELP in our app within 30 days of the trip* |  |
| DQ-01 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | DISP-002 logs wait_timer_started 10 s after driver_arrived. |
| DQ-02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| DQ-03 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| DQ-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| DQ-05 | 1 | RYDE_POLICY | RYDE-30741244296217 | 2025-07-17 |  | VERIFIED | corpus body | For a detailed breakdown of your fare, please refer to your receipt. |  |
| DQ-06 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "cancellation_fee": 5.00 |  |
| DQ-06 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | Rider will be charged a Cancellation Fee of $6.61* if: | Quoted for the amount only. [clause is one side of a META-04 known conflict: does not coun |
| DQ-06 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | is charged to the rider when the driver cancels after the free wait period. | Quoted for the amount: the fee of Section 2.2 is S$5.00. |
| CW-F01 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | Scheduled pickup 08:45. | DISP-002 says 'Scheduled pickup' yet assigns in 15 s with a 13-minute ETA; booking type is |
| CW-F02 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "driver_wait_start": "2026-09-13T08:43:00+08:00" |  |
| CW-F02 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | waits for > 3 minutes for the rider to arrive at the pick-up point and cancels the trip (Rider NO SHOW and no  |  |
| CW-F02B | 1 | INDUSTRY | IND-GRAB-ADVANCE | read 2026-10-05 |  | VERIFIED | sources/research/09_fact_check.md | Your driver will arrive early and wait for you for up to 15 minutes starting from the indicated pickup time. |  |
| CW-F02B | 2 | INDUSTRY | IND-BOLT-SCHEDULED | read 2026-10-05 |  | VERIFIED | sources/research/09_fact_check.md | The scheduled wait time of 5 minutes will be counted only from the scheduled start of the ride. |  |
| CW-F02B | 3 | RYDE_POLICY | RYDE-23575142762393 | 2023-10-02 |  | VERIFIED | corpus body | You arrived at the pickup location and the customer was not present within 3 minutes of your arrival. | Driver article (2023), not specific to advance bookings; conflicts with the rule above for |
| CW-F02B | 4 | RYDE_POLICY | RYDE-20244064619161 | 2024-04-23 |  | VERIFIED | corpus body | The driver pressed "I'm Here", waits for > 3 minutes for rider to arrive at the pick-up point and cancels the  | Driver policy pages (2024-04-23, and RYDE-33362932998937 of 2024-06-05 with the same words |
| CW-F02C | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | from the scheduled pickup time. |  |
| CW-F02C | 2 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp002.md | Free wait timer started. 5 min free wait period ends at 08:48. | The app's timer in DISP-002 starts at the driver's arrival (08:43), not at the scheduled t |
| CW-F03 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | No-show threshold (8 min) reached. | Logged at exactly 8:00 after driver_wait_start, so the organizer counts 'at least 8 minute |
| CW-F03 | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | Has waited for more than 3 mins |  |
| CW-F03 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | After 5 minutes, the driver may cancel the trip as a "rider no-show." |  |
| CW-F03B | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Drivers are only allowed to indicate arrival and impose the Waiting Time Fee only if he/she: |  |
| CW-F03B | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data |  |
| CW-F03B | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Where the wait starts when GPS confirms the driver only after the arrival indication is Fa |
| CW-F04 | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data |  |
| CW-F04 | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Has waited for more than 3 mins | The article's two conditions together (at the pick-up location according to GPS, and has w |
| CW-F04 | 3 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | The driver presses "I'm Here", waits for > 3 minutes for the rider to arrive at the pick-up point and cancels  | The window: the wait the fee pays for ends at the threshold (waits for more than 3 minutes |
| CW-F04 | 4 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | Driver GPS within 10m of pickup point. | The organizer's system uses 10 m for auto-arrival; FairRyde uses a wider radius for presen |
| CW-F04B | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | FairRyde's presence logic (open items D18, D24, D26), split out of CW-F04 in step A3 (roun |
| CW-F04B | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data | The condition the logic serves (CW-F04, CW-R06); Ryde does not say how GPS presence is che |
| CW-F05 | 1 | RYDE_POLICY | RYDE-115001438754 | 2021-09-20 |  | VERIFIED | corpus body | Try to contact the rider by in-app chat or call. |  |
| CW-F05 | 2 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | VERIFIED | sources/research/02_industry_dispute_benchmark.md | Attempted to contact you (or you contacted them) | Lyft's no-show conditions (research note 02). |
| CW-F05 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | At least 1 in-app chat message |  |
| CW-F05 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | At least 1 phone call |  |
| CW-F06 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Content-based reading of rider calls and messages since KB v0.2 (fix FX1, validation round |
| CW-F07 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 7. Cancellation, 7.2 Cancellation Terms for Users (paragraph 2) | If you decide to cancel your ride booking or do not show up at the designated location, you may be charged a C |  |
| CW-R00 | 1 | RYDE_POLICY | RYDE-4407761313305 | 2024-03-18 |  | VERIFIED | corpus body | Cancellation Policy applies to all Service Types * in the Ryde app and is executed on a service level, not dri |  |
| CW-R00 | 2 | RYDE_POLICY | RYDE-4407761313305 | 2024-03-18 |  | VERIFIED | corpus body | *All services except RydeTAXI |  |
| CW-R01 | 1 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | All cancellations made within 3 minutes of matching are not chargeable. |  |
| CW-R02 | 1 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | All cancellations made > 15 minutes before the scheduled trip time are not chargeable. |  |
| CW-R02 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | If the advanced trip request is accepted only after 5:45 PM, riders will have a 3 minute grace period) |  |
| CW-R03 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "no_show_threshold_min": 8 |  |
| CW-R03 | 2 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "cancellation_fee_after_wait": 5.00 |  |
| CW-R03 | 3 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | Rider will be charged a Cancellation Fee of $6.61* if: | Quoted for the amount; the operative condition is the next quote. [clause is one side of a |
| CW-R03 | 4 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | The driver presses "I'm Here", waits for > 3 minutes for the rider to arrive at the pick-up point and cancels  |  |
| CW-R03 | 5 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | is charged to the rider when the driver cancels after the free wait period. |  |
| CW-R03 | 6 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | After 5 minutes, the driver may cancel the trip as a "rider no-show." |  |
| CW-R04 | 1 | RYDE_POLICY | RYDE-115001438754 | 2021-09-20 |  | VERIFIED | corpus body | If the rider still cannot be reached, you may need to cancel the trip. |  |
| CW-R05 | 1 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | Riders may be charged a Waiting Time Fee of $5 at the end of the trip if: |  |
| CW-R05 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | The driver presses "I'm Here", waits for > 3 minutes for the rider to board, and continues the trip (Rider boa |  |
| CW-R05 | 3 | RYDE_POLICY | RYDE-4408079464217 | 2026-09-22 |  | VERIFIED | corpus body | Drivers are advised to tap on the waiting time fee toggle upon drop-off as we are unable to charge the rider o |  |
| CW-R06 | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Drivers are only allowed to indicate arrival and impose the Waiting Time Fee only if he/she: |  |
| CW-R06 | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data |  |
| CW-R06 | 3 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Otherwise, you will not be charged the $6.61 Waiting Time Fee if any of the above are not fulfilled. | [clause is one side of a META-04 known conflict: does not count toward A] |
| CW-R06 | 4 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | Driver GPS within 10m of pickup point. Speed 0 km/h. Auto-arrival confirmed. |  |
| CW-R07 | 1 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 |  | VERIFIED | corpus body | Rider cancels after 3 minutes of matching OR |  |
| CW-R08 | 1 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | PARAPHRASE |  |  | Grab: a late driver (ETA + 3 min) forfeits the fee; Gojek ETA + 5 min (research note 02). |
| CW-R08 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Two elements are FairRyde's: the 'not moving toward the pick-up point' condition has no so |
| CW-R08 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | (defined as scheduled pickup time + 5 minutes), the rider may cancel at no charge. |  |
| CW-R09 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "fee_goes_to": "driver_compensation" |  |
| CW-R09 | 2 | RYDE_POLICY | RYDE-4407761228825 | 2023-04-11 | ryde_2026 | VERIFIED | corpus body | Cancellation Fees compensate drivers for the time and effort they spend getting to your location. |  |
| CW-R09 | 3 | RYDE_POLICY | RYDE-4408070838297 | 2026-09-25 | ryde_2026 | VERIFIED | corpus body | Drivers will receive a $4.50 cancellation fee automatically if they cancel after >3 minutes of waiting. |  |
| CW-R09 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | The cancellation fee is transferred to the driver as compensation for time and fuel. |  |
| CW-R10 | 1 | RYDE_POLICY | RYDE-18229758389017 | 2026-02-26 |  | VERIFIED | corpus body | If you are eligible, we will issue you a voucher** with a unique code worth $6.61 as a refund for the incurred |  |
| CW-R10 | 2 | RYDE_POLICY | RYDE-27085468660505 | 2026-09-25 |  | VERIFIED | corpus body | If you are eligible, we will issue you a voucher** with a unique code worth $5.00 as a refund for the incurred |  |
| CW-R10 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | The $5.00 fee is reversed and refunded to the rider. |  |
| CW-R10 | 4 | ORGANIZER | ORG-DISP001 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp001.md | "method": "original_payment_method" |  |
| CW-R11 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 7. Cancellation, 7.2 Cancellation Terms for Users (paragraph 2) | If you decide to cancel your ride booking or do not show up at the designated location, you may be charged a C |  |
| CW-R11 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Approval trigger and goodwill option are FairRyde's design (D5). |
| CW-R12 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| CW-R13 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | At least 1 in-app chat message |  |
| CW-R13 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | At least 1 phone call |  |
| CW-R13 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | If the driver fails to meet both contact obligations, the cancellation fee is |  |
| CW-R13 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | The driver failed to meet both contact obligations. The $5.00 fee is reversed and refunded to the rider. |  |
| CW-R13 | 5 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Reading 'fails to meet both contact obligations' as failing either of the two is FairRyde' |
| CW-R14 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | (defined as scheduled pickup time + 5 minutes), the rider may cancel at no charge. |  |
| CW-R14 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | fails to attempt contact, the rider is eligible for a |  |
| FC-F01 | 1 | RYDE_POLICY | RYDE-30741244296217 | 2025-07-17 |  | VERIFIED | corpus body | Fares quoted for our services are generally fixed, except for RydeTAXI. | [clause is one side of a META-04 known conflict: does not count toward A] |
| FC-F01 | 2 | RYDE_POLICY | RYDE-360004075214 | 2024-10-08 |  | VERIFIED | corpus body | All fares are fixed at the time of booking but does not include toll charges such as ERP. |  |
| FC-F01 | 3 | RYDE_POLICY | RYDE-51399796192921 | 2025-10-10 |  | VERIFIED | corpus body | If the driver accepts your edit destination request, a $3.00 add/edit destination fee will apply. |  |
| FC-F01 | 4 | RYDE_POLICY | RYDE-50798691815449 | 2025-10-09 |  | VERIFIED | corpus body | Once the driver accepts, your trip fare will be recalculated, and your route will be updated to the new destin |  |
| FC-F01 | 5 | RYDE_POLICY | RYDE-34883561600025 | 2025-09-18 |  | VERIFIED | corpus body | You will receive a notification or a request pop up on your Ryde Driver app when riders request to change the  | Driver article: an added stop is the same request as a changed drop-off. |
| FC-F01 | 6 | RYDE_POLICY | RYDE-51399674412441 | 2025-10-10 |  | VERIFIED | corpus body | The rider can add another destination, leading to a map confirmation (for multiple stops). | Rider article: an added stop goes through the same edit request as a changed destination. |
| FC-F01 | 7 | RYDE_POLICY | RYDE-51399674412441 | 2025-10-10 |  | VERIFIED | corpus body | New destination and fare confirmation will be displayed. | The next step of the same article: the edit, an added stop included, ends with a fare conf |
| FC-F02 | 1 | RYDE_POLICY | RYDE-50798691815449 | 2025-10-09 |  | VERIFIED | corpus body | Once the driver accepts, your trip fare will be recalculated, and your route will be updated to the new destin |  |
| FC-F02 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Method from research note 08 (sparse-ping simulation). |
| FC-F02 | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | The final-itinerary baseline and the split at the point nearest the car at each accepted c |
| FC-F02 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Route deviation distance is calculated as: |  |
| FC-F03 | 1 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you g |  |
| FC-F03 | 2 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | hence the driver may decide to take the most efficient route according to GPS. |  |
| FC-F03 | 3 | RYDE_POLICY | RYDE-4412122016153 | 2023-06-16 |  | VERIFIED | corpus body | So you may decide to take the fastest or most efficient route based on your GPS. |  |
| FC-F03 | 4 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  |  |
| FC-F03 | 5 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Requiring the trip's navigation record for the GPS justification, and not accepting the dr |
| FC-F03 | 6 | INDUSTRY | IND-DIDI-DETOUR | undated (read 2026-10-05) |  | VERIFIED | sources/research/09_fact_check.md | 司机采用 App 导航，导致的乘客投诉绕路，视为司机履约，不承担违约责任 |  |
| FC-F04 | 1 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | Please key in ERP based on the ERP gantry you passed during the journey. |  |
| FC-F04 | 2 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The fares for RydeSEND include ERP. |  |
| FC-F04 | 3 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The driver bears 50% of the ERP charge, and the passenger pays the remaining 50%. |  |
| FC-F05 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | before or at the point of deviation |  |
| FC-F05 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | A brief reason (e.g., "traffic jam ahead onNicoll Highway, taking alternate route") is sufficient. |  |
| FC-F05 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | If the driver's in-app chat or call recording confirms rider acknowledgment, the deviation is considered agree |  |
| FC-F05 | 4 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | The phrase-list stand-in for the reading, and counting a call as UNCLEAR, are FairRyde's i |
| FC-F06 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | for the route segment at the trip time. |  |
| FC-F06 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | traffic justification (no evidence of congestion) |  |
| FC-F06B | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Matching an incident to a route by name, direction and time, because the sample's incident |
| FC-F06B | 2 | ORGANIZER | ORG-DISP001 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp001.md | Vehicle fire on PIE eastbound between Paya Lebar and Hougang. | An incident record of the sample: road, direction and stretch by name. |
| FC-F07 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | binding at the surge multiplier in effect at quote time |  |
| FC-F07 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | calculated using actual distance, actual time, and the surge multiplier in effect at trip start |  |
| FC-F08 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | before or at the point of pickup. |  |
| FC-F08 | 2 | ORGANIZER | ORG-DISP003 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp003.md | "rider_notified": false | The platform's own record in DISP-003. |
| FC-R00 | 1 | RYDE_POLICY | RYDE-900003406966 | 2026-01-26 |  | VERIFIED | corpus body | Do note that all fees for Standard and/or Premium Taxi Services follow that of the respective taxi company. |  |
| FC-R00 | 2 | RYDE_POLICY | RYDE-900003406966 | 2026-01-26 |  | VERIFIED | corpus body | Please do note that the payment method accepted for RydeTAXI is only via cash. |  |
| FC-R00 | 3 | RYDE_POLICY | RYDE-900004230226 | 2026-01-26 |  | VERIFIED | corpus body | Key in the fare as indicated on your meter. |  |
| FC-R00 | 4 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | That no platform-computed refund applies and the case escalates is FairRyde's reading (fix |
| FC-R01 | 1 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | The trip fare is fixed based on pick-up and drop-off points, hence the driver may decide to take the most effi |  |
| FC-R01 | 2 | RYDE_POLICY | RYDE-30741244296217 | 2025-07-17 |  | VERIFIED | corpus body | Fares quoted for our services are generally fixed, except for RydeTAXI. | [clause is one side of a META-04 known conflict: does not count toward A] |
| FC-R01 | 3 | RYDE_POLICY | RYDE-360004075214 | 2024-10-08 |  | VERIFIED | corpus body | All fares are fixed at the time of booking but does not include toll charges such as ERP. |  |
| FC-R01 | 4 | RYDE_POLICY | RYDE-115000772653 | 2024-04-19 |  | VERIFIED | corpus body | For all services apart from RydeSEND, ERP charges are excluded from the fares. |  |
| FC-R01 | 5 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Recording the deviation as driver-conduct information only, and opening the FC-TOLL claim  |
| FC-R02 | 1 | RYDE_POLICY | RYDE-4412122016153 | 2023-06-16 |  | VERIFIED | corpus body | So you may decide to take the fastest or most efficient route based on your GPS. |  |
| FC-R02 | 2 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you g |  |
| FC-R02 | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Applying the GPS-route permission, which Ryde gives because the fare is fixed, to every fa |
| FC-R03 | 1 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  |  |
| FC-R03 | 2 | INDUSTRY | IND-DIDI-DETOUR | undated (read 2026-10-05) |  | VERIFIED | sources/research/09_fact_check.md | 实际行驶里程÷腾讯地图里程 ≥120% 且 绕路里程≥3 公里，则判定为绕路 |  |
| FC-R03 | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Applying the private-hire (PDVL) route duty to every driver of a recalculated fare, withou |
| FC-R04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| FC-R05 | 1 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | PARAPHRASE |  |  | DiDi charges only the estimated fare when a detour is found (research notes 02 and 08). |
| FC-R06 | 1 | RYDE_POLICY | RYDE-115000772653 | 2024-04-19 |  | VERIFIED | corpus body | If a rider passes through an active ERP gantry, the toll charge will be applicable to the rider. |  |
| FC-R06 | 2 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The fares for RydeFLASH / RydePET / RydeX / RydeXL / RydeLUXE / RydeTAXI exclude ERP. |  |
| FC-R06 | 3 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The fares for RydeSEND include ERP. |  |
| FC-R06 | 4 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The driver bears 50% of the ERP charge, and the passenger pays the remaining 50%. |  |
| FC-R06 | 5 | RYDE_POLICY | RYDE-33363192453785 | 2026-09-02 |  | VERIFIED | corpus body | The tolls for RydePOOL are split equally between riders for a shared trip, with each paying 50% of the total t | Not used to set a share: it documents why RydePOOL has none (it contradicts the 2023 pages |
| FC-R06 | 6 | RYDE_POLICY | RYDE-23575142762393 | 2023-10-02 |  | VERIFIED | corpus body | Note: RydePOOL, RydeHIRE and RydeSEND include ERP. | 2023 driver page, not used to set a share: it documents the disagreement for RydePOOL and  |
| FC-R07 | 1 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | Please key in ERP based on the ERP gantry you passed during the journey. |  |
| FC-R07 | 2 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | Please bear in mind that if an additional/excessive amount is keyed in, this will be considered fraudulent and |  |
| FC-R07 | 3 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The fares for RydeSEND include ERP. |  |
| FC-R07 | 4 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The driver bears 50% of the ERP charge, and the passenger pays the remaining 50%. |  |
| FC-R07 | 5 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | The refund of the difference is FairRyde's remedy (a recommendation under Ryde's discretio |
| FC-R08 | 1 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  | LTA's list is the PDVL (private-hire driver's vocational license) offense list as at 1 Apr |
| FC-R08 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Turning the route duty into an ERP refund, and escalating a metered fare instead (D32), ar |
| FC-R08 | 3 | ORGANIZER | ORG-DISP001 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp001.md | Only the excess distance fare is refunded. Tolls are passed through at cost. |  |
| FC-R09 | 1 | RYDE_POLICY | RYDE-51399796192921 | 2025-10-10 |  | VERIFIED | corpus body | If the driver accepts your edit destination request, a $3.00 add/edit destination fee will apply. |  |
| FC-R09 | 2 | RYDE_POLICY | RYDE-50798691815449 | 2025-10-09 |  | VERIFIED | corpus body | *RydePOOL, RydeTAXI & Multiple stop bookings are not allowed to make any changes in destination. |  |
| FC-R10 | 1 | RYDE_POLICY | RYDE-18230976652185 | 2025-12-03 |  | VERIFIED | corpus body | If you have been charged for a trip that you have not taken, kindly share the details with us to investigate t |  |
| FC-R10 | 2 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Drivers who are found to have overcharged riders or completed trips without the rider onboard may face account |  |
| FC-R11 | 1 | RYDE_POLICY | RYDE-22836370596377 | 2026-02-26 |  | VERIFIED | corpus body | *First Tier Platform Fee: $1.25 (including GST) for fares $18 and below. |  |
| FC-R11 | 2 | RYDE_POLICY | RYDE-22836370596377 | 2026-02-26 |  | VERIFIED | corpus body | *Second Tier Platform Fee: $1.47 (including GST) for fares above $18. |  |
| FC-R11 | 3 | RYDE_POLICY | RYDE-52594357168281 | 2025-11-23 |  | VERIFIED | corpus body | 1.96% + $0.24 for Local Visa, Mastercard, and Rydecoins |  |
| FC-R12 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| FC-R13 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Driver reroutes for traffic, rider informed and agrees / Yes / Yes / No refund |  |
| FC-R13 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Driver reroutes for traffic, rider **not** informed / No / Yes / Partial refund of excess distance fare |  |
| FC-R13 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Driver reroutes for traffic, rider not informed / No / No (≤ 1km) / No refund (within tolerance) |  |
| FC-R13 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Partial refund of excess distance fare. Rationale: Driver had valid traffic justification (confirmed via traff |  |
| FC-R13 | 5 | ORGANIZER | ORG-DISP001 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp001.md | Only the excess distance fare is refunded. Tolls are passed through at cost. | DISP-001's recommended ruling: the refund base is the excess distance fare, not the whole  |
| FC-R13 | 6 | ORGANIZER | ORG-DISP001 | 2026-09 | organizer_v2_1 | VERIFIED | sources/organizer/disp001.md | "excess_distance_fare": 3.44 |  |
| FC-R13B | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | / N/A / Yes / **Full refund** of excess distance fare |  |
| FC-R13B | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Reading 'Full refund of excess distance fare' as the same base as the partial refund, with |
| FC-R14 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Where the difference is attributable solely to a surge multiplier change (all other fare components unchanged) |  |
| FC-R14 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | from surge pricing and remain fixed regardless of multiplier: |  |
| FC-R15 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Surge increases, rider notified, rider proceeds / Yes / No refund |  |
| FC-R15 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Surge increases, rider **not** notified / No / **Full refund of the surge differential** (actual fare − quoted |  |
| FC-R15 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Surge decreases between quote and trip start / N/A / Lower fare applies automatically (rider benefits) |  |
| FC-R15 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Surge unchanged / N/A / Quoted fare applies |  |
| FC-R15 | 5 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Full refund of surge differential. Rationale: Per Section 3.3, if surge increases between quote and trip start |  |
| DM-R01 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | Your vehicle must be professionally cleaned within 24 hours from the incident |  |
| DM-R01 | 2 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | Submit your claim via the driver app within 48 hours from the affected trip |  |
| DM-R02 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | At least one photo must show the vehicle's car plate number to verify the vehicle |  |
| DM-R02 | 2 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | Authorised personnel's signature and company stamp |  |
| DM-R03 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | Vomit / Up to S$200 |  |
| DM-R03 | 2 | RYDE_POLICY | RYDE-900003466206 | 2026-04-08 |  | VERIFIED | corpus body | For example, a verified vomit incident may result in a cleaning fee of up to S$200. |  |
| DM-R04 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | Ryde reserves the sole discretion to approve, deny, and decide on a fair reimbursement amount. |  |
| DM-R05 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | You can appeal within 24 hours if you disagree with the outcome of your claim with any additional supporting e |  |
| DM-R06 | 1 | RYDE_POLICY | RYDE-900004381243 | 2026-04-09 |  | VERIFIED | corpus body | The reimbursement is guaranteed and is not dependent on the rider completing payment, as Ryde will manage the  |  |
| DM-R06 | 2 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 11. Repair and Cleaning Fees for Users (paragraph 2) | Ryde may, subject to verification under its Vehicle Contamination Policy, reimburse the driver for the applica |  |
| SE-R01 | 1 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Violations of these guidelines will result in immediate termination and legal action where applicable. |  |
| SE-R01 | 2 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| SE-R01 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | AI agents (Rider Advocate, Driver Advocate, Judge) **MAY** gather evidence, summarize accounts, and prepare ca |  |
| SE-R02 | 1 | RYDE_POLICY | RYDE-16925196526489 | 2023-04-26 |  | VERIFIED | corpus body | The driver may terminate a ride in progress if there is a safety concern or if the rider is violating the comm |  |
| SE-R02 | 2 | RYDE_POLICY | RYDE-16925196526489 | 2023-04-26 |  | VERIFIED | corpus body | This could include situations where the rider is verbally or physically abusive towards the driver, is intoxic |  |
| SE-R02 | 3 | RYDE_POLICY | RYDE-16925196526489 | 2023-04-26 |  | VERIFIED | corpus body | Additionally, a driver may also terminate a ride in progress if their vehicle breaks down or malfunctions, and |  |
| SE-R03 | 1 | RYDE_POLICY | RYDE-51812996696217 | 2025-10-24 |  | VERIFIED | corpus body | No. Ryde does not allow drivers to use IVRDs or dashcams at this time. |  |
| SE-R03 | 2 | RYDE_POLICY | RYDE-360036735393 | 2025-09-19 |  | VERIFIED | corpus body | Unauthorised installation of inward-facing IVRD/Dashcams may result in 21 demerit points and suspension from o |  |
| SE-R04 | 1 | RYDE_POLICY | RYDE-900003838386 | 2023-09-19 |  | VERIFIED | corpus body | Report to us swiftly via RydeHelp within 1 hour. |  |
| SE-R04 | 2 | RYDE_POLICY | RYDE-900003838386 | 2023-09-19 |  | VERIFIED | corpus body | Make a traffic accident report within 24 hours when an accident involves injury, death, pedestrian, cyclist, g |  |
| GEN-R01 | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Otherwise, you will not be charged the $6.61 Waiting Time Fee if any of the above are not fulfilled. | [clause is one side of a META-04 known conflict: does not count toward A] |
| GEN-R02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| GEN-R03 | 1 | GOV_GUIDANCE | GOV-PDPC-AI | 2024-03-01 |  | PARAPHRASE |  |  | PDPC AI Advisory Guidelines (1 Mar 2024) paras 9.9 to 9.11: using personal data such as di |
| GEN-R03 | 2 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model AI Governance Framework para 3.23 warns about bias and reinforcement bias from produ |
| GEN-R04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| GEN-R05 | 1 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Driver-partners will be given the opportunity to respond before final decisions are made, except in urgent or  |  |
| GEN-R06 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 28. Suspension and Termination; Modification of Platform Content (a)-(c) | modify, suspend or terminate operation of or access to the Platform, or any portion of the Platform (including | Account suspension is Ryde's power under the contract, not FairRyde's. |
| GEN-R06 | 2 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| GEN-R07 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 把规则库偷偷换成"通用预设规则"，会让人误以为系统读了合同 |  |
| GEN-R08 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Agents should search precedent rulings by dispute type and key facts, and cite the relevant precedent in their |  |
| GEN-R08 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | All AI agents must cite the applicable policy section in their ruling rationale. |  |
| GEN-R08 | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Aligned and distinguished by equal key factors is FairRyde's matching method; the policy o |
| FRD-01 | 1 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | 5. Remaining stationary and uncontactable after accepting a ride to trigger cancellation or waiting fees |  |
| FRD-01 | 2 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | 8. Abuse of Cancellation and Waiting Fee Policy |  |
| FRD-01 | 3 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Drivers who overcharge riders and/or complete the trip without the rider onboard. | Community standards, 'Fraudulent Activity': the basis for the signal on a charge the drive |
| FRD-02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| AUTH-00 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 7. Cancellation, 7.2 Cancellation Terms for Users (paragraph 3) | Ryde reserves its absolute discretion to any refunds to you |  |
| AUTH-01 | 1 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model AI Governance Framework (2nd ed.) paras 3.14 to 3.16: human-over-the-loop for low-se |
| AUTH-02 | 1 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| AUTH-03 | 1 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| AUTH-03 | 2 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Violations of these guidelines will result in immediate termination and legal action where applicable. | Sanctions are Ryde's (termination, legal action), so they are not FairRyde's to apply. |
| AUTH-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| AUTH-05 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Weights, margin scale and penalty are to be calibrated on the dev set. The 4 Oct report us |
| AUTH-06 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | One tier per outcome, so annotators and reviewers get one answer (second independent revie |
| AUTH-07 | 1 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Under $10 / AI agent ruling is **final** / Any confidence level |  |
| AUTH-07 | 2 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | $10 - $50 / AI agent ruling with **80%+ confidence** / If confidence < 80%, escalate to human review |  |
| AUTH-07 | 3 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Above $50 / **Always human review** / N/A - AI agent prepares case file only |  |
| AUTH-07 | 4 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | Route deviation / AI agent ruling if confidence ≥ 80% and deviation ≤ 2km, else escalate |  |
| AUTH-07 | 5 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | No-show / cancellation / AI agent ruling is final (fee is fixed at $5.00) |  |
| AUTH-07 | 6 | ORGANIZER | ORG-POLICY-V21 | 2026-01-01 | organizer_v2_1 | VERIFIED | sources/organizer/policy_v2.1.md | If any party has a fraud flag ≥ 1, the confidence threshold is raised to 95% regardless of dispute value. |  |
| AUTH-07 | 7 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Mapping the policy's ruling paths to the three tiers, keeping FairRyde's other approval tr |
| EXP-01 | 1 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model Framework paras 3.48, 3.51 and 3.54 (explanations and requests for review); PDPC AI  |
| EXP-01 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | The content list (which rules decided the outcome, two to four decisive evidence items, mi |
| EXP-02 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 分"可以写死的规则"和"必须回头读原文的规则" |  |
| EXP-03 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |

## Credibility review

| rule | type | credibility | mode | weakest essential parameter | source types | note |
|---|---|---|---|---|---|---|
| META-01 | meta | D | HARD | D | FAIRRYDE, ORGANIZER |  |
| META-02 | meta | D | HARD |  | RYDE_POLICY | Ryde states effective dates (A); choosing parameters by trip date is FairRyde's rule (D). |
| META-03 | meta | A | HARD |  | RYDE_TOU |  |
| META-04 | meta | D | HARD |  | FAIRRYDE |  |
| META-05 | meta | A | HARD |  | INTERNAL_STANDARD |  |
| CLS-01 | classification | D | READ |  | FAIRRYDE, INDUSTRY, ORGANIZER, RYDE_POLICY | The conduct norm is Ryde's (A); handling safety content as its own claim is industry practice (C), and a human decides i |
| CLS-02 | classification | D | HARD |  | INTERNAL_STANDARD | The protocol names the pitfall (A); the ordering of primary and secondary claims is FairRyde's design (D). |
| CLS-03 | classification | D | HARD |  | FAIRRYDE |  |
| CLS-04 | classification | D | HARD |  | FAIRRYDE |  |
| CLS-05 | classification | A | HARD |  | ORGANIZER |  |
| CLS-06 | classification | D | HARD |  | FAIRRYDE, ORGANIZER, RYDE_POLICY | Ryde's policy distinguishes a rider cancellation from a driver's no-show cancellation (A); using the records, not the te |
| MAT-01 | matching | D | HARD |  | INTERNAL_STANDARD |  |
| MAT-02 | matching | D | HARD |  | INTERNAL_STANDARD, RYDE_POLICY |  |
| MAT-03 | procedural | D | HARD |  | GOV_GUIDANCE, RYDE_POLICY | Checkpoints are official guidance (B) and Ryde has appeal routes (A); sending every appeal of an automatic ruling to a h |
| MAT-04 | eligibility | A | HARD | A | RYDE_POLICY |  |
| DQ-01 | data_quality | D | HARD | D | FAIRRYDE |  |
| DQ-02 | data_quality | D | HARD | D | FAIRRYDE |  |
| DQ-03 | data_quality | D | HARD | D | FAIRRYDE |  |
| DQ-04 | data_quality | D | HARD |  | FAIRRYDE |  |
| DQ-05 | data_quality | D | HARD | D | RYDE_POLICY | Ryde says the receipt lists all components (A); the S$0.01 tolerance is FairRyde's (D). |
| DQ-06 | data_quality | D | HARD | D | ORGANIZER, RYDE_POLICY | The policy amounts are A; treating a mismatch as a reason to escalate is FairRyde's choice (D). |
| CW-F01 | fact | D | HARD | D | ORGANIZER |  |
| CW-F02 | fact | A | HARD | A | ORGANIZER, RYDE_POLICY |  |
| CW-F02B | fact | C | HARD |  | INDUSTRY, RYDE_POLICY |  |
| CW-F02C | fact | D | HARD | A | ORGANIZER | The wait start at the scheduled pickup time is the organizer's (Section 2.1, A). Counting from the driver's arrival when |
| CW-F03 | fact | A | HARD | A | ORGANIZER, RYDE_POLICY | Threshold and comparison are A; the 30 s boundary band is a FairRyde parameter (D) that only adds a flag. |
| CW-F03B | fact | D | HARD |  | FAIRRYDE, RYDE_POLICY | The GPS condition is Ryde text (B, see CW-R06); where the wait starts when that condition fails is FairRyde's inference, |
| CW-F04 | fact | B | HARD |  | ORGANIZER, RYDE_POLICY | The GPS condition is in a Ryde rider article whose wording about the fee name conflicts with the main policy page (META- |
| CW-F04B | fact | D | HARD | D | FAIRRYDE, RYDE_POLICY | FairRyde's design (D): Ryde does not say how GPS presence at the pick-up is checked (radius, ping gap, outliers). The ra |
| CW-F05 | fact | D | HARD | D | INDUSTRY, ORGANIZER, RYDE_POLICY | Ryde's driver guidance (an older article) asks drivers to try to contact the rider (B); the minimum counts are FairRyde  |
| CW-F06 | fact | D | HARD+READ | D | FAIRRYDE | FairRyde's design (D). Until v0.1 any rider call or message during the wait was STRONG whatever it said, which sent rout |
| CW-F07 | fact | D | HARD | D | RYDE_TOU | The 'designated location' concept is contractual (A); the 200 m threshold is FairRyde's (D). |
| CW-R00 | eligibility | B | HARD |  | RYDE_POLICY | Ryde text edited 2024-03-18 (older than 12 months). |
| CW-R01 | eligibility | A | HARD | A | RYDE_POLICY |  |
| CW-R02 | eligibility | A | HARD | A | RYDE_POLICY |  |
| CW-R03 | outcome | A | HARD | A | ORGANIZER, RYDE_POLICY |  |
| CW-R04 | procedural | D | HARD |  | RYDE_POLICY | Ryde's driver guidance expects a contact attempt before canceling (B, older article); making its absence a reason for hu |
| CW-R05 | outcome | A | HARD | A | RYDE_POLICY |  |
| CW-R06 | eligibility | B | HARD | D | ORGANIZER, RYDE_POLICY | The article calls the S$6.61 charge a "Waiting Time Fee", while the main policy page calls S$6.61 the Cancellation Fee ( |
| CW-R07 | outcome | A | HARD | A | RYDE_POLICY |  |
| CW-R08 | eligibility | D | HARD | C | FAIRRYDE, INDUSTRY, ORGANIZER | The late-driver waiver is other platforms' practice (C). The 'not moving toward the pick-up point' ground has no source  |
| CW-R09 | remedy | A | HARD | A | ORGANIZER, RYDE_POLICY | Under ryde_2026 the rider pays S$6.61 (S$5.00 base + S$1.25 platform fee + S$0.36 transaction fee, reference table CANCE |
| CW-R10 | remedy | A | HARD | D | ORGANIZER, RYDE_POLICY | For organizer cases the voucher form is assumed (D) because the organizer data does not say how refunds are paid. |
| CW-R11 | procedural | D | HARD | D | FAIRRYDE, RYDE_TOU |  |
| CW-R12 | outcome | D | HARD |  | FAIRRYDE |  |
| CW-R13 | outcome | D | HARD+READ | D | FAIRRYDE, ORGANIZER | The obligation, the voiding and the refund are the organizer's (A). The sentence 'fails to meet both contact obligations |
| CW-R14 | outcome | A | HARD | C | ORGANIZER | The grace of 300 s and the S$5.00 credit are the organizer's (A, profile organizer_v2_1). DRIVER_LATE_GRACE_S is rated C |
| FC-F01 | fact | B | HARD |  | RYDE_POLICY | 'Fares are fixed' comes from rider articles edited more than 12 months ago, and a driver FAQ describes earnings from dri |
| FC-F02 | fact | D | HARD | D | FAIRRYDE, ORGANIZER, RYDE_POLICY |  |
| FC-F03 | fact | D | READ |  | FAIRRYDE, INDUSTRY, REGULATION, RYDE_POLICY | Rider agreement and the GPS most-efficient route are Ryde text, but both route articles were edited more than 12 months  |
| FC-F04 | fact | A | HARD | A | RYDE_POLICY | The gantry sum and both exceptions are Ryde text in a driver article edited 2026-09-02 (A). The order of application is  |
| FC-F05 | fact | D | READ |  | FAIRRYDE, ORGANIZER | The duty, the timing, the reason and the agreement test are the organizer's text (A). The point of deviation (the first  |
| FC-F06 | fact | D | HARD |  | ORGANIZER | That a traffic incident justifies a reroute is the organizer's (Section 1.4, A). Treating a case with no traffic data at |
| FC-F06B | fact | D | HARD+READ |  | FAIRRYDE, ORGANIZER | The data and the need for it are the organizer's (A, FC-F06); locating an incident on the route by name, direction and t |
| FC-F07 | fact | A | HARD |  | ORGANIZER |  |
| FC-F08 | fact | A | HARD |  | ORGANIZER | The duty, its timing and the in-app channel are the organizer's text (A). Checking the notice's content is not possible  |
| FC-R00 | eligibility | D | HARD | C | FAIRRYDE, RYDE_POLICY | The RydeTAXI facts are Ryde text (rider and driver articles edited 2026-01-26, A). Excluding metered fares from a platfo |
| FC-R01 | outcome | B | HARD |  | FAIRRYDE, RYDE_POLICY | Both rider articles were edited more than 12 months ago (2024-10-01, 2025-07-17), and the article saying fixed fares exc |
| FC-R02 | eligibility | D | READ |  | FAIRRYDE, RYDE_POLICY | Both articles were edited more than 12 months ago (2023-06-16, 2024-10-01), so Ryde's text is B. Both give the permissio |
| FC-R03 | outcome | D | HARD+READ | C | FAIRRYDE, INDUSTRY, REGULATION | The duty to take the shortest route is in Singapore regulation (B), verified for private-hire (PDVL) drivers only (the t |
| FC-R04 | outcome | D | HARD | D | FAIRRYDE |  |
| FC-R05 | remedy | D | HARD | D | INDUSTRY |  |
| FC-R06 | eligibility | A | HARD | A | RYDE_POLICY | Every share is Ryde text in a driver article edited 2026-09-02 (A). The order of application, the default for an unrecor |
| FC-R07 | outcome | D | HARD+READ | D | FAIRRYDE, RYDE_POLICY | The overstatement rule and its fraud consequence are Ryde's (A), with the rider's share from FC-R06 (A). Refunding the d |
| FC-R08 | outcome | D | HARD+READ | D | FAIRRYDE, ORGANIZER, REGULATION | The route duty is regulatory (B) and verified for PDVL drivers only; turning it into a platform-computed ERP refund is F |
| FC-R09 | eligibility | A | HARD | A | RYDE_POLICY |  |
| FC-R10 | outcome | D | HARD+READ |  | RYDE_POLICY | Investigation and sanctions are Ryde's (A); the full-refund remedy is FairRyde's inference (D). |
| FC-R11 | remedy | A | HARD | A | RYDE_POLICY |  |
| FC-R12 | outcome | D | HARD |  | FAIRRYDE |  |
| FC-R13 | outcome | A | HARD | D | ORGANIZER | Rows (1), (2) except its amount, (3) and (4) are the organizer's matrix (A), and the refund base follows DISP-001 and Pr |
| FC-R13B | outcome | D | HARD |  | FAIRRYDE, ORGANIZER | The outcome word (a full refund) is the organizer's; what 'full' covers is ambiguous and FairRyde's reading decides the  |
| FC-R14 | fact | A | HARD | D | ORGANIZER | The rule and its test are the organizer's (A); the S$0.01 rounding tolerance only absorbs cents (MONEY_TOLERANCE_SGD, D) |
| FC-R15 | outcome | A | HARD | D | ORGANIZER | The table of Section 3.3 and the amount are the organizer's (A). MONEY_TOLERANCE_SGD (D) only absorbs cents, and REMEDY_ |
| DM-R01 | eligibility | A | HARD | A | RYDE_POLICY |  |
| DM-R02 | eligibility | A | HARD |  | RYDE_POLICY |  |
| DM-R03 | remedy | A | HARD+READ | A | RYDE_POLICY |  |
| DM-R04 | authority | A | READ |  | RYDE_POLICY |  |
| DM-R05 | procedural | A | HARD | A | RYDE_POLICY |  |
| DM-R06 | remedy | A | HARD |  | RYDE_POLICY, RYDE_TOU |  |
| SE-R01 | authority | D | HARD |  | GOV_GUIDANCE, ORGANIZER, RYDE_POLICY | That a human decides is official guidance (B) and sanctions are Ryde's (B); the triage steps (preserve and hash evidence |
| SE-R02 | eligibility | B | READ |  | RYDE_POLICY | Every element is in one Ryde rider article edited 2023-04-26 (older than 12 months), so B. |
| SE-R03 | eligibility | A | HARD |  | RYDE_POLICY |  |
| SE-R04 | procedural | B | READ | B | RYDE_POLICY | Both reporting duties are in one Ryde driver article edited 2023-09-19 (older than 12 months), so B; routing accidents t |
| GEN-R01 | procedural | D | HARD |  | RYDE_POLICY | Ryde's 'conditions must be fulfilled' wording supports it (A); generalizing it to all charges is FairRyde's (D). |
| GEN-R02 | procedural | D | HARD |  | FAIRRYDE |  |
| GEN-R03 | procedural | D | HARD |  | GOV_GUIDANCE | The guidance supports disclosure and caution (B); that history never decides an outcome is FairRyde's design (D). |
| GEN-R04 | procedural | D | HARD |  | FAIRRYDE |  |
| GEN-R05 | procedural | D | READ |  | RYDE_POLICY | Ryde's sentence sits in its misconduct section ("Ryde is committed to investigating all reports of misconduct fairly and |
| GEN-R06 | authority | B | HARD |  | GOV_GUIDANCE, RYDE_TOU |  |
| GEN-R07 | procedural | D | HARD |  | INTERNAL_STANDARD | The protocol names the risk (A); escalating as the response is FairRyde's design (D). |
| GEN-R08 | procedural | D | HARD |  | FAIRRYDE, ORGANIZER | The duty to search and cite is the organizer's (A); how a precedent is matched (equal key factors) is FairRyde's (D). |
| FRD-01 | fraud | D | READ | D | RYDE_POLICY | Ryde defines the prohibited behavior (A). The detection signals (arrival marked without GPS presence, repeated no-shows  |
| FRD-02 | fraud | D | HARD | D | FAIRRYDE |  |
| AUTH-00 | authority | A | READ |  | RYDE_TOU |  |
| AUTH-01 | authority | D | HARD | D | GOV_GUIDANCE |  |
| AUTH-02 | authority | D | HARD | D | GOV_GUIDANCE | The checkpoint principle is official guidance (B); the list of triggers is FairRyde's design (D). Triggers can only send |
| AUTH-03 | authority | B | HARD |  | GOV_GUIDANCE, RYDE_POLICY |  |
| AUTH-04 | authority | D | HARD | D | FAIRRYDE |  |
| AUTH-05 | authority | D | HARD | D | FAIRRYDE |  |
| AUTH-06 | authority | D | HARD |  | FAIRRYDE |  |
| AUTH-07 | authority | D | HARD | D | FAIRRYDE, ORGANIZER | The thresholds and the fraud-flag rule are the organizer's (A). Reading 'escalate to human review' as tier APPROVE or HU |
| EXP-01 | explanation | D | HARD |  | FAIRRYDE, GOV_GUIDANCE | Official guidance (B) asks for explanations and a way to request a review; the specific content list and the 30-day posi |
| EXP-02 | explanation | A | HARD |  | INTERNAL_STANDARD |  |
| EXP-03 | explanation | D | HARD |  | FAIRRYDE |  |
