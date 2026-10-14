# A4 check round 2 (last): brief for the reviewers

Commit range: `git diff f8a6abe ccc66b7`.

- The round 1 brief (`validation/build_checks/A4/round1_brief.md`) still describes what the step had to do.
- Round 1's findings and how each was handled are in `validation/build_checks/A4/04_round1_disposition.jsonl`.
- `git diff b36d911 ccc66b7` shows only the round 1 fixes.

## What changed in round 1

- **CLS-06 everywhere (F1, ADV-1, CONS-1, CONS-2):**
  - The rule, the DT-CW-NOSHOW precondition, PB-CW-NOSHOW step 1 and the engine now agree.
  - The engine (`canceling_party` in `kb/tools/engine_noshow.py`) reads four records: the reason, a `cancelled_by` field, the `driver_cancelled` and `rider_cancelled` events, and system messages.
  - Records that disagree or are silent, or a driver cancellation with no reason, give REQUEST_INFO (GEN-R-NEED-INFO) at tier HUMAN, with no fee ruling.
  - A rider cancellation goes to CW-RIDERCANCEL; any other driver or system cancellation goes to CW-OTHER.
  - A reclassified case with safety content still gets gate G4 and tier HUMAN (ADV-9).
  - Tests: V10 (now REQUEST_INFO) and V108 to V112.
- **Safety stand-in (CONS-3, ADV-7):**
  - `SAFETY_WORDS` is replaced by whole-word `SAFETY_PATTERNS`.
  - `a4_check` pins ordinary texts that must not fire and safety texts that must.
  - It is still a stand-in (D40 (a)).
- **CLS-01 wording (ADV-6, ADV-8, SG-3, SG-6, F7, ADV-12, CONS-14):**
  - Abuse or harassment of any kind is safety content (Code of Conduct item 5), with the item 5 and item 6 quotes. The rudeness carve-out is narrower.
  - Being stranded is tied to the driver's act, and "a rider under the influence" was removed.
  - The SE mapping now names SE-MISMATCH and SE-RECORDING. The zh was fixed.
  - SE-CONDUCT, EX-FEEDBACK and EX-LOCATION follow.
- **Toll engine (ADV-2, CONS-5, F4, ADV-10, F2):**
  - A single `itinerary_change(case)` in `kb/tools/engine_toll.py` is used by both `run()` and `fc_r01`. It returns True, None (a possible change) or False.
  - FC-R12 for a changed itinerary fires only when the recommended route can change the amount.
  - Tests: T43 to T46, and FC-R01 checks R9 and R10.
- **FC-F02 (ADV-4, SG-8):**
  - The recommended route is split at the point on it nearest the car at each accepted change.
  - The actual path is measured whole, so a deviation driven before the change stays a detour.
  - It now has a Ryde source and a FAIRRYDE note. FC-R12's text has the materiality condition.
- **CW-R08 (SG-1, SG-2, ADV-13):** a request accepted after the cut-off uses the app's ETA, and a driver already waiting at the pick-up counts as moving toward it. The labels were updated.
- **Other changes:**
  - EXP-03's verifier exempts only a verbatim clause quote (CONS-16).
  - CLS-03 applies to SE.
  - The REQUEST_INFO and GEN-R-NEED-INFO labels, the ontology rows, the playbooks' READ steps, the scope mapping and the engine labels and docstrings were updated.
  - The census was patched by `validation/build_checks/A4/census_a4.py`.
  - D39 (f) and D40 were updated, and NEXT_STEPS has a "To decide (A4)" line.
- **Recorded, not changed:** F3 and ADV-5 (the stand-in misses paraphrases, D40 (a)) and CONS-15 (no secondary EX-FEEDBACK claim in the engine, D40 (g)).
- **Out of the engine's scope:** E05 and E06 are now CW-RIDERCANCEL, which no engine rules on. The regression set (E01 to E04, E11) is unchanged: 5/5.

## What to check

- Check the fixes themselves: are they right and complete, and did they break anything?
- Check anything round 1 missed.

## Out of scope

- The rider-message reading is frozen (D34).
- The judgments recorded for Jasper in D39 and D40 (a) to (j) are Jasper's to make.
