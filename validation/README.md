# FairRyde KB v0.1: independent validation (7 Oct 2026)

Result: NO-GO for v0.1 as is (M1 0.90 good, M2 0.79 bad, M3 0.65 bad, M4 0.21 bad, M5 0.73 acceptable). See `V5_scorecard/51_scorecard.json` and the fix list in `V5_scorecard/54_fix_list.json`.

## Order of work (one primitive per step; D = an agent judges, E = a script executes)

| Step | D/E | Output |
|---|---|---|
| P0 freeze KB hashes | E | `00_freeze.json` |
| P1 pre-register plan, thresholds, decision rule | E | `01_plan.yaml`, `01_plan.sha256` |
| P2 seeded samples and packets | E | `V2_ontology/20_sample.json`, `V3_rules/30_sample.json`, `packs/` |
| V1.1 collect 20 real complaints | D | `V1_taxonomy/10_cases.jsonl` (names, plates, phones replaced) |
| V1.2 classify with the KB taxonomy | D | `V1_taxonomy/11_labels_kb.jsonl` |
| V1.3 blind labels, then verdicts | D | `V1_taxonomy/12_labels_judge_blind.jsonl`, `13_verdicts.jsonl` |
| V2.1 ground 14 ontology items | D | `V2_ontology/21_verdicts.jsonl` |
| V3.1a, V3.1b ground 22 rules (two blind passes) | D | `V3_rules/32_pass1_*.jsonl`, `32_final_*.jsonl` |
| V3.2 settle the two reviewer disagreements | D | `V3_rules/33_overlap_adjudication.jsonl` |
| V4.1 write 15 cases from Ryde policy only | D | `V4_e2e/cases/`, `40_intended.jsonl` |
| V4.2 label them from policy only | D | `V4_e2e/41_labels_policy.jsonl` |
| V4.3 settle references | E | `V4_e2e/42_reference.jsonl` |
| V4.4 reference engine on no-show cases | E | `V4_e2e/43_kb_engine.jsonl` |
| V4.5 apply the KB to the other cases | D | `V4_e2e/43_kb_applier.jsonl` |
| V4.6 compare | E | `V4_e2e/44_comparison.jsonl` |
| V4.7 adjudicate mismatches | D | `V4_e2e/45_adjudication.jsonl` |
| V5.0 check every evidence quote | E | `V5_scorecard/50_evidence_check.json` |
| V5.1 metrics, intervals, decision | E | `V5_scorecard/51_scorecard.json` |
| V5.2 KB and plan integrity | E | `V5_scorecard/52_integrity.json` |
| V5.3 fix list (builder synthesis) | D | `V5_scorecard/54_fix_list.json` |
| V5.4 scorecard page | E | `V5_scorecard/55_scorecard_page.html` |

`run_log.jsonl` has a start and an end line for every step. `python3 tools/timeline.py` prints where the time went (`V5_scorecard/53_timeline.json`). Every agent's prompt is in `prompts/`.

## Rerun after the v0.2 fixes

1. KB v0.2 was frozen in step A5 (`python3 tools/freeze.py --out validation/round2/00_freeze.json`; what changed is in `kb/CHANGELOG.md`). Check it is unchanged (`python3 tools/freeze.py --out validation/round2/00_freeze.json --check`), then write and hash a new plan (new seed, doubled samples, same thresholds).
2. Run the D steps with fresh agents using the prompts in `prompts/` (update paths and sample lists).
3. `python3 tools/evidence_check.py`, `python3 tools/scorecard.py`, `python3 tools/freeze.py --out validation/round2/00_freeze.json --check`, `python3 tools/render_page.py`.

## Before sharing outside the team

`packs/policy/organizer_*` and `packs/sources/ORG-*` are the organizer's handbook and sample case; remove them before making any repository public.
