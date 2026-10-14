# A6 round 1 note

The workflow was started by name and used a copy of kb-step-check.js that did not yet read `case_dir`, so the appliers for DISP-001, DISP-002 and DISP-003 looked for the cases in `validation/V4_e2e/cases` and found nothing (`02_applier_round1_INVALID.json`; the E01 and E04 appliers ran). The reviewers and skeptics were not affected. Round 2 runs the repository's workflow file by path so that the appliers read the pseudonymized organizer cases (answer blocks removed) from the scratchpad copy.
