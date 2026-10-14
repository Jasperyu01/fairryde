# A3 check round 2 (last): brief for the reviewers

Commit range: `git diff de53c7c 829d717`.

- The round 1 brief (`validation/build_checks/A3/round1_brief.md`) still describes what the step had to do.
- Round 1's findings and how each was handled are in `validation/build_checks/A3/04_round1_disposition.jsonl`.
- `git diff 453b511 829d717` shows only the round 1 fixes.

## What changed in round 1

- **D29's parameter part for waiting fees (SG-1, ADV-1, CRITICAL):** AUTH-02 trigger 12, CW-F04B and PB-CW-WAITING step 5 now also fire when F-GPS-LOGIC would be true with a CW-F04B parameter at an end of its plausible range. For no-show fees the engine reports the same trigger (V99).
- **Which set-aside pings count (ADV-4):** F-GPS-LOGIC counts a set-aside ping only if it could change the presence (it is in the window) or the arrival (it is in CW-R06's moment range; with the platform check, only at or after the indication). Tests: V96 and V97.
- **Ping order (ADV-3):** GPS pings are sorted by instant, not by timestamp text. This is a pre-existing defect. Test: V98.
- **Radius cost (ADV-2):** kept, as D29 is written. The cost is measured in the tier report (`01b_tier_report.md`, renamed from `02_tier_report.md`) and left to Jasper (open item D39 (g)). Do not report it again unless you find a new aspect.
- **Explanations:** `kb/tools/explain.py` names the points FairRyde's logic set aside or did not count, and what happened after the counted wait. R11's plain text was reworded.
- **Wording:** CW-F04, CW-R06, SE-R02, FC-R07, DQ-02, census, open items, NEXT_STEPS, playbooks, scope and annotation schema.

## What to check

- Check the fixes themselves: are they right and complete, and did they break anything?
- Check anything round 1 missed.

## Out of scope

- The rider-message reading is frozen (D34).
- Judgments recorded for Jasper in D39 (a) to (i) are his to make.
