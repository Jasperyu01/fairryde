# A3: how the approval tier changes (FX4, D29)

Step A3 split CW-F04 into Ryde's condition (CW-F04, B) and FairRyde's GPS presence logic (CW-F04B, D). It added the decision-table input `gps_logic_decides` (CW-F04B's finding F-GPS-LOGIC) and a new row R11. R11 is the D twin of R8 for an upheld fee that rests on that logic. It also added AUTH-02 trigger 12 (decision D29). The numbers below come from the reference engine (`kb/tools/engine_noshow.py`) before the step (commit 3426070, A2) and after it.

## The cases the step prompt names

| Case | Before A3 (row, tier) | After A3 (row, tier) | Change |
|---|---|---|---|
| DISP-002, organizer profile | UPHOLD, R8, APPROVE | UPHOLD, R8, APPROVE | none |
| DISP-002, Ryde profile | UPHOLD, R8, APPROVE | UPHOLD, R8, APPROVE | none |
| E01 | UPHOLD, R8, APPROVE | UPHOLD, R8, APPROVE | none |
| E02 | WAIVE_FEE, R1, APPROVE | WAIVE_FEE, R1, APPROVE | none |
| E03 | UPHOLD, R8, APPROVE | UPHOLD, R8, APPROVE | none |
| E04 | WAIVE_FEE, R6, AUTO | WAIVE_FEE, R6, AUTO | none |

- None of these tiers changes.
- In DISP-002, E01 and E03 every driver ping in the waiting window is inside the pick-up area, nothing is set aside, and the arrival is confirmed at the indication. So F-GPS-LOGIC is false and the uphold stays on R8 (B).
- These three upholds already needed approval for other reasons:
  - In E01, E03 and DISP-002 the ping-gap parameter is decisive: PING_MAX_GAP_S within its plausible range changes the outcome, or moves the case onto a row rated D. Since A3 this also carries D29's parameter part (AUTH-02 trigger 12).
  - Both DISP-002 profiles have the fraud signal on the rider and a pin far from the venue the rider names.
  - The organizer profile also has a zero margin inside the source spread. The Ryde profile's margin is +300 s.
- What changes is the attribution. The decisive parameter is now reported against CW-F04B, FairRyde's logic, not CW-F04. The engine rerun is in `01_engine_rerun.json`.
- E02 (an R1 waiver) and E04 (an R6 waiver) do not rest on CW-F04B.
- E11 (ERP) is unchanged: TOLL_REFUND S$6.00 at APPROVE. FC-R07 is now rated D, but its fraud signal already sent every overstatement to approval.

## Self-test variants whose row or tier changed

| Variant | What it is | Before | After |
|---|---|---|---|
| V25 | one ping 150 m out mid-wait, set aside as an outlier | R8, AUTO | R11, APPROVE |
| V32 | 5-second pings with a 10-second jump to 150 m (outlier) | R8, AUTO | R11, APPROVE |
| V04F, V33, V35, V48, V50, V51, V52, V54 | outliers, data errors, edge pings or GPS_AMBIGUOUS | R8, APPROVE | R11, APPROVE |
| V94 (new) | arrival confirmed only by a ping 40 s after the mark | R8, APPROVE (A2 engine; CW-F03B's start test) | R11, APPROVE |
| V95 (new) | the driver pulls away 2 s before the threshold (60 m out, not counted as leaving because it is within the tolerance of the window end) | R8, AUTO (same case run on the A2 engine) | R11, APPROVE |
| V96 (new, rebuilt in check round 2) | no platform check; a 150 m outlier is the last ping before the arrival mark, so it would otherwise be CW-R06's moment ping | R8, APPROVE (A2 engine) | R11, APPROVE |
| V96B, V100 (new, check round 2) | the same outlier followed by pings at the pin before the mark (V96B), or with the platform check (V100): it cannot change the arrival | R8, AUTO (A2 engine) | R8, AUTO |
| V97 (new, check round 1) | advance booking, platform check, an outlier long before the counted wait: it can change neither the arrival nor the presence | R8, AUTO (A2 engine) | R8, AUTO |
| V101 (new, check round 2) | advance booking, platform check, an outlier 10 s after the indication that would otherwise contradict the check | R8, AUTO (A2 engine) | R11, APPROVE |
| V102 (new, check round 2) | at the pin until 60 s before the 3-minute wait ends, next ping 400 m away after it ended | R8, AUTO (A2 engine) | R11, APPROVE (GPS_AMBIGUOUS) |
| V103 (new, check round 2) | advance booking: away until 10 s before the scheduled time, first back at the pin 50 s after it | R8, APPROVE (A2 engine, for the spread of the wait-start records, not the GPS) | R11, APPROVE (GPS_AMBIGUOUS) |
| V98 (new, check round 1) | a departure whose pings are written in UTC (pre-existing engine defect: pings sorted by text) | UPHOLD, R8, APPROVE (A2 engine, wrong) | WAIVE_FEE, R4 |
| V99 (new, check round 1) | pings 3 m from the pin and one at 15 m (inside the 50 m area) | R8, AUTO (A2 engine) | R8, APPROVE (radius part of D29) |

- The other 89 of the first 101 variants keep their row and tier. Of those, 19 variants still uphold automatically on R8, plus V96B, V97 and V100 among the new ones: all their pings in the window are inside, with nothing set aside that could change the result. They are the clean baseline V06, V24, V27, V34 and V40, and the rider-message variants that read as admissions or acknowledgments (V56 to V58, V63, V64, V68, V70, V73, V75 to V78, V82, V90).

## Random GPS cases (`kb/tools/fuzz_presence.py`, 3,000 cases, seed 11)

| | Before A3 | After A3 |
|---|---|---|
| Upheld fees | 959 | 959 |
| of which AUTO | 118 | 34 |
| of which on R11 | n/a | 533 |
| All AUTO rulings | 388 | 304 |
| Invariant findings | 0 | 0 |

- The generator deliberately places pings outside the area and near the window edges, so the share on R11 is far higher than in real cases.
- Waivers are unchanged.
- The fuzz invariant now also checks D29:
  - an automatic uphold has no ping outside the area in the window;
  - F-GPS-LOGIC is false;
  - the first ping away after the window end does not follow a last inside ping more than the tolerance before the window end.
- Seed 21 with 2,000 cases also gives 0 findings.
- The first draft gave 59 automatic upholds. The check rounds narrowed which set-aside pings count (round 1) and added the window-edge cases to GPS_AMBIGUOUS (round 2).

## Cost of the radius part of D29 (check round 1, ADV-2)

D29 names the ping-gap and radius parameters as part of FairRyde's GPS logic. At the radius's low end (ARRIVAL_GEOFENCE_M 10 m, the platform's own check), a ping 10 to 50 m from the pin is set aside as an outlier. So a clean uphold with ordinary GPS jitter would rest on the logic there, and the sensitivity test sends it to approval.

The self-test and fuzz cases put inside pings exactly on the pin, which hid this effect. A simulation of 600 clean upholds shows its size (`validation/build_checks/A3/jitter_sim.py kb/tools 600 5`): driver parked 0 to 25 m from the pin, jitter sigma 2 to 8 m, pings every 5 to 30 s, both profiles, platform check in 70% of cases. The same numbers hold after check round 2.

| | Before A3 | After A3 |
|---|---|---|
| Upheld | 600 | 600 |
| AUTO | 235 (39%) | 29 (5%) |
| AUTO among the 26 with every ping within 10 m | 26 | 26 |

- A check reviewer found the same effect independently on the round 1 draft (38% to 5%). Of the 201 cases that reviewer saw move, 198 moved through the radius and 3 through TS_TOLERANCE_S.
- This is the safe direction: no outcome changes, more cases go to approval.
- It follows from D29 as written. Whether to keep it is Jasper's call (open item D39 (g)). The options are:
  - keep it;
  - exempt the radius from the row-move part of decisive_definition clause 2;
  - raise the radius's low end above the platform's 10 m check.

## Waiting fees

- Waiting fees have no engine path and no decision table (D31).
- D29 reaches them through the rule text: CW-F04B states it, AUTH-02 trigger 12 carries it, and PB-CW-WAITING step 5 points to it.
- A waiting fee upheld while F-GPS-LOGIC is true is tier APPROVE.
- So is one where F-GPS-LOGIC would be true with a CW-F04B parameter at an end of its plausible range. This parameter part was missing in the first draft (check round 1, SG-1 and ADV-1): a no-show fee gets it from the move onto R9 or R11, but a waiting fee has no rows.
- E07's pings are 90 s apart, so at PING_MAX_GAP_S 60 its presence would be SPARSE. The fee therefore needs approval, as the round 1 applier also concluded.
- The check round's KB applier on E07 tests this path.
