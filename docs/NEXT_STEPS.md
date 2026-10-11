# Next steps: KB v0.2 and validation round 2

One cloud session per step. Each session reads `CLAUDE.md` first, logs its start and end, and commits its work with a message that names the step. Paste the prompt in the right column into a new session on this repo.

## A. Build v0.2 (fixes from `validation/V5_scorecard/54_fix_list.json`)

| Step | Fixes | Prompt |
|---|---|---|
| A1 | FX1 rider evidence, FX2 metered taxi | "Read CLAUDE.md and FX1 and FX2 in validation/V5_scorecard/54_fix_list.json. Make CW-F06 content-based and define 'during the wait' for waiting fees; update kb/tools/engine_noshow.py and add self-tests for the E01, E03 and E07 patterns. Add a RydeTAXI/METERED exclusion to FC-R03 and FC-R05 that escalates under GEN-R07. Rebuild with python3 kb/build_kb.py --no-xlsx (ERROR 0, WARN 0). Log the step as A1 with validation/tools/vlog.py. Do not touch other rules." |
| A2 | FX3 ERP, FX5 gate G3 | "Read CLAUDE.md and FX3 and FX5 in the fix list. Apply FC-R06's RydeSEND and carpool exceptions wherever ERP is computed (FC-F04, FC-R07, FC-R08) and record the precedence; FC-R08 to credibility D with the PDVL-only note; add the GPS most-efficient-route justification to FC-F03; make FC-R01 send detour ERP to its own FC-TOLL claim. Change AUTH-04 gate G3 so it keeps the history-blind ruling as provisional (tier APPROVE). Add tests, rebuild, log as A2." |
| A3 | FX4 credibility census | "Read CLAUDE.md and FX4. For all 17 rules rated B or C in kb/rules.yaml, write validation/round2/census.csv with one row per essential element: rule, element, source (document and clause) or FAIRRYDE, proposed label. Then relabel by the weakest-element principle. Split CW-F04 into the Ryde core (B) and FairRyde's presence logic (D) and update the decision-table rows. Rebuild, report how the approval tier of the DISP-002 and E01 to E04 cases changes, log as A3." |
| A4 | FX6 safety routing, FX7 drop-offs | "Read CLAUDE.md and FX6 and FX7. CLS-03's exception covers any SE leaf; give CLS-01 a definition with examples (abduction, unsafe drop-off, threats); define SE-CONDUCT. Make ENT-TRIP has_dropoff 1:N, ordered, with a destination-change event, and make route rules compare against the final itinerary. Rebuild, log as A4." |
| A5 | Freeze v0.2 | "Read CLAUDE.md. Run python3 kb/build_kb.py (full), set kb version 0.2.0, write kb/CHANGELOG.md listing every rule changed with the FX it comes from, then freeze with validation/tools/freeze.py into validation/round2/00_freeze.json. Log as A5." |

FX8 (two taxonomy leaves) and FX9 (wording) can go into A4 or A5 if time allows.

## B. Validation round 2

Run in a fresh session that did not make the fixes: "Read CLAUDE.md and validation/README.md. Run validation round 2 on KB v0.2 in validation/round2/, reusing the round 1 prompts and tools. Before any result, write and hash a new plan: new seed, doubled samples (taxonomy 40 new texts, ontology 28, rules 40 including all 17 B and C rules, end-to-end 30 with 15 new held-out cases), the same verdict definitions, metrics and thresholds; M5 is computed on the 15 new cases only and the 15 old cases are a regression check; two reviewers on a quarter of the rules. Run each D step as a separate fresh agent with the same read limits as round 1, log every step, then run evidence_check, scorecard, freeze --check and render_page."

## For people, not sessions

- Jasper or a teammate: spend 10 minutes on the four round 1 mismatches (E01, E03, E07, E10 in `validation/V4_e2e/45_adjudication.jsonl`) and confirm or overrule the adjudicator.
- Ask the organizer whether Ryde defines how GPS presence at the pick-up is checked (radius, ping gap). An answer lifts part of CW-F04 from D.
- Decide with Prof. Cao whether every no-show uphold that rests on FairRyde's presence logic should need human approval (the likely result of FX4).
