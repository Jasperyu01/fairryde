# A2 check round 2: brief for the reviewers and skeptics

This is the last review round allowed for step A2 (CLAUDE.md stop rules). Anything you find that is not fixed goes to `kb/open_items.yaml` afterwards. Range to check: `git diff da4c329 dda592c`.

## What step A2 had to do

Prompt (docs/NEXT_STEPS.md, A2): Apply FC-R06's RydeSEND and carpool exceptions wherever ERP is computed (FC-F04, FC-R07, FC-R08) and record the precedence; FC-R08 to credibility D with the PDVL-only note; add the GPS most-efficient-route justification to FC-F03; make FC-R01 send detour ERP to its own FC-TOLL claim. Settle open item D32 (FC-R08 on metered RydeTAXI trips, in line with FC-R00). Change AUTH-04 gate G3 so it keeps the history-blind ruling as provisional (tier APPROVE). Add tests, rebuild, log as A2.

Fix list (validation/V5_scorecard/54_fix_list.json):

- FX3: one ERP computation that applies FC-R06 in FC-F04, FC-R07 and FC-R08, with the precedence recorded; FC-R08 credibility C to D with the PDVL-only scope of the LTA duty; FC-F03 gets the GPS most-efficient-route justification; FC-R01: ERP from a detour always goes to its own FC-TOLL claim. Verify: rerun E11, add carpool and RydeSEND ERP cases.
- FX5: G3 keeps the history-blind ruling as the provisional ruling (tier APPROVE) and shows the disagreement to the reviewer. Verify: a test pair, same facts, flagged and unflagged rider, both outcomes.

Additional instruction from Jasper (11 Oct): D34 known limitation 1 ("I'm at the mall already" read as an admission of lateness, which upholds the fee automatically) is fixed in this step as a deliberate exception to the D34 freeze, with one test. Limitations 2 and 3 stay known limitations; the rest of the reading stays frozen.

## What was built, and what check round 1 changed

Round 1 found 41 things (1 CRITICAL, 6 MAJOR; see `validation/build_checks/A2/03_review_round1.json` and `04_round1_disposition.jsonl`). Round 1 ran without its arguments (no appliers, no step focus), so this round also has the three appliers.

- Rules FC-F03, FC-F04, FC-R01, FC-R06, FC-R07, FC-R08, AUTH-04 (gate_tiers data, G3 over G8), a pointer in FRD-02, a sentence in the CW-F06 source note.
- Reference table `ERP_RIDER_SHARE`: a share only for the services Ryde's 2026-09-02 driver article names (RydeFLASH, RydePET, RydeX, RydeXL, RydeLUXE, RydeTAXI: 1; RydeSEND: 0; carpool: 0.5). RydePOOL, RydeHIRE, Ryde X GO, Ryde+ and RydeSEND-plus-carpool have no share (GEN-R07); an unrecorded service type is insufficient data (FC-R12).
- FC-R08 refund = min(ERP(actual), ERP charged to the rider) minus ERP(recommended), floor 0, plus FC-R07's overstatement; METERED fares escalate (D32).
- New reference engines `kb/tools/engine_toll.py` (FC-TOLL and the FC-R01 split) and `kb/tools/engine_gates.py` (gate G3). Tests in `kb/tools/selftest.py`: `erp_cases` (27), `erp_check`, `erp_code_check`, `g3_check`, `rule_card_check`, variants V92 and V93, reading cases; wired into `kb/build_kb.py`.
- `kb/tools/engine_noshow.py` changed only in the lateness list `RIDER_LATE_CORE` (D34 item 1).
- Open items: D32 settled; D35 to D38, O15 and O16 added. Also updated: NEXT_STEPS, playbooks, taxonomy, ontology (`is_carpool`), report_md, make_xlsx, `validation/tools/rerun_engine.py` (E11), the workflow file.
- Builder's results: build ERROR 0 WARN 0, 99/99 variants, 561/561 readings, 27 ERP cases pass, E01 to E04 4/4 and E11 TOLL_REFUND S$6.00, 13 of 13 mutations of the new tests caught.

Left on purpose for Jasper and recorded in open_items (do not report these as new findings unless the record is wrong): FC-R07 stays credibility A although its refund remedy is FairRyde's (D35 item 5); FC-R01 opens the FC-TOLL claim without the rider naming the ERP, and only for a fixed fare charged as quoted (D35 item 2); FC-F03 stays C (D35 item 4); office, home and work still read as admissions, and a place plus an admission now goes to approval (D38).

## Focus per dimension

### Fidelity

