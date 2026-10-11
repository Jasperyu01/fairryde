# FairRyde knowledge base v0.1: check report

Generated from the YAML source files (knowledge base dated 2026-10-05).

* Rules: 88; vocabularies: 22; TX-CASE leaves: 33; entities: 20; events: 35; playbooks: 11
* Rule sources: 143; VERIFIED 113, NO_QUOTE (design assumption) 23, PARAPHRASE 7
* Credibility: A 27, B 11, C 6, D 44; modes: HARD 74, HARD+READ 6, READ 8
* DISP-002 fields mapped: 59 of 59 leaf paths
* DT-CW-NOSHOW enumeration: {'combinations': 96, 'unique': 96, 'gaps': 0, 'overlaps': 0}
* State machines: {'SM-TRIP': {'states': 12, 'reachable': 12, 'terminal': ['CANCELLED_BY_DRIVER', 'CANCELLED_BY_RIDER', 'CANCELLED_NO_SHOW', 'COMPLETED', 'TERMINATED_MID_TRIP']}, 'SM-CHARGE': {'states': 7, 'reachable': 7, 'terminal': []}, 'SM-TICKET': {'states': 8, 'reachable': 8, 'terminal': ['MERGED']}, 'SM-RULING': {'states': 5, 'reachable': 5, 'terminal': []}}
* Engine self-test: 79/79 variants pass
* Privacy dry run on DISP-002 (counts only): before {'PERSON_NAME': 3, 'PERSON_NAME_TOKEN': 8, 'VEHICLE_PLATE': 3, 'SG_PLATE': 3, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'LONG_NUMBER': 0}; after {'PERSON_NAME': 0, 'PERSON_NAME_TOKEN': 0, 'VEHICLE_PLATE': 0, 'SG_PLATE': 0, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'LONG_NUMBER': 0}; fragments after 0; clean True
* Leak scan of generated outputs (counts only): {'PERSON_NAME': 0, 'PERSON_NAME_TOKEN': 0, 'VEHICLE_PLATE': 0, 'SG_PLATE': 0, 'PHONE': 0, 'EMAIL': 0, 'NRIC_FIN': 0, 'UNIT_NUMBER': 0, 'LONG_NUMBER': 0, 'NAME_FRAGMENTS': 0, 'total': 0}
* Annotation workbook: workbooks skipped (--no-xlsx)
* Issues: ERROR 0, WARN 0, INFO 5

* DISP-002 under organizer_case: **UPHOLD** (row R8), reasons CW-R-NOSHOW-VALID, CW-R-PIN-AMBIGUOUS, flags BOOKING_TYPE_INFERRED, BOUNDARY_MARGIN, MARGIN_WITHIN_SPREAD, NO_RIDER_EVIDENCE, PIN_VENUE_MISMATCH, FRAUD_SIGNAL, GENERIC_ASSUMPTION_USED, confidence 0.689, tier **APPROVE**
* DISP-002 under ryde_2026: **UPHOLD** (row R8), reasons CW-R-NOSHOW-VALID, CW-R-PIN-AMBIGUOUS, flags BOOKING_TYPE_INFERRED, NO_RIDER_EVIDENCE, PIN_VENUE_MISMATCH, CHARGE_AMOUNT_MISMATCH, FRAUD_SIGNAL, GENERIC_ASSUMPTION_USED, confidence 0.939, tier **APPROVE**

## Issues

