"""Bring validation/round2/census.csv up to date with the rule elements step A4 changed (A4 check round 1). The A3 rows stay
as A3 wrote them, except the rows A4 superseded; each changed or added row says "A4" in its note. Labels do not change:
CLS-01 and CW-R08 stay D, FC-F01 stays B. Idempotent. Check round 2 updated the CLS-01, CW-F02B and CW-R08 notes.

    python3 validation/build_checks/A4/census_a4.py
"""
import csv
from pathlib import Path

CENSUS = Path(__file__).resolve().parents[2] / "round2" / "census.csv"

REPLACE = {
    ("CLS-01", "What counts as safety language: assault, harassment, threats, unsafe driving, accident, injury, intoxication"): {
        "element": "What counts as safety content: a definition read for meaning, with examples; unclear text counts as safety content; rudeness alone is feedback",
        "source": "FAIRRYDE (the definition by meaning, the examples Ryde does not name, the rule for unclear text and the line between rudeness and safety)",
        "element_label": "D", "counts_toward_label": "yes", "label_after": "D",
        "note": "A4 (FX6): replaces the word list of v0.1. Still FairRyde's design."},
    ("CLS-01", "Most examples of safety content: assault, sexual harassment, kidnapping, threats, abuse of any kind, personal questions and comments on appearance, reckless driving, alcohol and drugs, crimes, comments on race and similar grounds"): {
        "element": "Most examples of safety content: assault, sexual harassment, kidnapping, threats, abuse of any kind, personal questions and comments on appearance, reckless driving, alcohol and drugs, crimes, comments on race, ethnicity, national origin, disability, etc",
        "source": "RYDE-15395890865561 (Ryde Code of Conduct) items 5 to 8: 'Assault, harassment, or abuse of any kind will not be tolerated.', 'Do not commit crimes.', 'Reckless or dangerous driving that endangers passengers, pedestrians, or other road users is strictly prohibited.', 'Alcohol, drugs, and weapons are not tolerated.'; RYDE-33362721809049: 'Comments on race, ethnicity, national origin, disability, etc'",
        "note": "A4 (FX6 and check rounds 1 and 2): the examples quoted from Ryde, in Ryde's words; religion and other grounds read into 'etc' are in the FAIRRYDE row above."},
    ("CW-F02B", "The conflict with Ryde's older driver text (it counts from the arrival) is recorded"): {
        "note": "Documents the conflict; the rule does not rest on it. A4 (FX9) added the 2024 driver pages RYDE-20244064619161 and RYDE-33362932998937, which also count from 'I'm Here', to the note."},
    ("CW-R08", "A driver not moving toward the pick-up point makes it waivable"): {
        "element": "A driver not moving toward the pick-up point makes it waivable (a driver already waiting at the pick-up counts as moving; for an advance booking, only a driver who could no longer arrive by the assignment ETA plus the grace)",
        "note": "Unsourced in the KB, so FairRyde's until a source is added (open item, A3). Since A4 the advance-booking ETA is a counted D element too, so sources for both would make the rule C again."},
    ("FC-F01", "RECALCULATED when an added drop-off stop was accepted"): {
        "source": "RYDE-34883561600025 (driver article): 'You will receive a notification or a request pop up on your Ryde Driver app when riders request to change the drop-off and/or add an additional drop-off stop.'; RYDE-51399674412441 (rider article): 'The rider can add another destination, leading to a map confirmation (for multiple stops).', 'New destination and fare confirmation will be displayed.'",
        "note": "A4 (FX7): the two articles differ in date and rollout status, so B; the rider article's next step carries the fare confirmation (check round 2)."},
    ("CW-R08", "'Assignment ETA' for an advance booking"): {
        "source": "FAIRRYDE (FairRyde's reading: the scheduled time, or the app's ETA at acceptance for a request accepted after the CW-R02 cut-off)",
        "element_label": "D", "counts_toward_label": "yes", "label_after": "D",
        "note": "A4 (FX9) defines it; it is FairRyde's reading, so it counts and is D."},
}
ADD = [
    {"rule": "CLS-01", "label_before": "C", "element": "Most examples of safety content: assault, sexual harassment, kidnapping, threats, abuse of any kind, personal questions and comments on appearance, reckless driving, alcohol and drugs, crimes, comments on race, ethnicity, national origin, disability, etc",
     "source": "RYDE-15395890865561 (Ryde Code of Conduct) items 5 to 8: 'Assault, harassment, or abuse of any kind will not be tolerated.', 'Do not commit crimes.', 'Reckless or dangerous driving that endangers passengers, pedestrians, or other road users is strictly prohibited.', 'Alcohol, drugs, and weapons are not tolerated.'; RYDE-33362721809049: 'Comments on race, ethnicity, national origin, disability, etc'",
     "element_label": "A", "counts_toward_label": "yes", "label_after": "D", "note": "A4 (FX6 and check rounds 1 and 2): the examples quoted from Ryde, in Ryde's words; religion and other grounds read into 'etc' are in the FAIRRYDE row above."},
    {"rule": "FC-F01", "label_before": "B", "element": "RECALCULATED when an added drop-off stop was accepted",
     "source": "RYDE-34883561600025 (driver article): 'You will receive a notification or a request pop up on your Ryde Driver app when riders request to change the drop-off and/or add an additional drop-off stop.'; RYDE-51399674412441 (rider article): 'The rider can add another destination, leading to a map confirmation (for multiple stops).'",
     "element_label": "B", "counts_toward_label": "yes", "label_after": "B", "note": "A4 (FX7): the two articles differ in date and rollout status, so B; the rider article's next step, 'New destination and fare confirmation will be displayed.', carries the fare confirmation."},
]


def main():
    with CENSUS.open(newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        fields, rows = rd.fieldnames, list(rd)
    for r in rows:
        for (rid, old), new in REPLACE.items():
            if r["rule"] == rid and r["element"] == old:
                r.update(new)
    have = {(r["rule"], r["element"]) for r in rows}
    for a in ADD:
        if (a["rule"], a["element"]) not in have:
            i = max(k for k, r in enumerate(rows) if r["rule"] == a["rule"]) + 1
            rows.insert(i, a)
    with CENSUS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