Compare each changed rule card (FC-F03, FC-F04, FC-R01, FC-R06, FC-R07, FC-R08, AUTH-04, FRD-02, CW-F06 source note) with its version at the base commit and say whether the meaning changed beyond the task or beyond the round 1 fixes. Check that the round 1 fixes really fix what they claim: the share table, the FC-R08 refund formula against `engine_toll.py`, the reason codes, the FC-R01 changes. Check FC-R08 credibility D with the PDVL-only note; the metered exclusion of FC-R08 is in line with FC-R00 and FC-R00 itself is untouched; G3 keeps the history-blind ruling at APPROVE for a win and a loss, ESCALATE_HUMAN stays HUMAN, G3 over G8. Name every change that was not asked for and say whether it is needed. Check `engine_noshow.py` changed only in the lateness list. Re-run the new tests and `python3 validation/tools/rerun_engine.py` with E01 E02 E03 E04 E11. Check by mutating a scratch copy of `kb/` (never the repo) that the new tests fail without each change.

### Grounding

Check the `ERP_RIDER_SHARE` table and FC-R06, FC-F04 against the articles in `kb/sources/ryde_policy_corpus.json` (115001438614, 33363192453785, 19671307820825, 4408072389913, 23575142762393, 20244103989529, 115000772653): is every share in the table in an article edited within 12 months and uncontradicted, so that A holds; is the list of services with no share complete and right. Check the PDVL-only claim in FC-R08 against `kb/sources/research/09_fact_check.md` item 24; FC-F03 sources, dates and its FairRyde evidence rule; FC-R07's FairRyde source and note; FC-R01's new FairRyde source; whether the ratings follow the credibility_principle (the items left for Jasper above are known); the zh texts against the English; D32 and D35 to D38 in `kb/open_items.yaml` against the rules.

### Adversarial

Two targets.

1. `kb/tools/engine_toll.py` (`run`, `fc_r01`, `rider_share`, `service_code`) and `kb/tools/engine_gates.py` against the rule cards FC-R06, FC-F04, FC-R07, FC-R08, FC-F03, FC-R01 and AUTH-04. Import them as in `kb/tools/selftest.py` (`erp_cases` and `g3_check` show the case shape) and build at least 30 NEW edge cases beyond the 27 in selftest: every TX-SERVICE code, spelling variants, `is_carpool` with each service, charged between and around ERP(recommended), ERP(actual) and the sum, tolerance edges, rounding, justification variants, metered with and without detour, inactive gantries, repeated gantries, missing or negative values, missing recommended route. The unsafe error is a case that should go to a person (or be refused) but ends at tier AUTO, a refund above what the rule cards allow (the formula: total refund at most ERP charged minus ERP(recommended)), a fraud signal against a driver who followed the rules, or a crash.
2. The D34 item 1 change in `kb/tools/engine_noshow.py`: messages that mention mall, market, clinic, gym, kopitiam, ATM or MRT in the wait and before the arrival, including messages that also contain a real admission or a placement. Report any message that reads LATE or NEUTRAL although it places or may place the rider (unsafe). Everything else in the reading is frozen (D34): other gaps there are MINOR with the note "frozen area (D34)".

### Consistency

Check every consumer of the changed rules: `playbooks.yaml` (PB-FC-ROUTE, PB-FC-TOLL steps, sources and required_evidence), `taxonomy.yaml` (reason labels, FC-ROUTE excludes, FC-TOLL definition, RydeTAXI note), `ontology.yaml` (F-ERP-EXPECTED, `is_carpool`), `scope.yaml` (carpool and RydePOOL with several riders are in the backlog: consistent with FC-R06?), `reference_data.yaml`, `make_xlsx.py` and `report_md.py` (gate table tier column, test line), `kb/out/check_report.md`, `annotation_schema.yaml`, `kb/open_items.yaml` (D32, D34, D35 to D38, O15, O16 against the rules), `docs/NEXT_STEPS.md`, `validation/tools/rerun_engine.py`, `.claude/workflows/kb-step-check.js`. Grep `kb/` (excluding `kb/sources`) for wording that still describes the old behavior: "conduct information only", "Expected ERP = sum", "otherwise 1", "default: 1", "default 1.0", the old cap "never exceeds the ERP charged", G3 described as escalate or HUMAN, FC-R08 rated C, "still check ERP if contested", 17 rules rated B or C. `kb/tools/explain.py` handles the no-show fee only: say whether anything in it or in the explanation texts for ERP or G3 says something false. Check the changed text for em dashes, en dashes and British spellings.