| level | check | item | message |
|---|---|---|---|
| INFO | rule-credibility | CW-F04 | rated B but essential parameter(s) are D: ARRIVAL_GEOFENCE_M=D, PING_MAX_GAP_S=D, LEFT_MIN_OUTSIDE_S=D, SPEED_MAX_KMH=D, TS_TOLERANCE_S=D |
| INFO | rule-credibility | CW-R06 | rated B but essential parameter(s) are D: ARRIVAL_GEOFENCE_M=D, TS_TOLERANCE_S=D, PING_MAX_GAP_S=D, LEFT_MIN_OUTSIDE_S=D, SPEED_MAX_KMH=D |
| INFO | rule-credibility | CW-R10 | rated A but essential parameter(s) are D: REMEDY_FORM=D |
| INFO | rule-credibility | FC-R07 | rated A but essential parameter(s) are D: TOLL_TOLERANCE_SGD=D |
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
| V04F | platform GPS check says arrived; a single ping at that second is 300 m away, then the driver is at the pin | UPHOLD | R8 | APPROVE | 0.664 | pass |
| V04C | no platform GPS check and no driver pings from arrival on | WAIVE_FEE | R3 | APPROVE | 0.654 | pass |
| V04D | platform GPS check present, no driver pings during the wait | WAIVE_FEE | R5 | APPROVE | 0.654 | pass |
| V05 | rider GPS trace at the OneMap venue during the wait | ESCALATE_HUMAN | R7 | HUMAN | 0.725 | pass |
| V06 | clean baseline: pin at the venue, pings every 30 s, cancel at 08:52, rider without history | UPHOLD | R8 | AUTO | 0.964 | pass |
| V07 | only two driver pings, 8 minutes apart (rider contests) | ESCALATE_HUMAN | R10 | HUMAN | 0.664 | pass |
| V08 | as V07, and the rider's statement does not contest presence, timing or place | UPHOLD | R9 | APPROVE | 0.7 | pass |
| V10 | trip canceled for another reason (rider_cancelled) | None | None | n/a (reclassified to CW-RIDERCANCEL) | None | pass |
| V11 | V06, and the driver made no call and sent no message | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V12 | instruction injected in the rider's description | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V13 | safety language in the description | UPHOLD | R8 | HUMAN | 0.689 | pass |
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
| V25 | V06 with one driver ping 150 m away in the middle of the wait (a GPS outlier) | UPHOLD | R8 | AUTO | 0.939 | pass |
| V26 | V06, and the driver (who benefits) injected an instruction in a chat message | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V27 | V06 with the cancellation 1 s after the threshold and all records agreeing | UPHOLD | R8 | AUTO | 0.718 | pass |
| V28 | V06 with the cancellation 1 s before the threshold and all records agreeing | WAIVE_FEE | R6 | AUTO | 0.718 | pass |
| V29 | the case's policy object has no no-show threshold: Ryde's 3 minutes apply (META-01 fallback) | UPHOLD | R8 | APPROVE | 0.939 | pass |
| V30-1 | DISP-002 with the GPS array shuffled (seed 1): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V30-2 | DISP-002 with the GPS array shuffled (seed 2): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V30-3 | DISP-002 with the GPS array shuffled (seed 3): the outcome must not depend on array order | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V31 | only one ping inside the wait, 150 m out; pings at the pin 20 s before arrival and 20 s after the cancellation | ESCALATE_HUMAN | R10 | HUMAN | 0.639 | pass |
| V32 | V06 with pings every 5 s and a 10-second jump to 150 m (three pings): a GPS outlier, not a departure | UPHOLD | R8 | AUTO | 0.939 | pass |
| V33 | as V32 but the jump is 400 m (implied 288 km/h): a data error, set aside, gate G1 | UPHOLD | R8 | APPROVE | 0.939 | pass |
| V34 | V06, but the driver drives off at 08:51:15, after the 8-minute threshold, and cancels at 08:52 | UPHOLD | R8 | AUTO | 0.964 | pass |
| V35 | Ryde advance booking for 08:45: driver at the pin from 08:38, 150 m away for 45 s at 08:45, then waiting 4 min 15 s | UPHOLD | R8 | APPROVE | 0.914 | pass |
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
| V48 | DISP-002 with the last ping (08:51:00, at the cancellation) 60 m from the pin and no ping after it: not a departure | UPHOLD | R8 | APPROVE | 0.689 | pass |
| V49 | V06, but the driver is 400 m away from 08:50:30, 30 s before the threshold, and never comes back: leaving counts | WAIVE_FEE | R4 | APPROVE | 1.0 | pass |
| V50 | Ryde on-demand trip (more than 180 s): at the pin until 08:45, 400 m away at 08:46:00 (the threshold moment) and never back | UPHOLD | R8 | APPROVE | 0.881 | pass |
| V51 | V06 with pings every 120 s and one 400 m away at 08:47: set aside as an outlier, but the driver may have been away 240 s | UPHOLD | R8 | APPROVE | 0.975 | pass |
| V52 | V06 with pings every 120 s: away from 08:50:45 (within 30 s of the threshold) until after the cancellation, then back | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V53 | Ryde advance booking for 08:45: away from 08:44:50 to 08:47:40 with no ping in between, back at 08:49: the driver missed the wait | WAIVE_FEE | R4 | APPROVE | 0.939 | pass |
| V54 | V06 at the pin every 20 s until 08:50:20, one ping 100 m out at 08:51:10 (just after the threshold), back at 08:51:30 | UPHOLD | R8 | APPROVE | 1.0 | pass |
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
| V69 | V06, and the rider messages 'I'm at the lobby already' at 08:41, after the assignment and before the arrival (D30): approval | UPHOLD | R8 | APPROVE | 0.964 | pass |
| V70 | V06, and the rider asks 'where are you?' at 08:41, before the driver arrived: not counter-evidence | UPHOLD | R8 | AUTO | 0.964 | pass |
| V71 | V06, and rider GPS at the pick-up at 08:41:30, before the arrival indication (D30): approval | UPHOLD | R8 | APPROVE | 1.0 | pass |
| V72 | V08 (sparse driver GPS, statement not contesting), and the rider says 'I'm here at the pick-up point' before the arrival (D30) | ESCALATE_HUMAN | R10 | HUMAN | 0.7 | pass |
| V73 | V06, and the rider says 'I'm at the lobby already' at 08:30:05, before the driver was assigned (08:30:15): not counted | UPHOLD | R8 | AUTO | 0.964 | pass |

