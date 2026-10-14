# A3 check round 1: brief for the reviewers

Commit range: `git diff de53c7c 17fc16c` (de53c7c records Jasper's decisions of 14 Oct on A2's open points; 17fc16c is the A3 draft).

## What A3 had to do

From `docs/NEXT_STEPS.md`, step A3 (FX4 credibility census):

> For all 16 rules rated B or C in kb/rules.yaml (17 in v0.1; A2 moved FC-R08 to D), write validation/round2/census.csv with one row per essential element: rule, element, source (document and clause) or FAIRRYDE, proposed label. Then relabel by the weakest-element principle. Split CW-F04 into the Ryde core (B) and FairRyde's presence logic (D) and update the decision-table rows; apply decision D29 (Jasper, 11 Oct): an uphold that depends on FairRyde's own GPS presence logic always needs approval (tier APPROVE), never AUTO, for no-show fees in the engine and DT-CW-NOSHOW and for waiting fees in the rule text (D31: waiting fees have no decision table). Rebuild, report how the approval tier of the DISP-002 and E01 to E04 cases changes, log as A3.

FX4 (`validation/V5_scorecard/54_fix_list.json`):

- Census of all B and C rules, one row per element with its source; the weakest essential element sets the label.
- Split CW-F04 into the Ryde core (driver at the pick-up per GPS while waiting, B) and FairRyde's presence machinery (outliers, window edge, LEFT, SPARSE, UNKNOWN, GPS_AMBIGUOUS, D). DT rows then take the weaker label only when that machinery decides.

D29 (`kb/open_items.yaml`, Jasper, 11 Oct): whenever upholding a fee depends on FairRyde's own GPS logic, the ruling needs human approval (tier APPROVE), never AUTO. The logic covers outliers, window edges, LEFT, SPARSE, UNKNOWN, GPS_AMBIGUOUS, and the ping-gap and radius parameters.

Jasper, 14 Oct: FC-R07 goes to credibility D in A3.

## What the builder did (check it; do not take it as given)

- **Census:** `validation/round2/census.csv` has 77 rows for 18 rules: the 16 B and C rules, the new CW-F04B, and FC-R07.
- **Relabeled to D:** CLS-01, CW-R08, FC-F03, FC-R02, FC-R03, EXP-01, FC-R07.
- **Kept:** CW-F02B (C); CW-F04, CW-R00, CW-R06, FC-F01, FC-R01, SE-R02, SE-R04, GEN-R06, AUTH-03 (B).
- **Sources added:** FC-F01 (the recalculation quote), SE-R02 (two quotes), SE-R04 (the 24-hour traffic accident report quote; the statement now says "traffic accident report" instead of "police report").
- **CW-F04 split:**
  - CW-F04 (B) keeps only Ryde's condition and the window, with no parameters.
  - CW-F04B (D, new) holds the outlier, data-error, approach and window-edge logic, the LEFT/SPARSE/CONSISTENT/UNKNOWN values, GPS_AMBIGUOUS and the five GPS parameters. This text was moved from v0.1's CW-F04 and is meant to be unchanged in meaning.
  - CW-F04B also produces the new finding F-GPS-LOGIC. It is true when the logic, and not the pings alone, makes the driver count as arrived and present:
    - a ping was set aside between PING_MAX_GAP_S before the arrival indication and the window end;
    - an outside ping in the window was not counted as leaving;
    - the arrival was confirmed only by a later ping (ARRIVAL_UNCONFIRMED);
    - presence is SPARSE; or
    - GPS_AMBIGUOUS holds.
- **CW-R06 stays B.** Its FairRyde parts are named as belonging to D rules: the outlier step (CW-F04B), the later confirmation (CW-F03B), CONTESTED (GEN-R02) and UNKNOWN (GEN-R01). LEFT_MIN_OUTSIDE_S and SPEED_MAX_KMH left its params.
- **DT-CW-NOSHOW:**
  - new input `gps_logic_decides` (F-GPS-LOGIC);
  - R8 (B) now needs it false;
  - new row R11 (D) is the same uphold when it is true;
  - R5, R9 and R10 list CW-F04B;
  - R1 and R4 stay B, with a stated reason;
  - enumeration: 192 combinations, all unique.
- **D29:**
  - Engine (`kb/tools/engine_noshow.py`): computes F-GPS-LOGIC, feeds the table, and adds a trigger.
  - AUTH-02 trigger 12 covers waiting fees.
  - CW-F04B's text states D29.
  - PB-CW-WAITING step 5 points to it.
- **Tests:**
  - New variants V94 and V95. Ten variants moved from R8 to R11; V25 and V32 went from AUTO to APPROVE.
  - New `a3_check` in `kb/tools/selftest.py`: census coverage, weakest-element labels, the R8/R11 split, AUTH-02 trigger 12, and no AUTO uphold with F-GPS-LOGIC true.
  - New fuzz invariant in `kb/tools/fuzz_presence.py`.
- **Tier report:** `validation/build_checks/A3/02_tier_report.md`. DISP-002 and E01 to E04 are unchanged.
- **open_items:**
  - D29 marked implemented;
  - D35 items 4 and 5 closed;
  - new D39 with the judgments left for Jasper.
- **Not yet done:** `docs/NEXT_STEPS.md`'s status line is updated only when the step closes.

## Out of scope

- The rider-message reading (CW-F06 READ part, `rider_contact_reading`, `before_arrival_reading`) is frozen (D34). Report gaps there only as MINOR with the note "frozen area (D34)".
- Step A4 rewrites CLS-01 (FX6). A3 only relabels it.
