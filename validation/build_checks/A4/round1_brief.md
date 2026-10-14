# A4 check round 1: brief for the reviewers

Commit range: `git diff f8a6abe 8beb6e8`. f8a6abe is A3; 8beb6e8 is the A4 draft.

## What A4 had to do

From `docs/NEXT_STEPS.md`, step A4 (FX6 safety routing, FX7 drop-offs):

> Read CLAUDE.md and FX6 and FX7. CLS-03's exception covers any SE leaf; give CLS-01 a definition with examples (abduction, unsafe drop-off, threats); define SE-CONDUCT. Make ENT-TRIP has_dropoff 1:N, ordered, with a destination-change event, and make route rules compare against the final itinerary. Rebuild, log as A4.

NEXT_STEPS also says FX8 (two taxonomy leaves) and FX9 (wording) can go into A4 or A5. The builder put both into A4.

FX6, FX7, FX8 and FX9 are in `validation/V5_scorecard/54_fix_list.json`. The round 1 complaints behind them are in `validation/V1_taxonomy/13_verdicts.jsonl` (C02, C04, C05, C06, C07, C08, C11, C15, C16, C18, C19) and `validation/V2_ontology/21_verdicts.jsonl` (O08, O09, O10).

## What the builder did (check it; do not take it as given)

### FX6 (safety routing)

- **CLS-01** is now a definition read for meaning, with examples (mode READ).
  - Most examples come from Ryde's Code of Conduct and the community standards article.
  - FairRyde added: an unsafe drop-off, being stranded, and a driver who will not stop.
  - Unclear text counts as safety content (S1). Rudeness alone is feedback.
  - S0 means someone was hurt, held, assaulted, threatened with harm or put in immediate danger; S1 is everything else.
- **CLS-02** makes any SE claim primary. **CLS-03**'s exception covers any SE type.
- **SE-CONDUCT** and **EX-FEEDBACK** have definitions. Discrimination counts as SE-CONDUCT.
- **Engine:** the offline stand-in for the reading (`SAFETY_WORDS` in `kb/tools/engine_noshow.py`) has more words. It is still a word list.

### FX7 (drop-offs)

- **Ontology:** ENT-TRIP has_dropoff is 1:N and ordered (attribute `dropoffs`). destination_edit_accepted is the destination-change event, and stop_added is explained. O09 and O10 are labeled FairRyde design (FX9).
- **Route rules:** FC-F02 measures against the recommended route through the final itinerary, piecewise around each accepted change. FC-R03, FC-R05, FC-R08, FC-R12, FC-F01 (with a new quote) and FC-R01 follow it.
- **Engine:** `kb/tools/engine_toll.py` escalates under FC-R12 when the itinerary changed (destination_edit_accepted, or a stop_added event) and `route_review.final_itinerary` is not true.

### FX8 (taxonomy gaps)

- New leaves **FC-FAREMISMATCH** and **FC-DRIVERCHARGE**, both BACKLOG, so GEN-R07 escalates them.
- FC-SURCHARGE and FC-PAYMENT definitions point to FC-DRIVERCHARGE.
- New rule **CLS-06**: the canceling party comes from the trip record; if the record does not say, the outcome is REQUEST_INFO. The DT-CW-NOSHOW precondition and PB-CW-NOSHOW step 1 cite it.

### FX9 (wording)

- EXP-03 exempts numbers inside verbatim quotes.
- CW-F02B's note adds the 2024 driver pages.
- CW-R08 defines the assignment ETA of an advance booking: the scheduled time.

### Tests and records

- **No-show variants:** V104 to V106 are safety texts without v0.1's words, expected HUMAN. V107 is rudeness only, expected not to be safety.
- **ERP cases:** T40 to T42 cover the final itinerary.
- **Rule-card check:** `a4_check`.
- **open_items:** new D40.

## Out of scope

- The rider-message reading is frozen (D34).
- Judgments in D39 (A3) are Jasper's.
- `docs/NEXT_STEPS.md`'s status line is updated when the step closes.