## Entity coverage (ONT.6)

| entity | name | kind | covered by | status |
|---|---|---|---|---|
| ENT-ACCOUNT | Account | business | DISP-002 | ok (from the case file) |
| ENT-DISPUTEHISTORY | DisputeHistory | value_object | DISP-002 | ok (from the case file) |
| ENT-VEHICLE | Vehicle | business | DISP-002 | ok (from the case file) |
| ENT-PLATFORM | Platform (Ryde) | business | every case | ok |
| ENT-TRIP | Trip | business | DISP-002 | ok (from the case file) |
| ENT-PLACE | Place | business | DISP-002 | ok (from the case file) |
| ENT-EVENT | TripEvent | business | DISP-002 | ok (from the case file) |
| ENT-GPSPING | GPSPing | business | DISP-002 | ok (from the case file) |
| ENT-COMM | Communication | business | DISP-002 | ok (from the case file) |
| ENT-CHARGE | Charge | business | DISP-002 | ok (from the case file) |
| ENT-POLICYDOC | PolicyDocument | business | DISP-002 | ok (from the case file) |
| ENT-CLAUSE | PolicyClause | business | DISP-002 | ok (from the case file) |
| ENT-TICKET | DisputeTicket | case | DISP-002 | ok (from the case file) |
| ENT-CLAIM | Claim | case |  | created by the pipeline for every case |
| ENT-EVIDENCE | EvidenceItem | case |  | created by the pipeline for every case |
| ENT-FINDING | Finding | case |  | created by the pipeline for every case |
| ENT-RULING | Ruling | case |  | created by the pipeline for every case |
| ENT-REVIEW | HumanReview | case |  | created when a person reviews a ruling (APPROVE and HUMAN tiers) |
| ENT-PRECEDENT | Precedent | case |  | created only from human-reviewed rulings |
| ENT-ARGUMENT | Argument | system_artifact |  | created by the pipeline for every case |

## Rule sources and quote verification

