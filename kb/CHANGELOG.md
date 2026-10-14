# Knowledge base changelog

## v0.3.0 (14 Oct 2026)

Step A6 (Jasper, 14 Oct). The organizer uploaded Ryde Dispute Resolution Policy v2.1 and the sample cases DISP-001 (route deviation) and DISP-003 (fare and surge). Policy v2.1 says it applies to the Rider Advocate, Driver Advocate and Judge, so it is the primary policy for the hackathon. v0.2 is unchanged in the Ryde profile: E01 to E04 and E11 give the same results as in the A4 rerun (`validation/build_checks/A6/01_engine_rerun.json`).

Decisions D41 to D55 and organizer questions O17 to O25 are in `kb/open_items.yaml`.

### Sources, profiles and data

- **Sources:** ORG-POLICY-V21 (`kb/sources/organizer/policy_v2.1.md`, SHA-256 827c4d2c...8699), ORG-DISP001 and ORG-DISP003. Credibility A, quotes verified by section.
- **Profile `organizer_v2_1`:** the default for organizer cases (a DISP-nnn id). Free wait 5 minutes from the scheduled time, no-show fee S$5.00 paid to the driver, route tolerance 1.0 km, AI limit 2.0 km, final ruling below S$10, human review above S$50, confidence 0.80 (0.95 with a fraud flag). `organizer_case` stays as the legacy profile for E04's embedded policy object, and `ryde_2026` stays as the regression profile for E01 to E15. Tolls: `TOLLS_TREATMENT` is PASS_THROUGH under v2.1 and REFUND_DETOUR_ERP under ryde_2026.
- **Precedents:** `kb/precedents.yaml` holds PREC-7.1 (route, partial refund), PREC-7.2 (surge differential) and PREC-7.3 (no-show fee waived).
- **Expected rulings:** `kb/organizer_cases.yaml`: DISP-001 PARTIAL_REFUND S$3.44, tier APPROVE; DISP-002 UPHOLD, tier APPROVE; DISP-003 FULL_REFUND S$4.50, tier AUTO. The DISP-003 expectation was stated by Jasper and is not in the file.

### Taxonomy, ontology, rules and playbooks

