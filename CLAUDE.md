# FairRyde

Tencent Cloud x AI Singapore hackathon 2026, Ryde track: multi-agent resolution of ride-hailing disputes. Submission due 16 Oct 2026. Jasper owns the rule base (this KB) and the ground truth; Prof. Cao leads.

## Layout

- `kb/`: knowledge base (taxonomy, ontology, rules, reference data, playbooks as YAML) and its tools. `kb/sources/` holds the organizer handbook and sample case, Prof. Cao's ChordX protocol, the Ryde policy corpus and research notes.
- `validation/`: the independent validation pipeline and round 1 results for KB v0.1. Start with `validation/README.md`.
- `docs/NEXT_STEPS.md`: the plan for KB v0.2 and validation round 2, one session per step.

## Commands

- Build and check the KB: `python3 kb/build_kb.py` (must end with `ERROR 0 | WARN 0`). Faster: `--no-xlsx --no-fuzz`.
- Self-tests only: `python3 kb/tools/selftest.py` and `python3 kb/tools/selftest_v21.py` (policy v2.1, A6). Privacy scan: `python3 kb/tools/privacy_scan.py`.
- Validation scripts: `validation/tools/` (`freeze.py`, `evidence_check.py`, `scorecard.py`, `timeline.py`, `render_page.py`).

## Rules for every session

- Privacy (ChordX ONT.11): tables that map pseudonyms to real names stay on Jasper's computer and never enter this repo (`kb/private/` is ignored). Pseudonymize names, plates, phone numbers and account IDs before any cloud LLM call; keep places, dates, amounts and clause names. Never commit the ADP AppKey.
- This repo stays private: it contains the organizer's handbook and sample case and Prof. Cao's protocol.
- Work in DEP primitives: one step does one thing, is either D (a judgment) or E (a script), has an explicit input and output file, and logs its start and end with `python3 validation/tools/vlog.py start|end ...`.
- Stop rules: a D step has a 30-minute time box; a layer gets at most two review rounds; whatever is left goes to `kb/open_items.yaml`; a round that finds only MINOR issues ends that layer.
- Validators never edit the KB. Freeze it first (`validation/tools/freeze.py`) and check the hashes at the end.
- Every v0.2 build step is checked exactly as A1 was: engine rerun, fresh KB appliers on the affected cases, four reviewers each with a skeptic, a second round only if needed (see "How each step is checked" in `docs/NEXT_STEPS.md`; workflow `.claude/workflows/kb-step-check.js`).
- The reading of rider calls and messages (CW-F06's READ part and `rider_contact_reading` / `before_arrival_reading` in `kb/tools/engine_noshow.py`) is frozen (Jasper, 11 Oct, D34): do not extend it in later steps; record gaps in `kb/open_items.yaml`.
- Every rule element needs a source or an open FairRyde label. A rule's credibility is its weakest essential element: a Ryde condition extended by FairRyde is D.
- Writing style in docs and messages: no em dashes or en dashes; American spelling.

## Status (14 Oct 2026)

KB v0.1 was validated on 7 Oct: NO-GO (M1 0.90, M2 0.79, M3 0.65, M4 0.21, M5 0.73). KB v0.2 applied the fix list `validation/V5_scorecard/54_fix_list.json` (A1 to A5). KB v0.3.0 (step A6) adds the organizer's Ryde Dispute Resolution Policy v2.1 as the primary policy (profile `organizer_v2_1`, default for organizer cases; `ryde_2026` stays for E01 to E15 as regression) and the sample cases DISP-001, DISP-002 and DISP-003 (decisions D41 to D55 in `kb/open_items.yaml`). Next: validation round 2 on the frozen v0.3.0.