| rule | # | type | doc | doc date | profile | status | where | quote | note |
|---|---|---|---|---|---|---|---|---|---|
| META-01 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Organizer cases are scored against the organizer's expected ruling, computed under the emb |
| META-02 | 1 | RYDE_POLICY | RYDE-18229758389017 | 2026-02-26 |  | VERIFIED | corpus body | The increase is due to the platform fee changes effective 17 Feb 2026. |  |
| META-03 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 1. Introduction | These Terms of Service and the Ryde Policies (as defined below) constitute a legally binding agreement ("Agree |  |
| META-03 | 2 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 2. Definitions ("Ryde Policies") | frequently asked questions (FAQs), in-app or website product/service descriptions and information cards |  |
| META-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| META-05 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 用行业通用规则先顶上，并显式标注来源为'通用假设' |  |
| META-05 | 2 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 会让人误以为系统读了合同 |  |
| CLS-01 | 1 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | We have a zero-tolerance approach to any form of misconduct or inappropriate behavior between drivers and pass |  |
| CLS-01 | 2 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | PARAPHRASE |  |  | Lyft, Grab and DiDi route safety incidents to humans (research note 02). |
| CLS-02 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 一封邮件/单据涉及多个事件，只选一个会丢信息，全多选又没主次 |  |
| CLS-03 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| CLS-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| CLS-05 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | "dispute_type": "no_show_charge" |  |
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
| CW-F01 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | Scheduled pickup 08:45. | DISP-002 says 'Scheduled pickup' yet assigns in 15 s with a 13-minute ETA; booking type is |
| CW-F02 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "driver_wait_start": "2026-09-13T08:43:00+08:00" |  |
| CW-F02 | 2 | RYDE_POLICY | RYDE-23534478435353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | waits for > 3 minutes for the rider to arrive at the pick-up point and cancels the trip (Rider NO SHOW and no  |  |
| CW-F02B | 1 | INDUSTRY | IND-GRAB-ADVANCE | read 2026-10-05 |  | VERIFIED | sources/research/09_fact_check.md | Your driver will arrive early and wait for you for up to 15 minutes starting from the indicated pickup time. |  |
| CW-F02B | 2 | INDUSTRY | IND-BOLT-SCHEDULED | read 2026-10-05 |  | VERIFIED | sources/research/09_fact_check.md | The scheduled wait time of 5 minutes will be counted only from the scheduled start of the ride. |  |
| CW-F02B | 3 | RYDE_POLICY | RYDE-23575142762393 | 2023-10-02 |  | VERIFIED | corpus body | You arrived at the pickup location and the customer was not present within 3 minutes of your arrival. | Driver article (2023), not specific to advance bookings; conflicts with the rule above for |
| CW-F03 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | No-show threshold (8 min) reached. | Logged at exactly 8:00 after driver_wait_start, so the organizer counts 'at least 8 minute |
| CW-F03 | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 | ryde_2026 | VERIFIED | corpus body | Has waited for more than 3 mins |  |
| CW-F03B | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Drivers are only allowed to indicate arrival and impose the Waiting Time Fee only if he/she: |  |
| CW-F03B | 2 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data |  |
| CW-F03B | 3 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Where the wait starts when GPS confirms the driver only after the arrival indication is Fa |
| CW-F04 | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Is at the pick-up location according to GPS data |  |
| CW-F04 | 2 | ORGANIZER | ORG-DISP002 | 2026-09 |  | VERIFIED | sources/organizer/disp002.md | Driver GPS within 10m of pickup point. | The organizer's system uses 10 m for auto-arrival; FairRyde uses a wider radius for presen |
| CW-F05 | 1 | RYDE_POLICY | RYDE-115001438754 | 2021-09-20 |  | VERIFIED | corpus body | Try to contact the rider by in-app chat or call. |  |
| CW-F05 | 2 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | VERIFIED | sources/research/02_industry_dispute_benchmark.md | Attempted to contact you (or you contacted them) | Lyft's no-show conditions (research note 02). |
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
| CW-R09 | 1 | ORGANIZER | ORG-DISP002 | 2026-09 | organizer_case | VERIFIED | sources/organizer/disp002.md | "fee_goes_to": "driver_compensation" |  |
| CW-R09 | 2 | RYDE_POLICY | RYDE-4407761228825 | 2023-04-11 | ryde_2026 | VERIFIED | corpus body | Cancellation Fees compensate drivers for the time and effort they spend getting to your location. |  |
| CW-R09 | 3 | RYDE_POLICY | RYDE-4408070838297 | 2026-09-25 | ryde_2026 | VERIFIED | corpus body | Drivers will receive a $4.50 cancellation fee automatically if they cancel after >3 minutes of waiting. |  |
| CW-R10 | 1 | RYDE_POLICY | RYDE-18229758389017 | 2026-02-26 |  | VERIFIED | corpus body | If you are eligible, we will issue you a voucher** with a unique code worth $6.61 as a refund for the incurred |  |
| CW-R10 | 2 | RYDE_POLICY | RYDE-27085468660505 | 2026-09-25 |  | VERIFIED | corpus body | If you are eligible, we will issue you a voucher** with a unique code worth $5.00 as a refund for the incurred |  |
| CW-R11 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 7. Cancellation, 7.2 Cancellation Terms for Users (paragraph 2) | If you decide to cancel your ride booking or do not show up at the designated location, you may be charged a C |  |
| CW-R11 | 2 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Approval trigger and goodwill option are FairRyde's design (D5). |
| CW-R12 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| FC-F01 | 1 | RYDE_POLICY | RYDE-30741244296217 | 2025-07-17 |  | VERIFIED | corpus body | Fares quoted for our services are generally fixed, except for RydeTAXI. | [clause is one side of a META-04 known conflict: does not count toward A] |
| FC-F01 | 2 | RYDE_POLICY | RYDE-360004075214 | 2024-10-08 |  | VERIFIED | corpus body | All fares are fixed at the time of booking but does not include toll charges such as ERP. |  |
| FC-F01 | 3 | RYDE_POLICY | RYDE-51399796192921 | 2025-10-10 |  | VERIFIED | corpus body | If the driver accepts your edit destination request, a $3.00 add/edit destination fee will apply. |  |
| FC-F02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Method from research note 08 (sparse-ping simulation). |
| FC-F03 | 1 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you g |  |
| FC-F03 | 2 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  |  |
| FC-F03 | 3 | INDUSTRY | IND-DIDI-DETOUR | undated (read 2026-10-05) |  | VERIFIED | sources/research/09_fact_check.md | 司机采用 App 导航，导致的乘客投诉绕路，视为司机履约，不承担违约责任 |  |
| FC-F04 | 1 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | Please key in ERP based on the ERP gantry you passed during the journey. |  |
| FC-R00 | 1 | RYDE_POLICY | RYDE-900003406966 | 2026-01-26 |  | VERIFIED | corpus body | Do note that all fees for Standard and/or Premium Taxi Services follow that of the respective taxi company. |  |
| FC-R00 | 2 | RYDE_POLICY | RYDE-900003406966 | 2026-01-26 |  | VERIFIED | corpus body | Please do note that the payment method accepted for RydeTAXI is only via cash. |  |
| FC-R00 | 3 | RYDE_POLICY | RYDE-900004230226 | 2026-01-26 |  | VERIFIED | corpus body | Key in the fare as indicated on your meter. |  |
| FC-R00 | 4 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | That no platform-computed refund applies and the case escalates is FairRyde's reading (fix |
| FC-R01 | 1 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | The trip fare is fixed based on pick-up and drop-off points, hence the driver may decide to take the most effi |  |
| FC-R01 | 2 | RYDE_POLICY | RYDE-30741244296217 | 2025-07-17 |  | VERIFIED | corpus body | Fares quoted for our services are generally fixed, except for RydeTAXI. | [clause is one side of a META-04 known conflict: does not count toward A] |
| FC-R02 | 1 | RYDE_POLICY | RYDE-4412122016153 | 2023-06-16 |  | VERIFIED | corpus body | So you may decide to take the fastest or most efficient route based on your GPS. |  |
| FC-R02 | 2 | RYDE_POLICY | RYDE-4412121982745 | 2024-10-01 |  | VERIFIED | corpus body | If you have a preferred route, you may recommend this to your driver and reach a mutual agreement before you g |  |
| FC-R03 | 1 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  |  |
| FC-R03 | 2 | INDUSTRY | IND-DIDI-DETOUR | undated (read 2026-10-05) |  | VERIFIED | sources/research/09_fact_check.md | 实际行驶里程÷腾讯地图里程 ≥120% 且 绕路里程≥3 公里，则判定为绕路 |  |
| FC-R04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| FC-R05 | 1 | INDUSTRY | IND-BENCHMARK-NOTES | 2026-10-05 |  | PARAPHRASE |  |  | DiDi charges only the estimated fare when a detour is found (research notes 02 and 08). |
| FC-R06 | 1 | RYDE_POLICY | RYDE-115000772653 | 2024-04-19 |  | VERIFIED | corpus body | If a rider passes through an active ERP gantry, the toll charge will be applicable to the rider. |  |
| FC-R06 | 2 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The fares for RydeSEND include ERP. |  |
| FC-R06 | 3 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | The driver bears 50% of the ERP charge, and the passenger pays the remaining 50%. |  |
| FC-R07 | 1 | RYDE_POLICY | RYDE-115001438614 | 2026-09-02 |  | VERIFIED | corpus body | Please bear in mind that if an additional/excessive amount is keyed in, this will be considered fraudulent and |  |
| FC-R08 | 1 | REGULATION | LTA-PDVL-OFFENCES | 2023-04-01 |  | VERIFIED | sources/research/09_fact_check.md | Failing, without reasonable cause, to proceed to destination named by a passenger by shortest and most direct  |  |
| FC-R09 | 1 | RYDE_POLICY | RYDE-51399796192921 | 2025-10-10 |  | VERIFIED | corpus body | If the driver accepts your edit destination request, a $3.00 add/edit destination fee will apply. |  |
| FC-R09 | 2 | RYDE_POLICY | RYDE-50798691815449 | 2025-10-09 |  | VERIFIED | corpus body | *RydePOOL, RydeTAXI & Multiple stop bookings are not allowed to make any changes in destination. |  |
| FC-R10 | 1 | RYDE_POLICY | RYDE-18230976652185 | 2025-12-03 |  | VERIFIED | corpus body | If you have been charged for a trip that you have not taken, kindly share the details with us to investigate t |  |
| FC-R10 | 2 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Drivers who are found to have overcharged riders or completed trips without the rider onboard may face account |  |
| FC-R11 | 1 | RYDE_POLICY | RYDE-22836370596377 | 2026-02-26 |  | VERIFIED | corpus body | *First Tier Platform Fee: $1.25 (including GST) for fares $18 and below. |  |
| FC-R11 | 2 | RYDE_POLICY | RYDE-22836370596377 | 2026-02-26 |  | VERIFIED | corpus body | *Second Tier Platform Fee: $1.47 (including GST) for fares above $18. |  |
| FC-R11 | 3 | RYDE_POLICY | RYDE-52594357168281 | 2025-11-23 |  | VERIFIED | corpus body | 1.96% + $0.24 for Local Visa, Mastercard, and Rydecoins |  |
| FC-R12 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
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
| SE-R02 | 1 | RYDE_POLICY | RYDE-16925196526489 | 2023-04-26 |  | VERIFIED | corpus body | The driver may terminate a ride in progress if there is a safety concern or if the rider is violating the comm |  |
| SE-R03 | 1 | RYDE_POLICY | RYDE-51812996696217 | 2025-10-24 |  | VERIFIED | corpus body | No. Ryde does not allow drivers to use IVRDs or dashcams at this time. |  |
| SE-R03 | 2 | RYDE_POLICY | RYDE-360036735393 | 2025-09-19 |  | VERIFIED | corpus body | Unauthorised installation of inward-facing IVRD/Dashcams may result in 21 demerit points and suspension from o |  |
| SE-R04 | 1 | RYDE_POLICY | RYDE-900003838386 | 2023-09-19 |  | VERIFIED | corpus body | Report to us swiftly via RydeHelp within 1 hour. |  |
| GEN-R01 | 1 | RYDE_POLICY | RYDE-4407754403353 | 2026-02-26 |  | VERIFIED | corpus body | Otherwise, you will not be charged the $6.61 Waiting Time Fee if any of the above are not fulfilled. | [clause is one side of a META-04 known conflict: does not count toward A] |
| GEN-R02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| GEN-R03 | 1 | GOV_GUIDANCE | GOV-PDPC-AI | 2024-03-01 |  | PARAPHRASE |  |  | PDPC AI Advisory Guidelines (1 Mar 2024) paras 9.9 to 9.11: using personal data such as di |
| GEN-R03 | 2 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model AI Governance Framework para 3.23 warns about bias and reinforcement bias from produ |
| GEN-R04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| GEN-R05 | 1 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | Driver-partners will be given the opportunity to respond before final decisions are made, except in urgent or  |  |
| GEN-R06 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 28. Suspension and Termination; Modification of Platform Content (a)-(c) | modify, suspend or terminate operation of or access to the Platform, or any portion of the Platform (including | Account suspension is Ryde's power under the contract, not FairRyde's. |
| GEN-R06 | 2 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| GEN-R07 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 把规则库偷偷换成"通用预设规则"，会让人误以为系统读了合同 |  |
| FRD-01 | 1 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | 5. Remaining stationary and uncontactable after accepting a ride to trigger cancellation or waiting fees |  |
| FRD-01 | 2 | RYDE_POLICY | RYDE-33362721809049 | 2026-04-10 |  | VERIFIED | corpus body | 8. Abuse of Cancellation and Waiting Fee Policy |  |
| FRD-02 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| AUTH-00 | 1 | RYDE_TOU | RYDE-TOU | last modified 6 Apr 2022 (contains later content, such as the S$200 cleaning cap) |  | VERIFIED | Section A, 7. Cancellation, 7.2 Cancellation Terms for Users (paragraph 3) | Ryde reserves its absolute discretion to any refunds to you |  |
| AUTH-01 | 1 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model AI Governance Framework (2nd ed.) paras 3.14 to 3.16: human-over-the-loop for low-se |
| AUTH-02 | 1 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| AUTH-03 | 1 | GOV_GUIDANCE | GOV-IMDA-AGENTIC | 2026-01-22 |  | VERIFIED | sources/research/09_fact_check.md | Organisations should define significant checkpoints or action boundaries that require human approval, especial |  |
| AUTH-03 | 2 | RYDE_POLICY | RYDE-15395890865561 | 2026-04-10 |  | VERIFIED | corpus body | Violations of these guidelines will result in immediate termination and legal action where applicable. | Sanctions are Ryde's (termination, legal action), so they are not FairRyde's to apply. |
| AUTH-04 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |
| AUTH-05 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | Weights, margin scale and penalty are to be calibrated on the dev set. The 4 Oct report us |
| AUTH-06 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  | One tier per outcome, so annotators and reviewers get one answer (second independent revie |
| EXP-01 | 1 | GOV_GUIDANCE | GOV-MGF2 | 2020-01-21 |  | PARAPHRASE |  |  | Model Framework paras 3.48, 3.51 and 3.54 (explanations and requests for review); PDPC AI  |
| EXP-02 | 1 | INTERNAL_STANDARD | INT-CHORDX-ONT | 2026-09-25 |  | VERIFIED | sources/chordx_knowledge_base.md | 分"可以写死的规则"和"必须回头读原文的规则" |  |
| EXP-03 | 1 | FAIRRYDE | FAIRRYDE-DECISIONS | 2026-10-05 |  | NO_QUOTE (design assumption) |  |  |  |

## Credibility review

| rule | type | credibility | mode | weakest essential parameter | source types | note |
|---|---|---|---|---|---|---|
| META-01 | meta | D | HARD | D | FAIRRYDE |  |
| META-02 | meta | D | HARD |  | RYDE_POLICY | Ryde states effective dates (A); choosing parameters by trip date is FairRyde's rule (D). |
| META-03 | meta | A | HARD |  | RYDE_TOU |  |
| META-04 | meta | D | HARD |  | FAIRRYDE |  |
| META-05 | meta | A | HARD |  | INTERNAL_STANDARD |  |
| CLS-01 | classification | C | HARD |  | INDUSTRY, RYDE_POLICY | The norm is Ryde's (A); routing every safety case to a human is industry practice and FairRyde's choice (C). |
| CLS-02 | classification | D | HARD |  | INTERNAL_STANDARD | The protocol names the pitfall (A); the ordering of primary and secondary claims is FairRyde's design (D). |
| CLS-03 | classification | D | HARD |  | FAIRRYDE |  |
| CLS-04 | classification | D | HARD |  | FAIRRYDE |  |
| CLS-05 | classification | A | HARD |  | ORGANIZER |  |
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
| CW-F03 | fact | A | HARD | A | ORGANIZER, RYDE_POLICY | Threshold and comparison are A; the 30 s boundary band is a FairRyde parameter (D) that only adds a flag. |
| CW-F03B | fact | D | HARD |  | FAIRRYDE, RYDE_POLICY | The GPS condition is Ryde text (B, see CW-R06); where the wait starts when that condition fails is FairRyde's inference, |
| CW-F04 | fact | B | HARD | D | ORGANIZER, RYDE_POLICY | The GPS condition is in a Ryde rider article whose wording about the fee name conflicts with the main policy page (META- |
| CW-F05 | fact | D | HARD | D | INDUSTRY, RYDE_POLICY | Ryde's driver guidance (an older article) asks drivers to try to contact the rider (B); the minimum counts are FairRyde  |
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
| CW-R08 | eligibility | C | HARD | C | INDUSTRY |  |
| CW-R09 | remedy | A | HARD | A | ORGANIZER, RYDE_POLICY | Under ryde_2026 the rider pays S$6.61 (S$5.00 base + S$1.25 platform fee + S$0.36 transaction fee, reference table CANCE |
| CW-R10 | remedy | A | HARD | D | RYDE_POLICY | For organizer cases the voucher form is assumed (D) because the organizer data does not say how refunds are paid. |
| CW-R11 | procedural | D | HARD | D | FAIRRYDE, RYDE_TOU |  |
| CW-R12 | outcome | D | HARD |  | FAIRRYDE |  |
| FC-F01 | fact | B | HARD |  | RYDE_POLICY | 'Fares are fixed' comes from rider articles edited more than 12 months ago, and a driver FAQ describes earnings from dri |
| FC-F02 | fact | D | HARD | D | FAIRRYDE |  |
| FC-F03 | fact | C | READ |  | INDUSTRY, REGULATION, RYDE_POLICY | Rider agreement (Ryde, older article) and "reasonable cause" (LTA) are B; the navigation-reroute exemption comes from Di |
| FC-F04 | fact | A | HARD | A | RYDE_POLICY |  |
| FC-R00 | eligibility | D | HARD | C | FAIRRYDE, RYDE_POLICY | The RydeTAXI facts are Ryde text (rider and driver articles edited 2026-01-26, A). Excluding metered fares from a platfo |
| FC-R01 | outcome | B | HARD |  | RYDE_POLICY | Both rider articles were edited more than 12 months ago (2024-10-01, 2025-07-17). Ask the organizer to confirm fixed far |
| FC-R02 | eligibility | B | READ |  | RYDE_POLICY | Both articles were edited more than 12 months ago (2023-06-16, 2024-10-01). |
| FC-R03 | outcome | C | HARD+READ | C | INDUSTRY, REGULATION | The duty to take the shortest route is in Singapore regulation (B); the numeric thresholds are DiDi's published values u |
| FC-R04 | outcome | D | HARD | D | FAIRRYDE |  |
| FC-R05 | remedy | D | HARD | D | INDUSTRY |  |
| FC-R06 | eligibility | A | HARD |  | RYDE_POLICY |  |
| FC-R07 | outcome | A | HARD+READ | D | RYDE_POLICY | The overstatement rule and its fraud consequence are Ryde's (A). The tolerance is FairRyde's (D) and is set to S$0.00; t |
| FC-R08 | outcome | C | HARD+READ |  | REGULATION | The route duty is regulatory (B); turning it into an ERP refund is FairRyde's generalization (C/D). |
| FC-R09 | eligibility | A | HARD | A | RYDE_POLICY |  |
| FC-R10 | outcome | D | HARD+READ |  | RYDE_POLICY | Investigation and sanctions are Ryde's (A); the full-refund remedy is FairRyde's inference (D). |
| FC-R11 | remedy | A | HARD | A | RYDE_POLICY |  |
| FC-R12 | outcome | D | HARD |  | FAIRRYDE |  |
| DM-R01 | eligibility | A | HARD | A | RYDE_POLICY |  |
| DM-R02 | eligibility | A | HARD |  | RYDE_POLICY |  |
| DM-R03 | remedy | A | HARD+READ | A | RYDE_POLICY |  |
| DM-R04 | authority | A | READ |  | RYDE_POLICY |  |
| DM-R05 | procedural | A | HARD | A | RYDE_POLICY |  |
| DM-R06 | remedy | A | HARD |  | RYDE_POLICY, RYDE_TOU |  |
| SE-R01 | authority | D | HARD |  | GOV_GUIDANCE, RYDE_POLICY | That a human decides is official guidance (B) and sanctions are Ryde's (B); the triage steps (preserve and hash evidence |
| SE-R02 | eligibility | B | READ |  | RYDE_POLICY |  |
| SE-R03 | eligibility | A | HARD |  | RYDE_POLICY |  |
| SE-R04 | procedural | B | READ | B | RYDE_POLICY |  |
| GEN-R01 | procedural | D | HARD |  | RYDE_POLICY | Ryde's 'conditions must be fulfilled' wording supports it (A); generalizing it to all charges is FairRyde's (D). |
| GEN-R02 | procedural | D | HARD |  | FAIRRYDE |  |
| GEN-R03 | procedural | D | HARD |  | GOV_GUIDANCE | The guidance supports disclosure and caution (B); that history never decides an outcome is FairRyde's design (D). |
| GEN-R04 | procedural | D | HARD |  | FAIRRYDE |  |
| GEN-R05 | procedural | D | READ |  | RYDE_POLICY | Ryde's sentence sits in its misconduct section ("Ryde is committed to investigating all reports of misconduct fairly and |
| GEN-R06 | authority | B | HARD |  | GOV_GUIDANCE, RYDE_TOU |  |
| GEN-R07 | procedural | D | HARD |  | INTERNAL_STANDARD | The protocol names the risk (A); escalating as the response is FairRyde's design (D). |
| FRD-01 | fraud | D | READ | D | RYDE_POLICY | Ryde defines the prohibited behavior (A). The detection signals (arrival marked without GPS presence, repeated no-shows  |
| FRD-02 | fraud | D | HARD | D | FAIRRYDE |  |
| AUTH-00 | authority | A | READ |  | RYDE_TOU |  |
| AUTH-01 | authority | D | HARD | D | GOV_GUIDANCE |  |
| AUTH-02 | authority | D | HARD | D | GOV_GUIDANCE | The checkpoint principle is official guidance (B); the list of triggers is FairRyde's design (D). Triggers can only send |
| AUTH-03 | authority | B | HARD |  | GOV_GUIDANCE, RYDE_POLICY |  |
| AUTH-04 | authority | D | HARD | D | FAIRRYDE |  |
| AUTH-05 | authority | D | HARD | D | FAIRRYDE |  |
| AUTH-06 | authority | D | HARD |  | FAIRRYDE |  |
| EXP-01 | explanation | B | HARD |  | GOV_GUIDANCE |  |
| EXP-02 | explanation | A | HARD |  | INTERNAL_STANDARD |  |
| EXP-03 | explanation | D | HARD |  | FAIRRYDE |  |