- **Taxonomy:** FC-SURGE is now adjudicated (PB-FC-SURGE). New reasons CW-R-NOCONTACT-VOID, CW-R-DRIVER-NOSHOW, FC-R-DEVIATION-UNNOTIFIED, FC-R-DEVIATION-UNJUSTIFIED, FC-R-DEVIATION-AGREED, FC-R-DEVIATION-TOLERANCE, FC-R-SURGE-UNNOTIFIED, FC-R-SURGE-NOTIFIED and FC-R-SURGE-NOT-HIGHER. New remedy form ORIGINAL_PAYMENT_METHOD and flag FIGURES_DISAGREE.
- **Ontology:** the entities ENT-ROUTE, ENT-INCIDENT, ENT-FARE, ENT-SURGE and ENT-ORGREF; new attributes; finding types F-DEVIATION-KM, F-DEVIATION-CONFIRMED, F-FARE-FIGURES, F-NOTICE, F-AGREED, F-JUSTIFIED, F-SURGE-CHANGE, F-SURGE-NOTICE and F-SURGE-SOLELY. Field mappings for the DISP-001 and DISP-003 formats (`disp001_mapping`, `disp003_mapping`), including chat logs with a "message" field.
- **New rules:** CW-F02C, CW-R13 (D), CW-R14, FC-F05, FC-F06, FC-F06B (D), FC-F07, FC-F08, FC-R13, FC-R13B (D), FC-R14, FC-R15, AUTH-07 (D) and GEN-R08 (D).
- **Rules with v2.1 text and sources added (existing wording kept):** META-01, CLS-01, CLS-05, SE-R01, CW-F02, CW-F03, CW-F05, CW-R03, CW-R04, CW-R08, CW-R09, CW-R10, DQ-05, DQ-06, FC-F02, FC-F03, FC-R01, FC-R03, FC-R04, FC-R05, FC-R08, AUTH-01, AUTH-02, AUTH-04 and EXP-01.
- **Playbooks:** PB-CW-NOSHOW, PB-CW-RIDERCANCEL, PB-FC-ROUTE and PB-INTAKE take v2.1 steps; PB-FC-SURGE is new.
- **Conflicts between v2.1 and the earlier rules (each with its choice):**
  - D41: v2.1 is the primary policy; ryde_2026 is the fallback.
  - D42: free wait 5 minutes from the scheduled time (v2.1), against 3 minutes from arrival (Ryde pages).
  - D43: fee S$5.00, against S$6.61.
  - D44: Section 2.3 voids the fee when the driver made no contact (CW-R13).
  - D45: Section 2.4 driver no-show replaces DRIVER_LATE_GRACE_S in this profile.
  - D46: Section 1.3 gives a partial refund where the older rules gave a full one. "Full" in Section 1.3 is ambiguous and the choice is recorded.
  - D47: tolls pass through under v2.1; FC-R08 and the FC-R01 toll claim do not refund.
  - D48: Section 6 thresholds replace the AUTH limits; the tier mapping is final to AUTO, escalate with a proposed ruling to APPROVE, above S$50, safety or case file only to HUMAN.
  - D49: Section 5.2, safety content is case file only.
  - D50: Section 4.4 against Section 6.2 for damage.
  - D51: DISP-001 cites a nonexistent "Driver Policy 4.2"; Section 1.2 is cited instead.
  - D52: D29 stays as a confidence penalty of 0.10 (D, plausible range 0.05 to 0.25).
  - D53: DISP-001 is under S$10 but 4.3 km exceeds 2 km, so the tier is APPROVE with S$3.44 recommended.
  - D54: the new readings, and the rule that organizer answer blocks are removed before the engines read a case.
  - D55: known limitations.

### Tools and outputs

- **Engines:** `engine_route.py` and `engine_surge.py` are new. `engine_noshow.py` has a v2.1 branch, `engine_toll.py` honors TOLLS_TREATMENT, and `engines.py` picks the engine and scores a sample against its expected ruling. `case_adapter.py` removes the organizer answer blocks and normalizes chat logs. `policy_v21.py` holds the Section 6 path, the composite confidence, precedent matching and the evidence index.
- **Tests:** `kb/tools/selftest_v21.py`, 56 tests: the three samples pinned to their rulings, one-factor variants, tolls pass-through, regression E01 to E04 and E11, and the reconciliation records. The 128 no-show variants, 53 ERP cases and 565 message readings pass as before.
- **Workbooks:** `FairRyde_Annotation_v0.3.xlsx` carries DISP-001, DISP-002 and DISP-003 with the columns organizer_expected_outcome and organizer_expected_amount_sgd; `FairRyde_KB_v0.3.xlsx` has a sheet for the three organizer cases. Both are pseudonymized, and the leak scan is clean. The recalculation script was not available in this environment, so formulas were not recalculated.
- **Privacy:** example names in `privacy.yaml` changed so they do not collide with names in the new cases.

## v0.2.0 (14 Oct 2026)

v0.1 (7 Oct, commit b94bc63) was validated in round 1 and rated NO-GO. v0.2 applies the round 1 fix list, `validation/V5_scorecard/54_fix_list.json` (FX1 to FX9), in steps A1 to A4 of `docs/NEXT_STEPS.md`, and A5 freezes it for validation round 2.

Each build step was checked with the kb-step-check workflow: fresh KB appliers, four reviewers, and a skeptic for each reviewer. The records are in `validation/build_checks/<step>/` and the run log is `validation/run_log.jsonl`. Decisions and open points are in `kb/open_items.yaml`, D27 to D40.

Credibility counts:

