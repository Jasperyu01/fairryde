# Next steps: KB v0.2 and validation round 2

One cloud session per step. Each session reads `CLAUDE.md` first, logs its start and end, and commits its work with a message that names the step. Paste the prompt in the right column into a new session on this repo.

Each step is developed on its own branch and merged into `main` through a pull request that Jasper merges; start the next step's session from `main` after the merge.

Status: A1 done (11 Oct 2026, see `validation/build_checks/A1/` and decisions D27 to D32 in `kb/open_items.yaml`); A1b applied Jasper's decisions D27, D30 and D31 (`validation/build_checks/A1b/`). A2 to A5 and B are open.

## How each step is checked (Jasper, 11 Oct: exactly as A1)

1. E steps, run by the builder: `python3 kb/build_kb.py --no-xlsx` (ERROR 0, WARN 0), `python3 kb/tools/selftest.py`, and `python3 validation/tools/rerun_engine.py validation/build_checks/<step>/01_engine_rerun.json E01 E02 E03 E04`.
2. D steps, run by fresh agents that did not make the change, with the workflow `.claude/workflows/kb-step-check.js` (pass the step, the commit range, what the step had to do, the round 1 cases it affects, and step-specific focus for each reviewer):
   - fresh KB appliers re-decide the affected round 1 cases from the KB alone;
   - four reviewers each check one dimension: fix fidelity and scope; sources and credibility; an adversarial test of the changed logic; consistency across files and party-facing text;
   - each reviewer is followed by a skeptic that tries to refute every finding.
3. Fix what the skeptics confirm. Run a second round only if the first had CRITICAL or MAJOR findings; never more than two rounds (CLAUDE.md stop rules). Whatever is left goes to `kb/open_items.yaml`.
4. Save the appliers' decisions, the reviews and a per-finding disposition in `validation/build_checks/<step>/`, log every step with `validation/tools/vlog.py`, and open a pull request for Jasper.

## A. Build v0.2 (fixes from `validation/V5_scorecard/54_fix_list.json`)

| Step | Fixes | Prompt |
|---|---|---|
| A1 (done) | FX1 rider evidence, FX2 metered taxi | "Read CLAUDE.md and FX1 and FX2 in validation/V5_scorecard/54_fix_list.json. Make CW-F06 content-based and define 'during the wait' for waiting fees; update kb/tools/engine_noshow.py and add self-tests for the E01, E03 and E07 patterns. Add a RydeTAXI/METERED exclusion to FC-R03 and FC-R05 that escalates under GEN-R07. Rebuild with python3 kb/build_kb.py --no-xlsx (ERROR 0, WARN 0). Log the step as A1 with validation/tools/vlog.py. Do not touch other rules." |
| A2 | FX3 ERP, FX5 gate G3 | "Read CLAUDE.md and FX3 and FX5 in the fix list. Apply FC-R06's RydeSEND and carpool exceptions wherever ERP is computed (FC-F04, FC-R07, FC-R08) and record the precedence; FC-R08 to credibility D with the PDVL-only note; add the GPS most-efficient-route justification to FC-F03; make FC-R01 send detour ERP to its own FC-TOLL claim. Settle open item D32 (FC-R08 on metered RydeTAXI trips, in line with FC-R00). Change AUTH-04 gate G3 so it keeps the history-blind ruling as provisional (tier APPROVE). Add tests, rebuild, log as A2." |
| A3 | FX4 credibility census | "Read CLAUDE.md and FX4. For all 17 rules rated B or C in kb/rules.yaml, write validation/round2/census.csv with one row per essential element: rule, element, source (document and clause) or FAIRRYDE, proposed label. Then relabel by the weakest-element principle. Split CW-F04 into the Ryde core (B) and FairRyde's presence logic (D) and update the decision-table rows; apply decision D29 (Jasper, 11 Oct): an uphold that depends on FairRyde's own GPS presence logic always needs approval (tier APPROVE), never AUTO, for no-show fees in the engine and DT-CW-NOSHOW and for waiting fees in the rule text (D31: waiting fees have no decision table). Rebuild, report how the approval tier of the DISP-002 and E01 to E04 cases changes, log as A3." |
| A4 | FX6 safety routing, FX7 drop-offs | "Read CLAUDE.md and FX6 and FX7. CLS-03's exception covers any SE leaf; give CLS-01 a definition with examples (abduction, unsafe drop-off, threats); define SE-CONDUCT. Make ENT-TRIP has_dropoff 1:N, ordered, with a destination-change event, and make route rules compare against the final itinerary. Rebuild, log as A4." |
| A5 | Freeze v0.2 | "Read CLAUDE.md. Run python3 kb/build_kb.py (full), set kb version 0.2.0, write kb/CHANGELOG.md listing every rule changed with the FX it comes from, then freeze with validation/tools/freeze.py into validation/round2/00_freeze.json. Log as A5." |

FX8 (two taxonomy leaves) and FX9 (wording) can go into A4 or A5 if time allows.

## B. Validation round 2

Run in a fresh session that did not make the fixes: "Read CLAUDE.md and validation/README.md. Run validation round 2 on KB v0.2 in validation/round2/, reusing the round 1 prompts and tools. Before any result, write and hash a new plan: new seed, doubled samples (taxonomy 40 new texts, ontology 28, rules 40 including all 17 B and C rules, end-to-end 30 with 15 new held-out cases), the same verdict definitions, metrics and thresholds; M5 is computed on the 15 new cases only and the 15 old cases are a regression check; two reviewers on a quarter of the rules. Run each D step as a separate fresh agent with the same read limits as round 1, log every step, then run evidence_check, scorecard, freeze --check and render_page. Reuse validation/tools/rerun_engine.py for the regression check on the old cases."

## For people, not sessions

- Done (Jasper, 11 Oct): the four round 1 mismatches confirmed as the references say (E01, E03, E07 the fee stands; E10 escalate), recorded in `validation/V4_e2e/46_human_check.jsonl`.
- Ask the organizer whether Ryde defines how GPS presence at the pick-up is checked (radius, ping gap). An answer lifts part of CW-F04 from D.
- Decided by Jasper (11 Oct, D29): every uphold that rests on FairRyde's own GPS presence logic needs human approval; worth confirming with Prof. Cao.
- Decided by Jasper (11 Oct): D27 accepted (credibility D; readings that cannot be settled go to a person), D30 rider messages before the driver marks arrival that place the rider at the pick-up count (at least approval), D31 known limitation of v0.2 (no waiting-fee decision table or engine path).
- Open for Jasper: D33 (rider GPS before the arrival indication counted like a message; A1b's extension of D30). Organizer questions O13 (are rider call contents recorded?) and O14 (RydeTAXI detour refunds).