| | A | B | C | D | Rules |
|---|---|---|---|---|---|
| v0.1 | 27 | 11 | 6 | 43 | 87 |
| v0.2 | 26 | 9 | 1 | 54 | 90 |

The new rules are FC-R00, CW-F04B and CLS-06.

### By fix

| Fix | Step | What changed |
|---|---|---|
| FX1 rider evidence | A1, A1b | CW-F06 reads what the rider said. Placing the rider at the pick-up, or contesting presence, timing or place, is STRONG evidence. Admitting lateness is not counter-evidence. A reading that cannot be settled goes to a person. "During the wait" is defined. Messages before the arrival count (D30). The reading is frozen (D34). |
| FX2 metered taxi | A1 | New rule FC-R00: no detour refund the platform computes for a metered RydeTAXI fare. FC-R03 and FC-R05 exclude metered fares and escalate under GEN-R07. |
| FX3 ERP exceptions | A2 | FC-R06 sets the rider's ERP share by service, from the new table ERP_RIDER_SHARE: RydeSEND 0, carpool 0.5. FC-F04, FC-R07 and FC-R08 apply it in a recorded order. FC-R08 is D, and per D32 it does not apply to metered fares. FC-F03 has the GPS most-efficient-route justification. FC-R01 sends detour ERP to its own FC-TOLL claim. There is a new reference engine, `kb/tools/engine_toll.py`. |
| FX4 credibility census | A3 | `validation/round2/census.csv` lists every element of the rules rated B or C. Relabeled to D: CLS-01, CW-R08, FC-F03, FC-R02, FC-R03, EXP-01 and FC-R07 (on Jasper's decision). CW-F04 is split into Ryde's condition (B) and FairRyde's GPS logic, the new rule CW-F04B (D). D29: an uphold that rests on FairRyde's own GPS logic needs approval. This is the new finding F-GPS-LOGIC, row R11 and AUTH-02 trigger 12. |
| FX5 gate G3 | A2 | AUTH-04 gate G3 keeps the history-blind ruling as the provisional ruling at tier APPROVE (D37). Gate tiers are data on the rule card. |
| FX6 safety routing | A4 | CLS-01 is a definition read for meaning, with examples from Ryde's Code of Conduct. Unclear text counts as safety content, and rudeness alone is feedback. CLS-02 and CLS-03 cover any SE type. SE-CONDUCT and EX-FEEDBACK are defined. |
| FX7 drop-offs | A4 | ENT-TRIP has_dropoff is 1:N and ordered, and destination_edit_accepted is the destination-change event. Route rules compare against the final itinerary. FC-F02 splits the recommended route at each accepted change. The toll engine applies FC-R12 to a changed itinerary whose recommended route on record does not follow it. |
| FX8 taxonomy gaps | A4 | New leaves FC-FAREMISMATCH and FC-DRIVERCHARGE (BACKLOG). New rule CLS-06: who canceled comes from the trip record. If the records disagree, cannot be read or are silent, the outcome is REQUEST_INFO. |
| FX9 wording | A4 | EXP-03 exempts verbatim clause quotes. CW-F02B's note adds the 2024 driver pages. CW-R08 defines the assignment ETA of an advance booking. Ontology O09 and O10 are labeled FairRyde design. |

### Rules, decision tables and playbooks changed

Credibility is shown as v0.1 → v0.2 where it changed.

| Item | Steps | Fix | Change |
|---|---|---|---|
| CLS-01 | A3, A4 | FX4, FX6 | Definition read for meaning (mode READ), with examples from Ryde's Code of Conduct items 5 to 8 and the community standards. Unclear text is S1. Rudeness alone is feedback, and a money or damage dispute alone is not safety content. Full SE-type mapping. A complaint that mentions discrimination sends the whole case to a person with the case file only (Jasper, 14 Oct). C → D. |
| CLS-02 | A4, 14 Oct | FX6 | Any SE claim is primary, including against the organizer's code. With discrimination, a contested fee is a secondary claim with no proposed outcome (Jasper, 14 Oct). |
| CLS-03 | A4 | FX6 | The exception covers any SE type; applies_to adds SE. |
| CLS-05 | A4 | FX8 | For a cancellation-fee claim the trip record decides the type, over the code (CLS-06). |
| CLS-06 (new) | A4 | FX8 | Who canceled comes from the reason, cancelled_by, the cancel events and the system message. Rider: CW-RIDERCANCEL. Driver for another reason, or system: CW-OTHER. Disagreeing, unreadable or silent records, or a driver cancellation with no reason: REQUEST_INFO at tier HUMAN. D. |
| CW-F01 | A1b | FX1 | Missing booking records: ADVANCE plus RECORDS_MISSING. |
| CW-F02B | A4 | FX9 | Note cites the 2024 driver pages. |
| CW-F04 | A3 | FX4 | Ryde's condition only (B), with no parameters. |
| CW-F04B (new) | A3 | FX4 | FairRyde's GPS presence logic: outliers, window edges, LEFT, SPARSE, GPS_AMBIGUOUS and the five GPS parameters. Produces F-GPS-LOGIC (D29). D. |
| CW-F06 | A1, A1b, A2 | FX1 | Content-based reading of rider calls, messages and phone GPS. Messages before the arrival count (D30, D33). The "at the mall" exception (D38). |
| CW-R03 | A3 | FX4 | Inputs add F-GPS-LOGIC. |
| CW-R06 | A3 | FX4 | Its FairRyde parts are delegated to D rules. LEFT_MIN_OUTSIDE_S and SPEED_MAX_KMH moved to CW-F04B. |
| CW-R08 | A3, A4, 14 Oct | FX4, FX9 | The advance-booking assignment ETA is defined (a late acceptance uses the app's ETA). A driver waiting at the pick-up, or an early advance-booking driver who can still arrive in time, is not "not moving". A waiver always needs approval (Jasper, 14 Oct). C → D. |
| CW-R11 | A3 | FX4 | Rows R8, R9 and R11. |
| CW-R12 | A1b | FX1 | WEAK rider evidence includes messages and phone GPS before the wait. |
| DQ-02 | A3 | FX4 | Points to CW-F04B. |
| DT-CW-NOSHOW | A1, A1b, A3, A4 | FX1, FX4, FX8 | Rows follow CW-F06's readings. New input gps_logic_decides. R8 now needs F-GPS-LOGIC false; new row R11 (D) is the same uphold when it is true. The precondition follows CLS-06. 192 combinations, each unique. |
| AUTH-02 | A3, 14 Oct | FX4 | Trigger 12: an uphold resting on CW-F04B, including at an end of a parameter's plausible range (D29). Trigger 13: a CW-R08 waiver (Jasper, 14 Oct). |
| AUTH-04 | A2 | FX5 | G3 keeps the history-blind ruling at APPROVE; gate_tiers added. |
| EXP-01 | A3 | FX4 | B → D (the content list and the 30-day reading are FairRyde's). |
| EXP-03 | A4 | FX9 | Numbers inside a verbatim clause quote are exempt. |
| FC-F01 | A3, A4 | FX4, FX7 | Recalculation quote. An added drop-off stop makes the fare RECALCULATED, citing the driver and rider articles. |
| FC-F02 | A4 | FX7 | Final itinerary, split at the point nearest the car at each accepted change. The actual path is measured whole. |
| FC-F03 | A2, A3 | FX3, FX4 | GPS most-efficient-route justification. C → D. |
| FC-F04 | A2 | FX3 | ERP expected at the rider's share (FC-R06). |
| FC-R00 (new) | A1 | FX2 | No platform-computed detour refund for a metered fare; GEN-R07 with the measurement attached. |
| FC-R01 | A2, A3, A4 | FX3, FX7 | Detour ERP goes to its own FC-TOLL claim. The recommended route runs through the final itinerary. |
| FC-R02 | A3 | FX4 | B → D (the GPS permission applied beyond fixed fares). |
| FC-R03 | A1, A3, A4 | FX2, FX4, FX7 | Excludes metered fares and uses the final itinerary. C → D. |
| FC-R05 | A1, A4 | FX2, FX7 | Excludes metered fares and uses the final itinerary. |
| FC-R06 | A2 | FX3 | The rider's ERP share by service (ERP_RIDER_SHARE), with precedence over the plain gantry sum. |
| FC-R07 | A2, A3 | FX3, FX4 | Compares against the rider's share. A → D (Jasper, 14 Oct). |
| FC-R08 | A2, A4 | FX3, FX7 | The refund is bounded by the rider's share, with the PDVL-only note and no ruling on metered fares (D32). Uses the final itinerary. C → D. |
| FC-R12 | A2, A4 | FX3, FX7 | ERP data gaps. A changed itinerary whose route on record does not follow it, when the route can change the amount. |
| FRD-01 | 14 Oct | FX8 | A charge the driver made up (FC-DRIVERCHARGE) raises a fraud signal against the driver; it never changes the outcome and is shown to the reviewer only (Jasper, 14 Oct). |
| FRD-02 | A2 | FX5 | The fraud signal never changes the outcome, and G3 is described. |
| SE-R01 | 14 Oct | FX6 | With a mention of discrimination, FairRyde prepares the case file only and makes no recommendation of any kind (Jasper, 14 Oct). |
| SE-R02 | A3 | FX4 | Ryde examples and breakdown quoted. |
| SE-R04 | A3 | FX4 | "Traffic accident report" instead of a police report. |
| PB-INTAKE | A4, 14 Oct | FX6, FX8 | CLS-01 is a READ step; CLS-06 at classification; a discrimination complaint goes to a person whole. |
| PB-CW-NOSHOW | A1, A1b, A3, A4 | FX1, FX4, FX8 | Reading steps, D29 at step 9, and the CLS-06 precondition with its evidence. |
| PB-CW-WAITING | A1, A1b, A3 | FX1, FX4 | Window of the reading; D29 for waiting fees (step 5). |
| PB-CW-RIDERCANCEL | A3, A4, 14 Oct | FX4, FX8, FX9 | CLS-06 precondition; CW-R08's two FairRyde elements named; a CW-R08 waiver needs approval. |
| PB-FC-ROUTE, PB-FC-TOLL | A1, A2, A4 | FX2, FX3, FX7 | Metered exclusion, ERP share and evidence for the final itinerary. |
| PB-TRIAGE-HUMAN, PB-ROUTE-SUPPORT | A4, 14 Oct | FX6 | CLS-01 is a READ step; with discrimination, the case file only (PB-TRIAGE-HUMAN step 6). |

### Taxonomy, ontology and reference data

- **Taxonomy (A2, A4):**
  - New leaves FC-FAREMISMATCH and FC-DRIVERCHARGE.
  - Definitions for SE-CONDUCT, EX-FEEDBACK, EX-LOCATION and FC-TOLL.
  - FC-ROUTE, FC-SURCHARGE, FC-PAYMENT, CW-DRIVERNOSHOW and CW-OTHER text.
  - The REQUEST_INFO and GEN-R-NEED-INFO labels.
- **Ontology (A2 to A4):**
  - ENT-TRIP: ordered dropoffs, an optional cancelled_by and is_carpool.
  - has_dropoff is 1:N. The destination-change events are annotated, and so is the recommended route.
  - New finding F-GPS-LOGIC; F-PRESENCE is produced by CW-F04 and CW-F04B; F-ERP-EXPECTED is at the rider's share.
  - The wraps and rebuts relations are labeled FairRyde design.
- **Reference data:** the new table ERP_RIDER_SHARE (A2). LEFT_MIN_OUTSIDE_S belongs to CW-F04B (A3). ARRIVAL_GEOFENCE_M's plausible range is [25, 100] (Jasper, 14 Oct).
- **Annotation schema:** decision-table row R11, and the autonomy tier of REQUEST_INFO.

### Tools and outputs

- **Reference engines:**
  - `kb/tools/engine_noshow.py`: the CW-F06 reading, F-GPS-LOGIC and D29, CLS-06, and a whole-word safety stand-in.
  - `kb/tools/engine_toll.py` (new): FC-R06 to FC-R08, FC-R01, and FC-R12 on changed itineraries.
  - `kb/tools/engine_gates.py`: gate G3.
  - `kb/tools/explain.py`: party explanations, with the EXP-03 quote exemption.
- **Tests (`kb/tools/selftest.py`):**
  - 128 no-show variants and 565 message readings.
  - 53 ERP cases and the FC-R01 split (R1 to R10).
  - The A2, A3 and A4 rule-card checks, the census check, and the GPS fuzz invariants (`kb/tools/fuzz_presence.py`).
- **Workbooks:** the names follow the KB version: `kb/out/FairRyde_KB_v0.2.xlsx` and `kb/out/FairRyde_Annotation_v0.2.xlsx`. The repository's annotation workbook had no human labels. A labeled v0.1 copy elsewhere is not overwritten; move its labels by content.
- **Freeze:** `validation/tools/freeze.py` hashes the repository's `kb/` and takes `--out`. The round 2 freeze is `validation/round2/00_freeze.json`.

### Jasper's decisions of 14 Oct on the points A3 and A4 left open

Applied after A5 and before the freeze. They were checked by the build, the self-tests and the E01 to E04 rerun, not by kb-step-check, on Jasper's instruction.

- **D29's radius part (D39 (g)):** the plausible range of ARRIVAL_GEOFENCE_M now starts at 25 m instead of the platform's 10 m check.
  - The reason is FairRyde's own design, with no outside source: the GPS position of a car parked near tall buildings drifts while it stands still. At the low end, that drift must not count as being away.
  - The value stays 50 m and the credibility D. A ping between 25 and 50 m from the pin still sends an uphold to approval.
  - In the jitter simulation, automatic upholds of 600 clean cases go from 29 back to 347 (A2: 235).
  - Tests V99 (a 30 m ping, approval) and V99B (a 20 m ping, automatic) pin both sides.
- **CW-R08:** a rider's cancellation fee waived because the driver was late or not moving always needs approval, in line with D29. This is the new AUTH-02 trigger 13, also stated in CW-R08 and PB-CW-RIDERCANCEL step 5.
- **A charge the driver made up (D40 (b)):** FRD-01 raises a fraud signal against the driver for FC-DRIVERCHARGE. The basis is Ryde's community standards: 'Drivers who overcharge riders ...'. As with FRD-02's signal, it never changes the outcome and is shown to the reviewer only.
- **Discrimination (D40 (c)):** a complaint that mentions discrimination is always safety content, and the whole case goes to a person.
  - FairRyde prepares the case file only: the claims, the evidence and the findings. It proposes no outcome, amount or measure on any claim.
  - A contested fee is a secondary claim in the file.
  - Rules: CLS-01, CLS-02, SE-R01, PB-INTAKE step 2 and PB-TRIAGE-HUMAN step 6.
  - Engine: it stops before the decision table. V106, V119 and V120 pin it.
- **Kept as they are:** CW-R06, FC-R01 and AUTH-03 at B (D39 (a) to (c)). An unrecorded is_carpool goes to a person only for RydeFLASH (D35 item 8). The line between rudeness and abuse stays as A4 drew it (D40 (e)).
- **Known limitations of v0.2:** the reference engine's safety check is a pattern list that misses paraphrases (D40 (a)), and the case data has no field for several drop-offs, trip_data.stops (D40 (d)).

### Still open

- The other points of D39 and D40 are recorded for information: engine gaps not fixed, FC-R12 materiality, and the narrower safety examples.
