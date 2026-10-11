"""Reference evaluation of playbook PB-INTAKE + PB-CW-NOSHOW on an organizer-format case (DISP-002 and its variants).

Purpose: prove that the knowledge base is complete enough to decide a real sample, and show which rule, parameter and
evidence item produced each step. It is a verification tool for the knowledge base, not the product engine:
- there is no LLM, so the run-agreement (A) and rules-engine agreement (R) confidence terms are set to 1.0 and marked;
- the READ parts of CW-F06 (does the rider's statement contest presence, timing or place? does a rider call or message
  during the wait place the rider at the pick-up or contest presence?) are approximated by phrase lists here; at run time
  an LLM reads the text, and the decisive test checks whether another reading would matter.
"""
from __future__ import annotations

import copy
import math
import re
from datetime import datetime, timedelta

from kbload import KB

SAFETY_WORDS = ["assault", "harass", "threat", "unsafe", "accident", "injur", "drunk", "intoxicat", "grope",
                "weapon", "sexual", "abuse", "crash", "touched me", "police", "hit me", "fight"]
INJECTION_PATTERNS = [r"ignore (all |any |the )?(previous|prior|above) instructions", r"system prompt", r"you are now",
                      r"as the judge", r"rule in my favou?r", r"disregard (the )?(policy|rules)", r"```", r"\{\s*\"ruling\""]
CONTEST_PHRASES = [r"\bi was (at|there|on time|waiting|outside|at the)", r"never (showed|came|arrived)", r"\bwaited\b",
                   r"couldn'?t find", r"wasn'?t there", r"was not there", r"did ?n[o']t (arrive|come|show)", r"on time",
                   r"wrong (place|location|pin)", r"not at the pick", r"driver was not"]
# CW-F06, rider calls and messages during the wait: only content that places the rider at the pin or venue, or contests the
# driver's presence, the timing or the place, is STRONG; an admission of lateness or "coming" is not counter-evidence.
# Safety by construction: a message reads LATE only when it is made up entirely of known admission phrases and filler
# words. Any other word (a place, a question, a second person, a language the lists do not know) leaves it UNCLEAR, where
# the reading test applies (approval), never an automatic uphold.
_FP = r"(?:i'?\s?m|iam|i am|we'?re|we are)"                      # first person + be ("i'm", "im", "i m", "iam")
_WHO = r"(?:you|u|ur|you'?re|youre|uncle|aunty|auntie|driver|the driver|the car|your car|ur car|car|anyone|anybody|someone|somebody|nobody)"
_SPOT = (r"(?:lobby|lift lobby|void deck|carpark|car park|porch|entrance|exit|gate|door|kerb|curb|taxi stand|taxi bay|bus stop|"
         r"pick-?\s?up(?: point)?|pin|drop-?off point|blk|block|main road|guardhouse|guard house|driveway|letterbox|other side|"
         r"opposite|7-?11|seven eleven|mrt exit|lift landing|side gate|main gate|basement|level \d+ lobby)")
_NOT_YET = r"(?!\s+(?:soon|later|in\b|yet|liao\s+soon))"         # "reach soon", "here in 2 min" are admissions
RIDER_QUESTION_PHRASES = [                                      # the rider asks about or doubts the driver: contests presence
    rf"\b(?:are|r|is|will)\s+{_WHO}\s+(?:still\s+|already\s+|alr\s+)?(?:coming|on the way|on da way|omw|otw|here|there|near|nearby|reaching|arriving|outside|at|close|around|almost there|nearly there|be there)\b",
    rf"\b{_WHO}\s+(?:still\s+|already\s+|alr\s+|really\s+)?(?:coming|on the way|on da way|omw|otw|reaching|reach|reached|here|there|arrive|arrived|arriving|near|nearby|almost there|nearly there|at where|at which)\b",
    rf"\b{_WHO}\s+(?:haven'?t|have not|has not|hasn'?t|never|not yet|didn'?t|did not|not even|still not|not)\s+(?:arrive|arrived|come|came|reach|reached|show|showed|here|there)",
    rf"\b{_WHO}\s+(?:said|say|says|told|wrote|write)\b[^.!?]*", rf"\b{_WHO}\s+(?:are\s+|r\s+|is\s+|too\s+|very\s+|so\s+)*(?:early|late)\b",
    r"\b(?:where|wer|whr|mana)\b", r"\bwhich\s+(?:car|side|lane|entrance|exit|door|gate|block|blk|level)\b", r"\bhow\s+(?:long\s+more|far)\b",
    r"\b(?:when|what time)\s+(?:will|are|r|do)\s+(?:you|u)\b", r"\b(?:you|u)\s+left\b", r"\bdid\s+(?:you|u)\s+leave\b",
    r"\bplate\b"]
_ENDS_ASKING = r"\?\s*$"                                       # a message that ends in a question, other than asking the driver to wait
RIDER_SELF_PLACE_PHRASES = [                                    # the rider says where they are: at the pick-up or venue
    rf"\b{_FP}\s*(?:already\s+|alr\s+|still\s+|now\s+|just\s+|really\s+)?(?:here|there|downstairs|down already|at the pick|at pick|outside(?=\s*(?:$|[.,!?]|already|alr|now|liao|le|lah|leh|(?:the\s+)?{_SPOT}))){_NOT_YET}",
    rf"\b{_FP}\s+(?:already\s+|alr\s+|still\s+|now\s+|standing\s+|waiting\s+)?(?:here\s+)?(?:at|by|near|outside|in front of|beside)\b[^.?!,]*\b{_SPOT}\b",
    rf"(?<!almost )(?<!nearly )(?<!not )(?<!be )(?<!to )\b(?:at|outside|near|in front of|beside|by)\s+(?:the\s+|d\s+)?{_SPOT}\b(?!\s+(?:soon|later|in\b))",
    r"(?<!belum )(?<!nak )(?<!hampir )\b(?:here|reach|reached|arrived|downstairs|outside|sampai|dao le)\s+(?:already|alr|liao|le|lah|leh|now|edy)\b",
    r"(?<!coming )(?<!come )(?<!going )(?<!way )(?<!otw )(?<!omw )(?<!walking )(?<!heading )(?<!rushing )(?<!running )\bdown\s+(?:already|alr|liao|le|lah|leh|edy)\b",
    r"\b(?:already|alr|dah|sudah)\s+(?:here|there|downstairs|outside|at|reach|reached|sampai)\b",
    rf"\b(?:i|we)\s+(?:reach|reached|arrived|am here|have arrived|have reached|here|there|at|kat|downstairs)\b{_NOT_YET}",
    rf"^\W*(?:reach|reached|here+|arrived|imhere|downstairs)\b{_NOT_YET}", r"\bimhere\b", r"📍",
    r"\b(?:i|we|i'?m|im|i am)\s+(?:already\s+|been\s+|still\s+)?(?:wait|waited|waiting)\b(?!\s+for\s+(?:the\s+|my\s+)?(?:lift|elevator|bus|train|food|bill|grab|taxi))",
    r"^\W*(?:waiting|waited)\b(?!\s+for\s+(?:the\s+|my\s+)?(?:lift|elevator|bus|train|food|bill))", r"\bwait(?:ed|ing)?\s+(?:for\s+)?(?:you|u)\b",
    r"\bbeen\s+(?:here|there|waiting)\b", r"\bwait\s+so\s+long\b", r"^\W*\d+\s*(?:min|mins|minute|minutes)\s+(?:already|alr|liao|le)\b",
    r"\b(?:dah|sudah|saya)\s+tunggu\b|\btunggu\s+\d+", r"\bkat\s+(?:bawah|lobby|lobi|\w+)\b", r"(?<!belum )(?<!nak )(?<!hampir )\b(?:dah\s+)?sampai\b", r"\bwo\s+dao\s+le\b|\bdao\s+le\b",
    r"(?<!快)(?<!还没)(?<!没)到了|在楼下|到楼下|我在(?:楼下|门口|大堂|大厅|这里|这边|上车点|路边)",
    r"\b(?:standing|waiting|sitting)\s+(?:near|at|outside|beside|by|in front of)\b",
    rf"\bi\s+was\s+(?:here|there|waiting|at\s+(?:the\s+)?{_SPOT})\b", r"\b(?:i|we)\s+(?:can\s+)?see\s+(?:you|u|your car|ur car|the car)\b"]
RIDER_CONTEST_PHRASES = [                                       # the rider contests the driver's presence, the timing or the place
    r"\b(?:don'?t|dont|do not|can'?t|cannot|cant|couldn'?t|could not|never|didn'?t)\s+(?:see|find|spot)\b",
    r"\bno\s+(?:car|driver|one|body)\b", r"\bnobody\b", r"\b(?:no|not)\s+(?:car|driver)\s+(?:here|there)\b",
    r"\b(?:you'?re|you are|u r|ur|youre|u)\s+not\s+(?:here|there|at)\b", r"\b(?:your|ur|the)\s+car\b[^.?!]*\b(?:is|was)\s+(?:not|nowhere)\b",
    r"\bwrong\b", r"\b(?:right|correct)\s+(?:place|location|pin|spot|address)\b",
    r"\b(?:pin|location|address|pick-?\s?up(?: point)?|map|place|side|entrance)\s+(?:is|was|r)\s+(?:wrong|incorrect|correct|right)\b",
    r"\b(?:you'?re|you are|u r|ur|driver|car)\s+(?:is\s+)?not\s+at\s+the\s+pick", r"\b(?:i'?m|im|i am|i was)\s+not\s+late\b",
    r"\bapp\s+(?:says|say|said|shows|show)\b"]
RIDER_PLACE_PHRASES = RIDER_QUESTION_PHRASES + RIDER_SELF_PLACE_PHRASES + RIDER_CONTEST_PHRASES
RIDER_FAULT_PHRASES = [r"\bmy\s+(?:bad|mistake|fault)\b", r"\b(?:i|we|i'?ve|i have)\s+(?:put|set|entered|chose|selected|keyed in|pinned|went to|walked to|was at|were at|booked)\s+(?:the\s+|a\s+)?wrong\b",
                       r"\bsorry\b[^.?!]*\bwrong\b", r"\bwrong\b[^.?!]*\bsorry\b"]
RIDER_LATE_CORE = [                                             # first-person admissions of lateness or of still being on the way
    r"(?<!you )(?<!u )(?<!not )(?<!uncle )(?<!driver )\b(?:coming|comin|cming)(?:\s+(?:down|out|over|now|already|liao|soon))*\b(?!\s*\?)",
    r"\b(?:on\s+(?:my|the|da)\s+way|omw|otw)(?:\s+(?:down|out|over|now|already|liao))*\b(?!\s*\?)", r"\bgetting\s+ready\b", r"\brunning\s+late\b",
    r"(?<!not )(?<!you )(?<!u )(?<!driver )(?<!uncle )\b(?:a bit\s+|a little\s+|abit\s+|so\s+|very\s+)?late(?:\s+(?:a bit|abit|a little))?\b", r"\boverslept\b",
    r"\b(?:walking|heading|going|rushing|running)(?:\s+(?:over|there|down|out|now|to))?\b", r"\b(?:almost|nearly)\s+(?:there|reach|reaching|down|at|here)\b",
    r"\b(?:abt|about)\s+to\s+reach\b", r"\breaching\b", r"\b(?:reach|here|there|down|arrive|arriving)\s+soon\b", rf"\b{_FP}\s+there\s+soon\b",
    r"\b(?:i'm|i)\s+(?:still\s+)?not\s+(?:yet\s+)?(?:reach|reached|there|here|down)(?:\s+yet)?\b", r"^\W*not\s+yet\s+(?:reach|reached|there|here|down)\b",
    r"\bnot\s+coming\s+down\s+yet\b",
    r"\b(?:i'?ll|i will|will|i'?m going to|gonna)\s+be\s+(?:right\s+)?(?:down|there|out)\b", r"^\W*be\s+(?:there|down|out)\b",
    r"\bleaving\s+(?:now|the house|my house|home|office|work)\b", r"\bjust\s+left\b",
    r"\bstill\s+(?:at home|at work|upstairs|getting|inside|packing|showering|bathing|eating)\b",
    r"\b(?:still\s+)?(?:in|at)\s+(?:the\s+|my\s+)?(?:lift|elevator|toilet|shower|bathroom|office|house|room|train|bus(?!\s+stop)|mrt(?!\s+exit)|mall|market|clinic|meeting|traffic|jam|gym|kopitiam|atm)\b", rf"\b{_FP}\s+(?:still\s+)?(?:at\s+)?(?:home|work)\b(?:\s+still)?",
    r"\b(?:waiting|wait)\s+for\s+(?:the\s+|my\s+)?(?:lift|elevator)\b", r"\b(?:lift|elevator)\s+(?:very\s+|so\s+|damn\s+)?(?:slow|spoil|broken)\b",
    r"\b(?:in|taking|take|took)\s+(?:the\s+)?(?:lift|elevator)\b", r"\bstuck\s+in\s+(?:the\s+)?(?:jam|traffic|lift)\b", r"\bwalking\s+down\s+the\s+stairs\b",
    r"\bgive\s+me\s+(?:a\s+)?(?:\d+|few|a few|one|two|five)\b", r"\bgimme\b", r"\bneed\s+(?:\d+|a few|few)\s+(?:more\s+)?(?:min|mins|minutes?)\b",
    r"\b(?:\d+|one|two|few|a few)\s+more\s+(?:min|mins|minute|minutes|sec|secs)\b", r"🏃",
    r"^\W*\d+\s*(?:min|mins|minute|minutes)\W*$",                 # a bare duration: "5 min"
    r"在路上|快到了|马上到|马上下来|还没到|我在家|等一下|稍等", r"\bbelum\s+(?:sampai|turun|siap)\b", r"\b(?:nak|hampir)\s+sampai\b",
    r"\bmasih\s+(?:di\s+)?rumah\b",
    r"(?<!i )(?<!i've )(?<!been )(?<!we )\bwait(?:\s+(?:ah|ya))?\s+(?:for\s+me|another\s+\d+|\d+\s*(?:more\s+)?(?:min|mins|minutes?))\b"]
RIDER_WAIT_REQUEST = (r"\b(?:can|could|pls|please|plz)?\s*(?:you\s+|u\s+)?wait\b(?:\s+(?:ah|ya))?(?:\s+for\s+me)?(?:\s+(?:a\s+)?(?:bit|while|moment|min|minute|sec|"
                      r"another\s+(?:\d+\s*(?:min|mins|minutes?)|few\s+(?:min|mins|minutes))|\d+\s*(?:more\s+)?(?:min|mins|minutes?)))?\s*(?:ah|ya|ok)?\s*\??")
_FILLER = (r"\b(?:sorry|sry|soz|uncle|aunty|auntie|bro|boss|sir|madam|maam|pls|plz|please|ok|okay|k|kk|hi|hey|hello|lah|la|leh|ah|lor|liao|le|"
           r"hor|meh|ya|yah|yeah|now|just|already|alr|very|so|a|bit|abit|little|the|my|me|i'm|i'll|ill|i|will|be|in|more|and|then|still|"
           r"another|few|for|while|moment|slow|thanks|thank you|thx|sec|secs|seconds|haha+|lol|really|soon|right|be|is|it|its|it'?s|"
           r"to|from|d|da|ready|can|wait|min|mins|minute|minutes|one|two|three|five|ten|first|need|again|sorrysorry|\d+)\b")
_FROM_TO = rf"\b(?:from|to|towards)\s+(?!reach\b|come\b|be\b)(?:the\s+|my\s+|d\s+)?(?:{_SPOT}|[a-z0-9'-]+)(?:\s+[a-z0-9'-]+)?"
RIDER_ACK = r"\s*(?:ok(?:ay|ie|ies)?|k|kk|okok|noted|ok noted|ok can|thanks?(?: you)?|ok thanks|thx|ty|alright|👍|ok 👍)\s*[.!]*\s*"
SOFT_FLAGS = ("SPEED_INCONSISTENT", "PIN_VENUE_MISMATCH", "SPARSE_GPS", "TIMER_ANCHOR_MISMATCH", "GPS_OUTLIER")


def T(s: str) -> datetime:
    return datetime.fromisoformat(s)


def hav(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------------------------- evidence
def venue_for(kb: KB, case: dict):
    name = (case.get("trip_data", {}).get("pickup_location", {}).get("name") or "").lower()
    return next((v for v in kb.tables["VENUES"]["rows"] if v["name"].lower() == name), None)


def evidence_index(case: dict, kb: KB | None = None) -> dict:
    """Immutable, ID-addressed evidence items (ontology ENT-EVIDENCE). With kb, adds the OneMap lookup E-GEO-01 when the
    pick-up venue is in the reference table (a reference lookup: cited, but never counted as evidence in AUTH-05)."""
    E = {}
    E["E-TKT-01"] = {"type": "statement", "tier": "D", "path": "dispute_ticket", "ts": case["dispute_ticket"]["filed_at"],
                     "summary": "Ticket; the description is the rider's own statement (tier D); filed_at is a server field.",
                     "untrusted_text": True}
    E["E-PRF-R"] = {"type": "profile_stat", "tier": "A", "path": "rider_profile", "ts": None, "summary": "Rider profile (history, rating, flags). Never decisive (GEN-R03)."}
    E["E-PRF-D"] = {"type": "profile_stat", "tier": "A", "path": "driver_profile", "ts": None, "summary": "Driver profile (history, rating, flags). Never decisive (GEN-R03)."}
    E["E-TRP-01"] = {"type": "trip_record", "tier": "A", "path": "trip_data", "ts": None, "summary": "Trip record (times, fee, reason)."}
    for i, g in enumerate(case.get("gps_telemetry", []), 1):
        E[f"E-GPS-{i:02d}"] = {"type": "gps_ping", "tier": "B", "path": f"gps_telemetry[{i-1}]", "ts": g["timestamp"],
                               "summary": f"{g['timestamp'][11:19]} {g['status']} speed {g['speed_kmh']} km/h"}
    for i, c in enumerate(case.get("chat_logs", []), 1):
        typ = {"message": "chat_message", "call": "call_log", "system": "app_event"}.get(c["type"], "other")
        tier = {"chat_message": "C", "call_log": "A", "app_event": "A"}.get(typ, "D")
        E[f"E-CHT-{i:02d}"] = {"type": typ, "tier": tier, "path": f"chat_logs[{i-1}]", "ts": c["timestamp"],
                               "summary": f"{c['timestamp'][11:19]} {c['sender']} {c['type']}", "untrusted_text": c["type"] == "message"}
    for i, a in enumerate(case.get("app_events", []), 1):
        E[f"E-APP-{i:02d}"] = {"type": "app_event", "tier": "A", "path": f"app_events[{i-1}]", "ts": a["timestamp"],
                               "summary": f"{a['timestamp'][11:19]} {a['event_type']}"}
    if case.get("cancellation_policy"):
        E["E-POL-01"] = {"type": "policy_clause", "tier": "A", "path": "cancellation_policy", "ts": None, "summary": "Policy object embedded in the case."}
    for i, g in enumerate(case.get("rider_gps_telemetry") or [], 1):
        E[f"E-RGPS-{i:02d}"] = {"type": "gps_ping", "tier": "B", "path": f"rider_gps_telemetry[{i-1}]", "ts": g["timestamp"], "summary": "Rider GPS"}
    if kb is not None:
        v = venue_for(kb, case)
        if v:
            E["E-GEO-01"] = {"type": "reference_lookup", "tier": "A", "path": "reference_data.tables.VENUES", "ts": None,
                             "summary": f"OneMap address of {v['name']} ({v['lat']:.5f}, {v['lng']:.5f}); a reference, not evidence (AUTH-05)"}
    return E


def _ev_id(prefix: str, case: dict, key: str, match) -> list[str]:
    return [f"{prefix}-{i:02d}" for i, x in enumerate(case.get(key, []), 1) if match(x)]


def case_overrides(kb: KB, case: dict) -> dict:
    """META-01: build profile organizer_case from the case's own policy object (field, parameter, scale)."""
    pol = case.get("cancellation_policy") or {}
    out = {}
    for m in kb.y["ontology"]["disp002_mapping"]:
        if not m.get("param") or not m["path"].startswith("cancellation_policy."):
            continue
        field = m["path"].split(".", 1)[1]
        if field not in pol:
            continue
        if m["param"] == "FEE_PAYEE":
            out["FEE_PAYEE"] = "DRIVER" if "driver" in str(pol[field]).lower() else "PLATFORM"
        else:
            v = float(pol[field]) * float(m.get("scale", 1))
            out[m["param"]] = int(v) if v.is_integer() and m.get("scale", 1) != 1 else v
    return out


# ---------------------------------------------------------------------------------------------- trace
class Trace:
    def __init__(self, profile, overrides):
        self.profile = profile
        self.overrides = overrides or {}
        self.steps, self.flags, self.reasons, self.rules_on_path, self.notes, self.also = [], [], [], [], [], []
        self.rules_used = []      # rules that changed a flag, the remedy or the tier but are not on the decisive path
        self.findings, self.params_used, self.remedy = {}, {}, {}
        self.outcome = None
        self.dt_row = None
        self.dt_row_credibility = None
        self.reclassified_to = None
        self.policy_gap = []
        self.fallbacks = []
        self.early_press = False
        self.fraud_detail, self.arrival_detail, self.presence_detail = {}, {}, {}
        self.wait_start = None
        self.wait_start_from = None   # anchor, arrival (confirmed arrival later than the anchor) or ping (later GPS confirmation)
        self.cmp_fallback = False
        self.injection_authors = []
        self.fraud = []
        self.relation = None
        self.claim_type = None
        self.rider_contests = False
        self.rider_at_venue_claim = False
        self.pin_mismatch = False
        self.venue_name = None
        self.margin = 0
        self.spread_max = 0
        self.contact_detail = {}

    def flag(self, f):
        if f not in self.flags:
            self.flags.append(f)

    def path(self, *rids):
        """decisive_definition: eligibility rules that could stop the case, fact rules feeding the row, the row's rules."""
        for r in rids:
            if r not in self.rules_on_path:
                self.rules_on_path.append(r)

    def use(self, *rids):
        for r in rids:
            if r not in self.rules_used and r not in self.rules_on_path:
                self.rules_used.append(r)

    def step(self, pb, n, rule, result, evidence=(), status="done", note=""):
        self.steps.append({"playbook": pb, "n": n, "rule": rule, "status": status, "result": result, "evidence": list(evidence), "note": note})

    def finding(self, code, value, unit="", status="established", basis=(), rule="", params=()):
        self.findings[code] = {"value": value, "unit": unit, "status": status, "basis": list(basis), "rule": rule, "params": list(params)}


def contests_statement(text: str) -> bool:
    """Proxy for the READ part of CW-F06: does the statement contest presence, timing or place?"""
    t = (text or "").lower()
    return any(re.search(p, t) for p in CONTEST_PHRASES)


def _rider_text(text: str) -> str:
    t = re.sub(r"[\u2018\u2019\u02bc\uff07`\u00b4]", "'", (text or "").lower()).replace("\uff1f", "?").replace("\uff0c", ",")
    t = re.sub(r"\b(?:i\s?'\s?m|i\s+m|iam|im)\b", "i'm", t)            # "I m", "Im", "Iam" -> "i'm"
    return re.sub(r"\s+", " ", t).strip()


def rider_contact_reading(c: dict) -> str:
    """Proxy for the READ part of CW-F06 on one rider call or message during the wait: PLACES (at the pin or venue, or contests
    presence, timing or place, including asking where the driver is), LATE (admits being late or still on the way, and says
    nothing else the lists do not know), NEUTRAL (an acknowledgment such as 'ok') or UNCLEAR (a call, whose words are not
    recorded, or a message that fits neither reading or both)."""
    if c["type"] != "message":
        return "UNCLEAR"
    t = _rider_text(c.get("content"))
    if re.fullmatch(RIDER_ACK, t):
        return "NEUTRAL"
    places = (any(re.search(p, t) for p in RIDER_PLACE_PHRASES)
              or bool(re.search(_ENDS_ASKING, re.sub(r"\b(?:can|could|pls|please)?\s*(?:you\s+|u\s+)?wait\b[^?]*\?\s*$", "", t))))
    fault = any(re.search(p, t) for p in RIDER_FAULT_PHRASES)
    asked = t
    for p in RIDER_QUESTION_PHRASES:               # "are you coming", "u on the way ah": about the driver, not an admission
        asked = re.sub(p, " ", asked)
    late = any(re.search(p, asked) for p in RIDER_LATE_CORE)
    if places:
        return "UNCLEAR" if (late or fault) else "PLACES"
    if not late or fault:
        return "UNCLEAR"
    rest = asked                                   # LATE only if nothing but admissions, requests to wait and filler is left
    for p in [RIDER_WAIT_REQUEST, _FROM_TO] + RIDER_LATE_CORE:
        rest = re.sub(p, " ", rest)
    rest = re.sub(_FILLER, " ", rest)
    rest = re.sub(r"[\s.,!~\u2026'\"()\-:;]+", "", rest)
    return "LATE" if not rest else "UNCLEAR"


_PLACE_WORDS = rf"(?<!to )(?<!to the )(?<!towards )\b(?:here|reach|reached|arrived|downstairs|outside|{_SPOT}|location|address)\b"
_PICKUP_INSTRUCTION = (r"(?:^|[.,!?;]\s*|\b(?:pls|please|plz|can you|could you|can u|pls can|then)\s+)"   # imperative position only
                       r"(?:pick\s+(?:me\s+)?up|meet(?:\s+me)?|wait(?:\s+for\s+me)?|stop|park|come|drop\s+me)\s+"
                       r"(?:at|near|outside|by|beside|in front of|opposite)\b[^.!?,]*")
_LEFTOVER = (r"\b(?:are|r|is|am|was|you|u|ur|your|yours|uncle|aunty|driver|did|do|does|can|could|will|would|how|what|when|which|"
             r"who|why|where|wer|whr|mana|car|a|an|of|on|yet|not|no|lah|ya)\b|[我你吗呢了的啊吧呀]")      # question and filler words
_FUTURE = r"\b(?:i'll|i will|will be|i'm going to|gonna|meet you|meet u|see you|see u|later|tomorrow|tmr)\b"


def _asks_driver(text: str | None) -> bool:
    """A driver message that asks the rider something (a question mark anywhere, ASCII or full-width)."""
    return "?" in (text or "").replace("\uff1f", "?")


def before_arrival_reading(c: dict, place_names: list[str], answers_question: bool = False) -> str | None:
    """D30 proxy: does a rider message sent before the wait count? PLACES (it clearly places the rider at the pick-up now),
    UNCLEAR (it may; the reading test applies) or None (it does not count). Fail-safe by construction: a message is dropped
    only when it is positively known not to be a placement: a call, an admission, an acknowledgment that answers no driver
    question, or nothing but questions about the driver, contests, pick-up instructions, admissions and filler. Anything
    else counts, including words the lists do not know."""
    if c["type"] != "message":
        return None
    r = rider_contact_reading(c)
    if r == "NEUTRAL":
        return "UNCLEAR" if answers_question else None
    if r == "LATE":
        return None
    t = _rider_text(c.get("content"))
    qrest = re.sub(_PICKUP_INSTRUCTION, " ", t)       # what is left once instructions and questions about the driver are set aside
    for p_ in RIDER_QUESTION_PHRASES + RIDER_CONTEST_PHRASES:
        qrest = re.sub(p_, " ", qrest)
    if any(re.search(p_, qrest) for p_ in RIDER_SELF_PLACE_PHRASES):
        return "PLACES" if r == "PLACES" and not re.search(_FUTURE, t) else "UNCLEAR"
    rest = qrest
    for p_ in [RIDER_WAIT_REQUEST] + RIDER_LATE_CORE:
        rest = re.sub(p_, " ", rest)
    rest = re.sub(_FILLER, " ", rest)
    rest = re.sub(_LEFTOVER, " ", rest)
    rest = re.sub(r"[\s.,!?~\u2026'\"()\-:;]+", "", rest)
    return "UNCLEAR" if (rest or any(n and n in t for n in place_names)) else None


def evaluate(kb: KB, case: dict, profile: str | None = None, overrides: dict | None = None,
             force_reading: str | None = None, alt_start: str | None = None, contact_reading: str | None = None) -> Trace:
    """force_reading: NONE or WEAK to test another reading of the rider's statement (decisive test, clause 1).
    alt_start: "anchor" counts the wait from the anchor without CW-F03B (decisive test of that FairRyde reading).
    contact_reading: "STRONG" reads the rider's unclear calls and messages during the wait as placing the rider at the
    pick-up (decisive test of CW-F06's READ part, clause 1)."""
    tk, t = case["dispute_ticket"], case["trip_data"]
    ev, chat = case.get("app_events", []), case.get("chat_logs", [])
    gps_raw = case.get("gps_telemetry", []) or []
    gps_no = {id(g): i + 1 for i, g in enumerate(gps_raw)}          # E-GPS-nn follows the case file's order
    gps = sorted(gps_raw, key=lambda g: g["timestamp"])               # the rules read pings in time order
    gid = lambda g: f"E-GPS-{gps_no[id(g)]:02d}"
    forced = profile is not None
    if profile is None:
        profile = "organizer_case" if case.get("cancellation_policy") else "ryde_2026"
    case_ov = case_overrides(kb, case) if profile == "organizer_case" else {}
    ov = dict(case_ov)
    ov.update(overrides or {})
    tr = Trace(profile, overrides or {})

    def P(name):
        e = kb.param(name, profile, ov)
        if e is None:
            raise KeyError(name)
        info = {"value": e.get("value"), "credibility": e.get("credibility"), "plausible_range": e.get("plausible_range"),
                "flag_only": e.get("flag_only", False)}
        if name in case_ov and name not in (overrides or {}):
            info["source"], info["credibility"] = "case policy object", "A"
        elif e.get("fallback_from"):
            info["source"] = f"{e['fallback_from']} (META-01 fallback: not in the case's policy object)"
        elif name == "THRESHOLD_COMPARISON" and tr.cmp_fallback:
            info["source"] = "ryde_2026 (follows the fallback threshold, META-01)"
        tr.params_used[name] = info
        return e.get("value")

    # party text with its author: GEN-R04 treats it as evidence, and AUTH-02 trigger 10 needs to know who wrote it
    filer = kb.resolve("TX-ROLE", tk.get("filed_by")) or "OTHER"
    texts = [(filer, tk.get("description", "") or "")] + [(kb.resolve("TX-ROLE", c["sender"]) or "OTHER", c["content"])
                                                           for c in chat if c["type"] == "message"]
    free_text = [x for _, x in texts]

    # ---------------- PB-INTAKE
    tr.injection_authors = sorted({who for who, x in texts if any(re.search(p, x, re.I) for p in INJECTION_PATTERNS)})
    if tr.injection_authors:
        tr.flag("INJECTION_SUSPECTED")
    tr.step("PB-INTAKE", 1, "GEN-R04", f"instruction-like text from {', '.join(tr.injection_authors)} flagged and ignored" if tr.injection_authors
            else "no instructions found in party text", ["E-TKT-01"] + _ev_id("E-CHT", case, "chat_logs", lambda c: c["type"] == "message"))
    safety_hits = sorted({w for w in SAFETY_WORDS for x in free_text if w in x.lower()})
    tr.findings["_safety"] = bool(safety_hits)
    tr.step("PB-INTAKE", 2, "CLS-01", f"safety words: {safety_hits}" if safety_hits else "no safety language", ["E-TKT-01"])
    tr.claim_type = kb.resolve("TX-CASE", tk["dispute_type"])
    tr.step("PB-INTAKE", 3, "CLS-05, CLS-02, CLS-04",
            f"dispute_type {tk['dispute_type']!r} -> {tr.claim_type}; one claim contesting CANCELLATION_FEE S${t['cancellation_fee']:.2f}"
            + ("; a safety claim is added as the primary claim" if safety_hits else ""), ["E-TKT-01", "E-TRP-01.cancellation_fee"])
    tr.step("PB-INTAKE", 4, "CLS-03", "contested charge present: not routed to support", ["E-TRP-01.cancellation_fee"])
    trip_ok = tk["trip_id"] == t["trip_id"]
    tr.step("PB-INTAKE", 5, "MAT-01", f"trip {t['trip_id']} {'matches' if trip_ok else 'DOES NOT match'} the ticket", ["E-TKT-01.trip_id", "E-TRP-01.trip_id"])
    tr.relation = "NEW"
    tr.step("PB-INTAKE", 6, "MAT-02", "no ticket index in the case file; treated as NEW (at run time the ticket index is checked)", ["E-TKT-01"], status="missing")
    tr.step("PB-INTAKE", 7, "MAT-03", "not an appeal", ["E-TKT-01.status"], status="not_applicable")
    if forced and profile != "organizer_case" and case.get("cancellation_policy"):
        why = "forced for a what-if; META-01 would choose organizer_case because the case embeds a policy object"
    elif profile == "organizer_case":
        why = "the case embeds cancellation_policy; parameters read from it: " + ", ".join(f"{k}={v}" for k, v in case_ov.items())
    else:
        why = "no embedded policy object"
    trip_date = (t.get("cancellation_time") or t.get("scheduled_time") or "")[:10]
    eff = kb.y["reference_data"]["profiles"][profile].get("effective_from")
    eff_ok = (eff in (None, "case-specific")) or (trip_date >= str(eff))
    if not eff_ok:
        tr.policy_gap.append(("META-02", f"the {profile} profile starts on {eff}, after the trip date {trip_date}"))
        tr.path("META-02")
    if profile == "organizer_case":
        tr.fallbacks = [n for n in kb.y["reference_data"]["profiles"]["organizer_case"].get("case_fields", {}) if n not in case_ov]
        if "NO_SHOW_THRESHOLD_S" in tr.fallbacks and "THRESHOLD_COMPARISON" not in (overrides or {}):
            fb = kb.y["reference_data"]["profiles"]["organizer_case"].get("fallback_profile", "ryde_2026")
            ov["THRESHOLD_COMPARISON"] = kb.pval("THRESHOLD_COMPARISON", fb)     # the comparison belongs to the threshold it came with
            tr.cmp_fallback = True
    tr.step("PB-INTAKE", 8, "META-01, META-02", f"profile {profile} ({why}); effective from {eff}: "
            + ("in force" if eff_ok else "NOT in force on the trip date, so there are no values to apply (policy gap)")
            + (f"; not in the policy object, so the Ryde value applies (META-01): {', '.join(tr.fallbacks)}" if tr.fallbacks else ""),
            ["E-POL-01"] if case.get("cancellation_policy") else [])
    bbox = P("SG_BBOX")
    pts = [(g["lat"], g["lng"]) for g in gps] + [(t["pickup_location"]["lat"], t["pickup_location"]["lng"]), (t["dropoff_location"]["lat"], t["dropoff_location"]["lng"])]
    in_box = all(bbox[0] <= la <= bbox[2] and bbox[1] <= lo <= bbox[3] for la, lo in pts)
    times = [T(a["timestamp"]) for a in ev]
    ordered = times == sorted(times) and T(tk["filed_at"]) >= T(t["cancellation_time"])
    tr.step("PB-INTAKE", 9, "DQ-03, DQ-04", f"coordinates in Singapore: {in_box}; timeline ordered and filed after the trip: {ordered}", ["E-TRP-01", "E-GPS-*"])

    pb = "PB-CW-NOSHOW"
    # 1 precondition: driver no-show cancellation
    by_rider = any(re.search(r"cancel+ed by (the )?rider", c["content"], re.I) for c in chat if c["type"] == "system")
    drv_cancel = t.get("cancellation_reason") == "rider_no_show" and not by_rider
    tr.step(pb, 1, "CLS-02, CW-R03", "driver canceled with reason rider_no_show" if drv_cancel else "not a driver no-show cancellation: reclassify",
            ["E-TRP-01.cancellation_reason"] + _ev_id("E-CHT", case, "chat_logs", lambda c: c["type"] == "system"))
    if not drv_cancel:
        tr.reclassified_to = "CW-RIDERCANCEL" if t.get("cancellation_reason") == "rider_cancelled" else "CW-OTHER"
        tr.amount_at_stake = float(t.get("cancellation_fee") or 0)
        tr.confidence = {"A": None, "M": None, "E": None, "R": None, "C": None, "assumed": [], "evidence_present": {}, "soft_flags": []}
        return tr

    # 2 MAT-04 window
    days = (T(tk["filed_at"]) - T(t["cancellation_time"])).total_seconds() / 86400
    window = P("WAIVER_WINDOW_DAYS")
    tr.finding("F-FILING-WINDOW", round(days, 3), "days", basis=["E-TKT-01.filed_at", "E-TRP-01.cancellation_time"], rule="MAT-04", params=["WAIVER_WINDOW_DAYS"])
    tr.path("MAT-04")
    tr.step(pb, 2, "MAT-04", f"filed {days:.2f} days after the trip (window {window} days: {'inside' if days <= window else 'OUTSIDE'})",
            ["E-TKT-01.filed_at", "E-TRP-01.cancellation_time"])
    if days > window:
        tr.flag("OUT_OF_WINDOW")

    # 3 CW-R00 scope (Ryde's scope rule also applies to organizer cases, because the policy object does not say which services it covers)
    svc_raw = t.get("service_type")
    svc = kb.resolve("TX-SERVICE", svc_raw) if svc_raw else None
    tr.path("CW-R00")
    if svc == "RYDETAXI":
        tr.policy_gap.append(("CW-R00", "RydeTAXI is outside the cancellation policy and no written rule covers its no-show fee"))
        tr.step(pb, 3, "CW-R00", "service RYDETAXI: outside the cancellation policy (policy gap, escalate per GEN-R07)", ["E-TRP-01.service_type"])
    elif svc_raw is None:
        tr.step(pb, 3, "CW-R00", "service type not recorded; treated as in scope (the policy covers every service except RydeTAXI)", ["E-TRP-01"], status="missing")
    else:
        tr.step(pb, 3, "CW-R00", f"service {svc or svc_raw}: in scope", ["E-TRP-01.service_type"])

    # 4 CW-F01 booking type
    booked = next((a for a in ev if a["event_type"] == "booking_confirmed"), None)
    assigned = next((a for a in ev if a["event_type"] == "driver_assigned"), None)
    m = re.search(r"ETA (\d+) min", assigned["details"]) if assigned else None
    eta_min = int(m.group(1)) if m else None
    match_s = (T(assigned["timestamp"]) - T(booked["timestamp"])).total_seconds() if booked and assigned else None
    recorded = t.get("booking_type")
    infer_match, infer_eta = P("BOOKING_INFER_MATCH_S"), P("BOOKING_INFER_ETA_S")
    if recorded:
        btype, bnote = kb.resolve("TX-BOOKING", recorded), "recorded"
    elif match_s is None or not t.get("scheduled_time"):   # nothing to infer from: CW-F01's "otherwise ADVANCE", and a person checks
        btype, bnote = "ADVANCE", "not recorded and not inferable (booking or assignment record missing); ADVANCE as CW-F01 says, records missing"
        tr.flag("BOOKING_TYPE_INFERRED")
        tr.flag("RECORDS_MISSING")
    else:
        eta_gap = abs(T(assigned["timestamp"]).timestamp() + (eta_min or 0) * 60 - T(t["scheduled_time"]).timestamp())
        btype = "ON_DEMAND" if (match_s <= infer_match and eta_min is not None and eta_gap <= infer_eta) else "ADVANCE"
        bnote = f"inferred: matched {match_s:.0f} s after booking, ETA lands {eta_gap:.0f} s from scheduled_time"
        tr.flag("BOOKING_TYPE_INFERRED")
    i_book = _ev_id("E-APP", case, "app_events", lambda a: a["event_type"] in ("booking_confirmed", "driver_assigned"))
    tr.finding("F-BOOKING-TYPE", btype, basis=i_book + ["E-TRP-01.scheduled_time"], rule="CW-F01",
               params=[] if recorded else ["BOOKING_INFER_MATCH_S", "BOOKING_INFER_ETA_S"], status="established" if recorded else "inferred")
    tr.step(pb, 4, "CW-F01", f"{btype} ({bnote})", i_book + ["E-TRP-01.scheduled_time"])

    # 5 CW-F02 / CW-F02B anchor
    arrived_ev = next((a for a in ev if a["event_type"] == "driver_arrived"), None)
    t_arr = T(arrived_ev["timestamp"]) if arrived_ev else (T(t["driver_arrival_time"]) if t.get("driver_arrival_time") else None)
    i_arr = ["E-APP-%02d" % (ev.index(arrived_ev) + 1)] if arrived_ev else (["E-TRP-01.driver_arrival_time"] if t.get("driver_arrival_time") else [])
    anchor_field = P("WAIT_ANCHOR_FIELD")
    end = T(t["cancellation_time"])
    anchor_note = ""
    if profile == "organizer_case" and t.get("driver_wait_start"):
        anchor, anchor_rule, anchor_basis = T(t["driver_wait_start"]), "CW-F02", ["E-TRP-01.driver_wait_start"]
        anchor_note = anchor_field
    elif btype == "ADVANCE" and t.get("scheduled_time") and t_arr:
        anchor = max(t_arr, T(t["scheduled_time"]))
        anchor_rule, anchor_basis, anchor_note = "CW-F02B", i_arr + ["E-TRP-01.scheduled_time"], "ADVANCE: later of arrival and scheduled time"
    else:                                        # no arrival indication: no wait can start, whatever the booking type
        anchor, anchor_rule, anchor_basis = (t_arr or end), ("CW-F02B" if btype == "ADVANCE" else "CW-F02"), i_arr
        anchor_note = btype if t_arr else "no arrival indication, so no wait can start"
    no_wait = t_arr is None and anchor == end
    tr.finding("F-WAIT-ANCHOR", anchor.isoformat(), basis=anchor_basis, rule=anchor_rule, params=["WAIT_ANCHOR_FIELD"])
    tr.path(anchor_rule)
    if profile != "organizer_case":
        tr.path("CW-F01")
    tr.step(pb, 5, anchor_rule, f"wait anchor {anchor.strftime('%H:%M:%S')} ({anchor_note})", anchor_basis)

    # 6 DQ-01 records of the same moment (arrival, wait start, end); DQ-02 speeds
    tol = P("TS_TOLERANCE_S")
    rec_arrival = [("trip_data.driver_arrival_time", t.get("driver_arrival_time"))] \
        + [("app_events.driver_arrived", a["timestamp"]) for a in ev if a["event_type"] == "driver_arrived"] \
        + [("gps.arrived", g["timestamp"]) for g in gps if g["status"] == "arrived"]
    rec_start = [("trip_data.driver_wait_start", t.get("driver_wait_start"))] \
        + [("app_events.wait_timer_started", a["timestamp"]) for a in ev if a["event_type"] == "wait_timer_started"]
    if t_arr is not None and abs((anchor - t_arr).total_seconds()) <= tol:
        rec_start = rec_start + rec_arrival          # the wait starts at the arrival
    rec_end = [("trip_data.cancellation_time", t["cancellation_time"])] \
        + [(f"app_events.{a['event_type']}", a["timestamp"]) for a in ev if a["event_type"] in ("cancellation_fee_applied", "driver_cancelled")] \
        + [("chat.system", c["timestamp"]) for c in chat if c["type"] == "system"] \
        + [("gps.cancelled", g["timestamp"]) for g in gps if g["status"] == "cancelled"]

    def spread(recs):
        ts = [T(x[1]).timestamp() for x in recs if x[1]]
        return (max(ts) - min(ts)) if ts else 0
    spreads = {"arrival": spread(rec_arrival), "start": spread(rec_start), "end": spread(rec_end)}
    ts_ok = all(v <= tol for v in spreads.values())
    tr.finding("F-TS-CONSISTENCY", {k: round(v) for k, v in spreads.items()}, "s", basis=["E-TRP-01", "E-APP-*", "E-GPS-*", "E-CHT-*"], rule="DQ-01", params=["TS_TOLERANCE_S"])
    if not ts_ok:
        tr.flag("TIMER_ANCHOR_MISMATCH")
        tr.use("DQ-01")

    # 7 CW-R06 arrival: outliers first (same rule as CW-F04), then the moment ping
    pin = (t["pickup_location"]["lat"], t["pickup_location"]["lng"])
    gf, maxgap, lmin, vmax = P("ARRIVAL_GEOFENCE_M"), P("PING_MAX_GAP_S"), P("LEFT_MIN_OUTSIDE_S"), P("SPEED_MAX_KMH")
    smax_ratio = P("SPEED_RATIO_SOFT")
    dist = lambda g: hav(g["lat"], g["lng"], *pin)
    platform_check = bool(arrived_ev and re.search(r"GPS within (\d+) ?m of pickup", arrived_ev["details"]))
    # observations: pings, plus the platform's arrival check as an inside observation at the arrival
    obs = [{"t": T(g["timestamp"]), "lat": g["lat"], "lng": g["lng"], "inside": dist(g) <= gf, "ping": g} for g in gps]
    if platform_check and t_arr is not None:
        k = next((i for i, o in enumerate(obs) if o["t"] >= t_arr), len(obs))
        obs.insert(k, {"t": t_arr, "lat": pin[0], "lng": pin[1], "inside": True, "ping": None})

    def kmh(a, b):
        dt = (b["t"] - a["t"]).total_seconds()
        d = hav(a["lat"], a["lng"], b["lat"], b["lng"])
        return d / dt * 3.6 if dt > 0 else 0.0           # same instant: no speed information
    first_in = next((i for i, o in enumerate(obs) if o["inside"]), None)
    runs, i = [], (first_in + 1 if first_in is not None else len(obs))
    while i < len(obs):
        if obs[i]["inside"]:
            i += 1
            continue
        j = i
        while j + 1 < len(obs) and not obs[j + 1]["inside"]:
            j += 1
        span = (obs[j]["t"] - obs[i]["t"]).total_seconds()
        returned = j + 1 < len(obs)              # seen inside again; without a return nothing shows the stretch was brief
        v_in = kmh(obs[i - 1], obs[i])
        v_out = kmh(obs[j], obs[j + 1]) if returned else 0.0
        error = v_in > vmax or v_out > vmax
        s_max = (obs[j + 1]["t"] - obs[i - 1]["t"]).total_seconds() if returned else None    # longest the driver can have been away
        runs.append({"i0": i, "i1": j, "span": span, "s_max": s_max, "error": error, "returned": returned,
                     "outlier": error or (returned and span < lmin)})
        i = j + 1
    aside = {k for r in runs if r["outlier"] for k in range(r["i0"], r["i1"] + 1)}
    if first_in is not None and first_in > 0 and not obs[first_in - 1]["inside"] and kmh(obs[first_in - 1], obs[first_in]) > vmax:
        aside.add(first_in - 1)                      # an impossible jump just before the driver is first seen inside
        runs.append({"i0": first_in - 1, "i1": first_in - 1, "span": 0, "s_max": None, "error": True, "outlier": True, "returned": True})
    n_appr = first_in if first_in is not None else len(obs)
    if n_appr:                                       # the approach: pings before the driver is first seen inside, never outliers on duration
        runs.append({"i0": 0, "i1": n_appr - 1, "span": (obs[n_appr - 1]["t"] - obs[0]["t"]).total_seconds(),
                     "error": False, "outlier": False, "approach": True, "returned": first_in is not None})
    kept = [k for k in range(len(obs)) if k not in aside and obs[k]["ping"] is not None]
    moment = None
    if t_arr is not None:
        cand = [k for k in kept if t_arr - timedelta(seconds=maxgap) <= obs[k]["t"] <= t_arr + timedelta(seconds=tol)]
        moment = cand[-1] if cand else None
    m_in = moment is not None and obs[moment]["inside"]
    contradicted = moment is not None and not obs[moment]["inside"] and obs[moment]["t"] >= t_arr
    later_in = [k for k in kept if obs[k]["inside"] and t_arr is not None and t_arr + timedelta(seconds=tol) < obs[k]["t"] <= end]
    after_arr = [k for k in kept if t_arr is not None and t_arr <= obs[k]["t"] <= end]      # remaining pings from the arrival on
    brief_in = False
    t_confirm, how = None, ""
    if t_arr is None:
        arrival, how = "UNKNOWN", "no arrival indication"
    elif platform_check and contradicted:
        arrival, how = "CONTESTED", "the platform check says arrived, but GPS shows the driver outside the area at or after the arrival"
    elif platform_check or m_in:
        arrival, t_confirm = "TRUE", t_arr
        how = "platform GPS arrival check" if platform_check else f"ping inside the area at {obs[moment]['t'].strftime('%H:%M:%S')}"
    elif later_in:
        arrival, t_confirm = "TRUE", obs[later_in[0]]["t"]
        tr.flag("ARRIVAL_UNCONFIRMED")
        how = (f"not confirmed at the arrival{' (GPS outside the area at ' + obs[moment]['t'].strftime('%H:%M:%S') + ')' if contradicted else ''}; "
               f"first confirmed by the ping at {t_confirm.strftime('%H:%M:%S')}")
    elif after_arr:
        arrival = "FALSE"
        brief_in = any(obs[k]["inside"] for k in after_arr)          # inside for a moment, then outside before the moment ping
        how = ("inside the area only for a moment after the arrival, then outside until the cancellation" if brief_in
               else "no remaining ping from the arrival to the cancellation is inside the area")
    else:
        arrival, how = "UNKNOWN", "no platform check and no remaining ping from the arrival on"
    late_out = []                                # FRD-01: outside after the arrival mark beyond the tolerance, before the confirmation
    if not platform_check and "ARRIVAL_UNCONFIRMED" in tr.flags:
        late_out = [k for k in kept if not obs[k]["inside"] and t_arr + timedelta(seconds=tol) < obs[k]["t"] < t_confirm]
    tr.early_press = bool(late_out) or arrival == "FALSE"     # a CONTESTED arrival goes to a person without a fraud signal
    i_parr = [gid(obs[moment]["ping"])] if moment is not None else []
    if arrival == "TRUE" and "ARRIVAL_UNCONFIRMED" in tr.flags:      # basis = the records that support the value, not every nearby ping
        arr_basis = i_arr + (i_parr if contradicted else []) + [gid(obs[later_in[0]]["ping"])]
    elif arrival == "TRUE":
        arr_basis = i_arr + (i_parr if m_in else [])
    elif arrival == "CONTESTED":
        arr_basis = i_arr + i_parr
    elif arrival == "FALSE":
        arr_basis = i_arr + [gid(obs[k]["ping"]) for k in after_arr]
    else:
        arr_basis = i_arr
    tr.finding("F-ARRIVAL-VALID", arrival, status={"TRUE": "established", "FALSE": "established", "CONTESTED": "contested", "UNKNOWN": "unknown"}[arrival],
               basis=arr_basis, rule="CW-R06", params=["ARRIVAL_GEOFENCE_M", "TS_TOLERANCE_S", "PING_MAX_GAP_S", "LEFT_MIN_OUTSIDE_S", "SPEED_MAX_KMH"])
    tr.arrival_detail = {"t_arr": t_arr.isoformat() if t_arr else None, "t_confirm": t_confirm.isoformat() if t_confirm else None,
                         "platform_check": platform_check, "moment_ping": i_parr[0] if i_parr else None, "brief_inside": brief_in,
                         "confirm_ping": gid(obs[later_in[0]]["ping"]) if "ARRIVAL_UNCONFIRMED" in tr.flags else None,
                         "late_outside": [gid(obs[k]["ping"]) for k in late_out]}
    tr.path("CW-R06")
    tr.step(pb, 7, "CW-R06", f"{arrival}: {how}", arr_basis)

    # 8 CW-F03 elapsed from the confirmed wait start, margin, spread of the records
    start = max(anchor, t_confirm) if (arrival == "TRUE" and t_confirm and alt_start != "anchor") else anchor     # CW-F03B
    elapsed = (end - start).total_seconds()
    thr, cmp_, band = P("NO_SHOW_THRESHOLD_S"), P("THRESHOLD_COMPARISON"), P("BOUNDARY_BAND_S")
    margin = elapsed - thr
    met = elapsed >= thr if cmp_ == "at_least" else elapsed > thr
    if start == anchor:                          # the start is the anchor, the confirmed arrival, or a later confirming ping
        basis_start, start_spread, start_from = anchor_basis, spreads["start"], "anchor"
    elif start == t_arr:
        basis_start, start_spread, start_from = i_arr + i_parr, spreads["arrival"], "arrival"
    else:
        basis_start, start_spread, start_from = [gid(obs[later_in[0]]["ping"])], 0, "ping"
    w_status = "not_applicable" if no_wait else "established"
    tr.finding("F-WAIT-ELAPSED", elapsed, "s", basis=basis_start + ["E-TRP-01.cancellation_time"], rule="CW-F03", status=w_status)
    tr.finding("F-WAIT-MARGIN", margin, "s", basis=basis_start + ["E-TRP-01.cancellation_time"], rule="CW-F03", status=w_status,
               params=["NO_SHOW_THRESHOLD_S", "THRESHOLD_COMPARISON", "BOUNDARY_BAND_S"])
    if start_from != "anchor":
        tr.path("CW-F03B")
    if abs(margin) <= band:
        tr.flag("BOUNDARY_MARGIN")
    spread_max = max(start_spread, spreads["end"])
    if abs(margin) <= band and spread_max > abs(margin):
        tr.flag("MARGIN_WITHIN_SPREAD")
    tr.wait_start, tr.wait_start_from = start, start_from
    tr.path("CW-F03")
    tr.step(pb, 8, "CW-F03, CW-F03B", f"wait counted from {start.strftime('%H:%M:%S')}"
            + {"anchor": "", "arrival": " (the confirmed arrival, later than the anchor)", "ping": " (GPS confirmation after the anchor)"}[start_from]
            + f"; elapsed {elapsed:.0f} s; threshold {thr} s ({cmp_}); margin {margin:+.0f} s: {'met' if met else 'NOT met'}"
            + (f"; the records of the start or end differ by up to {spread_max:.0f} s, more than the margin" if "MARGIN_WITHIN_SPREAD" in tr.flags else ""),
            basis_start + ["E-TRP-01.cancellation_time"])

    # 9 CW-F04 presence over the waiting the fee pays for
    wend = min(end, start + timedelta(seconds=thr)) if met else end
    in_w = lambda k: start <= obs[k]["t"] <= wend

    def touch(r):                                # any ping of the stretch inside the window (used for the outlier flag)
        return any(obs[k]["ping"] is not None and in_w(k) for k in range(r["i0"], r["i1"] + 1))

    def counts(r):                               # leaving: the stretch is seen outside at least TS_TOLERANCE_S before the window end
        ks = [k for k in range(r["i0"], r["i1"] + 1) if k not in aside and obs[k]["ping"] is not None]
        if not ks:
            return False
        lo = start + timedelta(seconds=tol) if r.get("approach") else start      # the approach also needs more than that after the start
        hi = wend - timedelta(seconds=tol)
        t_a, t_b = obs[ks[0]]["t"], obs[ks[-1]]["t"]          # observed outside from its first to its last ping
        return lo <= hi and t_a <= hi and (t_b > lo if r.get("approach") else t_b >= lo)

    def outside_in_wait(r):                      # observed time outside from the wait start to the cancellation
        ks = [k for k in range(r["i0"], r["i1"] + 1) if k not in aside]
        return max(0.0, (min(obs[ks[-1]]["t"], end) - max(obs[ks[0]]["t"], start)).total_seconds()) if ks else 0.0
    win = [k for k in range(len(obs)) if obs[k]["ping"] is not None and in_w(k)]
    left_runs = [r for r in runs if not r["outlier"] and counts(r)]
    out_runs = [r for r in runs if r["outlier"] and touch(r)]
    near_arr = lambda r: t_arr is not None and t_arr - timedelta(seconds=maxgap) <= obs[r["i0"]]["t"] <= wend
    err_runs = [r for r in runs if r["error"] and (touch(r) or near_arr(r))]
    ins = sorted(obs[k]["t"] for k in win if obs[k]["inside"] and k not in aside)
    gaps = []
    if wend <= start:                            # no wait, so no window to check
        presence = "UNKNOWN"
    elif not win:
        presence = "UNKNOWN"
    elif left_runs:
        presence = "LEFT"
    elif arrival != "TRUE" and not ins:          # without a confirmed arrival the window start is not a point at the pick-up
        presence = "UNKNOWN"
    else:
        seq = [start] + [x for x in ins if start < x < wend] + [wend]
        gaps = [(b - a).total_seconds() for a, b in zip(seq, seq[1:])]
        presence = "SPARSE" if gaps and max(gaps) > maxgap else "CONSISTENT"
    if out_runs:
        tr.flag("GPS_OUTLIER")
    if err_runs:
        tr.flag("GPS_DATA_ERROR")
        tr.use("DQ-02")
    # GPS_AMBIGUOUS: the pings cannot settle whether the driver left (approval, AUTH-02); the value does not change
    ambiguous = []
    for r in runs:
        if r.get("approach") or r["error"]:
            continue
        t_prev, t_first = obs[r["i0"] - 1]["t"], obs[r["i0"]]["t"]
        n_pings = sum(1 for k in range(r["i0"], r["i1"] + 1) if obs[k]["ping"] is not None)
        if r["outlier"] and r["s_max"] > lmin and t_first <= wend + timedelta(seconds=tol) \
                and t_prev < wend - timedelta(seconds=tol) and obs[r["i1"] + 1]["t"] > start:
            ambiguous.append({"kind": "gap", "s": r["s_max"]})          # set aside, but the driver may have been away longer
        elif not r["returned"] and r in left_runs and n_pings == 1:
            ambiguous.append({"kind": "single", "s": 0})
        elif not r["outlier"] and r not in left_runs and start <= t_first <= wend + timedelta(seconds=tol) \
                and t_prev < wend - timedelta(seconds=tol):
            ambiguous.append({"kind": "end", "s": (t_first - t_prev).total_seconds()})
    if arrival == "FALSE" and len(after_arr) == 1:
        ambiguous.append({"kind": "single_false", "s": 0})
    if ambiguous:
        tr.flag("GPS_AMBIGUOUS")
    used = [k for k in win if k not in aside]
    ids_win = [gid(obs[k]["ping"]) for k in used]
    dists = [dist(obs[k]["ping"]) for k in used]
    n_out = sum(1 for k in win if k in aside)
    run_of = {k: r for r in runs if not r.get("approach") for k in range(r["i0"], r["i1"] + 1)}
    kinds = {"brief": 0, "error": 0, "ambiguous": 0, "ambiguous_gap_s": 0}
    for k in win:
        if k in aside:
            r = run_of.get(k, {"error": True})
            kind = "error" if r["error"] else ("ambiguous" if (r["s_max"] or 0) > lmin else "brief")
            kinds[kind] += 1
            if kind == "ambiguous":
                kinds["ambiguous_gap_s"] = max(kinds["ambiguous_gap_s"], r["s_max"])
    edge_out = [k for k in used if not obs[k]["inside"]] if presence in ("CONSISTENT", "SPARSE") else []   # within the tolerance, not leaving
    tr.finding("F-PRESENCE", presence, basis=ids_win, rule="CW-F04", params=["ARRIVAL_GEOFENCE_M", "PING_MAX_GAP_S", "LEFT_MIN_OUTSIDE_S", "SPEED_MAX_KMH", "TS_TOLERANCE_S"],
               status="established" if presence != "UNKNOWN" else ("not_applicable" if wend <= start else "unknown"))
    longest_left = max([outside_in_wait(r) for r in left_runs], default=0)
    tr.presence_detail = {"pings": len(win), "usable_pings": len(used), "inside_pings": len(ins),
                          "max_dist_m": round(max(dists), 1) if dists else None, "gaps_s": [round(x) for x in gaps],
                          "outliers": n_out, "window": [start.isoformat(), wend.isoformat()], "longest_outside_s": round(longest_left),
                          "left_by_approach": bool(left_runs) and all(r.get("approach") for r in left_runs),
                          "no_return": any(not r.get("returned", True) for r in left_runs),
                          "edge_outside": len(edge_out), "edge_ids": [gid(obs[k]["ping"]) for k in edge_out],
                          "outlier_kinds": kinds, "ambiguous": ambiguous}
    if presence == "SPARSE":
        tr.flag("SPARSE_GPS")
    tr.path("CW-F04")
    tr.step(pb, 9, "CW-F04", f"{presence}: window {start.strftime('%H:%M:%S')} to {wend.strftime('%H:%M:%S')}, {len(win)} ping(s), max distance "
            f"{max(dists) if dists else 0:.1f} m (area {gf} m)"
            + (((f"; outside for {longest_left:.0f} s of the wait" if longest_left else "; seen outside the area")
                + (" (the driver was not yet seen inside the area)" if tr.presence_detail["left_by_approach"]
                   else " (not seen back inside, so not an outlier)" if tr.presence_detail["no_return"] else f" (LEFT needs a stretch of {lmin} s)"))
               if left_runs else "")
            + ("; no wait to check" if wend <= start else "")
            + (f"; {n_out} outlier ping(s) set aside" if n_out else "")
            + (f"; {len(edge_out)} ping(s) outside the area within {tol} s of the window start or end, not counted as leaving" if edge_out else "")
            + ("; impossible speed (data error)" if err_runs else "")
            + ("; GPS cannot settle whether the driver left (" + ", ".join(sorted({a['kind'] for a in ambiguous})) + ")" if ambiguous else "")
            + ("; no inside ping and no confirmed arrival, so presence is not shown" if presence == "UNKNOWN" and win and wend > start else "")
            + (f"; longest stretch without presence evidence {max(gaps):.0f} s (limit {maxgap} s)" if gaps else ""),
            ids_win, status="done" if win else "missing")

    # DQ-02 speed consistency inside the window (soft); hard errors were handled with the outliers above
    wp = [g for g in gps if start <= T(g["timestamp"]) <= wend]
    soft = hard = 0
    for a, b in zip(wp, wp[1:]):
        dt = (T(b["timestamp"]) - T(a["timestamp"])).total_seconds()
        dist_ab = hav(a["lat"], a["lng"], b["lat"], b["lng"])
        implied = dist_ab / dt * 3.6 if dt > 0 else 0
        reported = (a["speed_kmh"] + b["speed_kmh"]) / 2
        hard += implied > vmax
        soft += reported > smax_ratio * implied and reported > 5
    tr.finding("F-SPEED-CONSISTENCY", {"soft_segments": soft, "hard_segments": hard, "data_error_stretches": len(err_runs), "window": "wait"},
               basis=["E-GPS-*"], rule="DQ-02", params=["SPEED_RATIO_SOFT", "SPEED_MAX_KMH"])
    if soft:
        tr.flag("SPEED_INCONSISTENT")
    tr.step(pb, 6, "DQ-01, DQ-02", f"spread of the arrival records {spreads['arrival']:.0f} s, of the wait start {spreads['start']:.0f} s, of the end {spreads['end']:.0f} s "
            f"(tolerance {tol} s): {'consistent' if ts_ok else 'INCONSISTENT'}; speed in the wait window: {soft} soft, {hard} hard"
            + (f", {len(err_runs)} impossible jump(s) set aside" if err_runs else ""), ["E-TRP-01", "E-APP-*", "E-GPS-*"])
    tr.steps.sort(key=lambda x: (x["playbook"] != "PB-INTAKE", x["n"]))

    # 10 CW-F05 contact
    t_arr = t_arr or anchor
    calls = [c for c in chat if c["sender"] == "driver" and c["type"] == "call" and t_arr <= T(c["timestamp"]) <= end]
    msgs = [c for c in chat if c["sender"] == "driver" and c["type"] == "message" and t_arr <= T(c["timestamp"]) <= end]
    rider_contacts = [c for c in chat if c["sender"] == "rider" and t_arr <= T(c["timestamp"]) <= end]
    min_calls, min_msgs = P("CONTACT_MIN_CALLS"), P("CONTACT_MIN_MESSAGES")
    contact = "ADEQUATE" if (len(calls) >= min_calls or len(msgs) >= min_msgs or rider_contacts) else ("INSUFFICIENT" if (calls or msgs) else "NONE")
    if t_arr >= end:              # no arrival and no anchor before the cancellation: CW-F05 has no window to count in
        contact = None
    i_c = _ev_id("E-CHT", case, "chat_logs", lambda c: c["type"] in ("call", "message") and t_arr <= T(c["timestamp"]) <= end)
    tr.finding("F-CONTACT", contact, basis=i_c, rule="CW-F05", params=["CONTACT_MIN_CALLS", "CONTACT_MIN_MESSAGES"],
               status="established" if contact else "not_applicable")
    tr.contact_detail = {"driver_calls": len(calls), "driver_messages": len(msgs), "rider_contacts": len(rider_contacts), "call_ids": _ev_id("E-CHT", case, "chat_logs", lambda c: c in calls), "message_ids": _ev_id("E-CHT", case, "chat_logs", lambda c: c in msgs)}
    tr.step(pb, 10, "CW-F05", f"{contact}: driver {len(calls)} call(s) and {len(msgs)} message(s), rider {len(rider_contacts)} contact(s)" if contact
            else "not assessed: no arrival indication, so there is no wait in which to count contact attempts", i_c, status="done" if contact else "not_applicable")

    # 11 CW-F06 rider counter-evidence (HARD part from records, READ part from the statement)
    rider_gps = case.get("rider_gps_telemetry") or []
    venue = venue_for(kb, case)
    strong = []
    pvmax = P("PIN_VENUE_MAX_M")
    for g in rider_gps:                  # the same window as the rider's calls and messages: from TS_TOLERANCE_S before the arrival indication to the cancellation
        if t_arr - timedelta(seconds=tol) <= T(g["timestamp"]) <= end:
            if hav(g["lat"], g["lng"], *pin) <= gf:
                strong.append("rider GPS at the pin")
            if venue and hav(g["lat"], g["lng"], venue["lat"], venue["lng"]) <= pvmax:
                strong.append("rider GPS at the named venue")
    if any(re.search(r"fail|not delivered|undelivered", a["details"], re.I) for a in ev if a["event_type"] == "rider_notified"):
        strong.append("notification failure log")
    records_strong = bool(strong)
    # READ part on the rider's own calls and messages during the wait (from TS_TOLERANCE_S before the arrival indication to the cancellation)
    cid = lambda c: _ev_id("E-CHT", case, "chat_logs", lambda x: x is c)[0]
    w_start = t_arr - timedelta(seconds=tol)      # records of the arrival can differ by TS_TOLERANCE_S (DQ-01)
    contacts06 = [c for c in chat if c["sender"] == "rider" and c["type"] in ("call", "message") and w_start <= T(c["timestamp"]) <= end]

    def answers_question(c):                    # the driver's last message before c (in time order) asks something
        prev = sorted((x for x in chat if x["sender"] == "driver" and x["type"] == "message" and T(x["timestamp"]) <= T(c["timestamp"])),
                      key=lambda x: x["timestamp"])
        return bool(prev) and _asks_driver(prev[-1].get("content"))

    def read06(c):
        r_ = rider_contact_reading(c)
        if r_ == "NEUTRAL" and answers_question(c):   # "ok" or a thumbs-up answering the driver's question reads like a bare "yes"
            return "UNCLEAR"
        return r_
    readings = {cid(c): read06(c) for c in contacts06}
    by = {k: [i for i, r in readings.items() if r == k] for k in ("PLACES", "LATE", "NEUTRAL", "UNCLEAR")}
    if by["PLACES"]:
        strong.append("a rider message during the wait places the rider at the pick-up or contests presence, timing or place")
    if by["UNCLEAR"] and contact_reading == "STRONG":
        strong.append("an unclear rider call or message during the wait, read as placing the rider at the pick-up (other reading)")
    # D30: before the arrival indication (from the driver's assignment), a rider message that places the rider at the pick-up,
    # or rider GPS at the pin or venue, counts too: at least WEAK, with STRONG as its other reading in the reading test.
    # Questions about the driver, pick-up instructions, admissions and calls before the wait do not count: the wait had not started.
    starts = [T(a["timestamp"]) for a in ev if a["event_type"] == "driver_assigned"] or \
             [T(a["timestamp"]) for a in ev if a["event_type"] == "booking_confirmed"]
    d30_from = min(starts) if starts else None     # the earliest assignment (else the booking); none recorded: no lower bound
    if d30_from is not None and d30_from >= w_start:  # assignment stamped after the arrival: a data error, so a person checks
        booked_at = [T(a["timestamp"]) for a in ev if a["event_type"] == "booking_confirmed" and T(a["timestamp"]) < w_start]
        d30_from = min(booked_at) if booked_at else None
        tr.flag("RECORDS_MISSING")
    before = lambda ts: (d30_from is None or d30_from <= T(ts)) and T(ts) < w_start
    place_names = [n.lower().split("(")[0].strip() for n in ((venue or {}).get("name"), t["pickup_location"].get("name")) if n]
    pre_read = {cid(c): before_arrival_reading(c, place_names, answers_question(c)) for c in chat if c["sender"] == "rider" and before(c["timestamp"])}
    pre_ids = [i for i, r_ in pre_read.items() if r_]
    pre_clear = [i for i, r_ in pre_read.items() if r_ == "PLACES"]
    pre_gps, pre_gps_where = [], {}
    for i, g in enumerate(rider_gps, 1):
        if before(g["timestamp"]):
            where = ("pin" if hav(g["lat"], g["lng"], *pin) <= gf else
                     "venue" if venue and hav(g["lat"], g["lng"], venue["lat"], venue["lng"]) <= pvmax else None)
            if where:
                pre_gps.append(f"E-RGPS-{i:02d}")
                pre_gps_where[f"E-RGPS-{i:02d}"] = where
    if (pre_ids or pre_gps) and contact_reading == "STRONG":
        strong.append("the rider at the pick-up before the driver's arrival indication, read as STRONG (other reading)")
    outside = _ev_id("E-CHT", case, "chat_logs", lambda c: c["sender"] == "rider" and c["type"] in ("call", "message")
                     and c not in contacts06 and cid(c) not in pre_ids)
    tr.rider_contact_detail = {"readings": readings, **{k.lower() + "_ids": v for k, v in by.items()}, "outside_ids": outside,
                               "before_arrival_ids": pre_ids, "before_arrival_clear_ids": pre_clear,
                               "before_arrival_gps_ids": pre_gps, "before_arrival_gps_where": pre_gps_where}
    contested = contests_statement(tk.get("description", "")) if tk.get("filed_by") == "rider" else False
    rider_ev = "STRONG" if strong else ("WEAK" if (pre_ids or pre_gps) else (force_reading or ("WEAK" if contested else "NONE")))
    if rider_ev != "STRONG":
        tr.flag("NO_RIDER_EVIDENCE")
    tr.rider_contests = contested if not force_reading else (force_reading == "WEAK")
    tr.rider_at_venue_claim = bool(venue and venue["name"].lower() in (tk.get("description", "") or "").lower() and tr.rider_contests)
    tr.finding("F-RIDER-EVIDENCE", rider_ev, basis=["E-TKT-01"] + (["E-RGPS-*"] if rider_gps else []) + list(readings) + pre_ids + pre_gps, rule="CW-F06",
               params=["ARRIVAL_GEOFENCE_M", "PIN_VENUE_MAX_M", "TS_TOLERANCE_S"], status="established" if records_strong else "read")
    tr.path("CW-F06")
    contact_words = "; ".join(f"{i} {r}" for i, r in readings.items())
    pre_words = (f"the rider's message or GPS before the arrival indication ({', '.join(pre_ids + pre_gps)}) places or may place the rider"
                 " at the pick-up, which counts as counter-evidence (D30; GPS: open item D33), so at least WEAK")
    tr.step(pb, 11, "CW-F06", f"{rider_ev}: " + ("; ".join(sorted(set(strong))) if strong else
            "; ".join(([pre_words] if (pre_ids or pre_gps) else [])
                      + (["the statement contests presence or place, but no rider-side record or rider message during the wait shows the rider at the pick-up"]
                         if contested and not force_reading or force_reading == "WEAK" else []))
            if rider_ev == "WEAK" else "no rider-side record or rider message shows the rider at the pick-up, and the statement does not contest presence, timing or place")
            + (f" (rider calls and messages during the wait: {contact_words})" if readings else ""),
            ["E-TKT-01"] + _ev_id("E-APP", case, "app_events", lambda a: a["event_type"] == "rider_notified")
            + list(readings) + pre_ids + (pre_gps or (["E-RGPS-*"] if rider_gps else [])),
            note="" if records_strong else "READ: judged from the statement and the rider's calls and messages")

    # 12 CW-F07 pin vs venue
    if venue:
        dpv = hav(pin[0], pin[1], venue["lat"], venue["lng"])
        mismatch = dpv > pvmax
        tr.finding("F-PIN-VENUE", round(dpv), "m", basis=["E-TRP-01.pickup_location", "E-GEO-01"], rule="CW-F07", params=["PIN_VENUE_MAX_M"])
        tr.step(pb, 12, "CW-F07", f"pin is {dpv:,.0f} m from the OneMap address of {venue['name']} (limit {pvmax} m): mismatch = {mismatch}", ["E-TRP-01.pickup_location", "E-GEO-01"])
    else:
        mismatch = False
        tr.finding("F-PIN-VENUE", None, "m", status="unknown", rule="CW-F07")
        tr.step(pb, 12, "CW-F07", "venue not in reference table VENUES", [], status="missing")
    tr.pin_mismatch = mismatch
    tr.venue_name = venue["name"] if venue else t["pickup_location"]["name"]
    if mismatch:
        tr.flag("PIN_VENUE_MISMATCH")

    # 13 GEN-R05 advocates: not simulated here
    tr.step(pb, 13, "GEN-R05", "advocate briefs are produced at run time by the Rider and Driver Advocates; not simulated in this offline check", [], status="missing")

    # 14 DT-CW-NOSHOW
    env = {"arrival_valid": arrival, "presence": presence, "threshold_met": met, "rider_evidence": rider_ev}
    dt = kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]
    hits = [r for r in dt["rows"] if all(env[k] in (v if isinstance(v, list) else [v]) for k, v in r["when"].items())]
    assert len(hits) == 1, f"decision table hit {len(hits)} rows for {env}"
    row = hits[0]
    tr.dt_env, tr.dt_row, tr.dt_row_credibility = env, row["row"], row.get("credibility")
    tr.outcome = row["outcome"]
    tr.reasons = [row["reason"]]
    for f in row.get("flags", []) or []:
        tr.flag(f)
    tr.path(*row.get("rules", []))
    tr.also = list(row.get("also", []) or [])
    override = ""
    if tr.policy_gap:          # META-02 / CW-R00 then GEN-R07: no written rule applies, a human decides
        tr.outcome = "ESCALATE_HUMAN"
        tr.reasons = ["GEN-R-POLICY-GAP"]
        tr.path("GEN-R07")
        override = "; overridden by " + ", ".join(r for r, _ in tr.policy_gap) + " and GEN-R07 (policy gap)"
        tr.notes.append(f"decision table row {row['row']} recorded for information only; " + "; ".join(w for _, w in tr.policy_gap))
    elif days > window:        # MAT-04: a waiver request after the window is not considered
        tr.outcome = "UPHOLD"
        tr.reasons = ["CW-R-OUT-OF-WINDOW"]
        override = "; overridden by MAT-04 (out of window)"
        tr.notes.append(f"decision table row {row['row']} recorded for information only; MAT-04 decides")
    tr.step(pb, 14, "DT-CW-NOSHOW", f"row {row['row']} (credibility {row.get('credibility')}): {row['outcome']} ({row['reason']})" + override,
            ["F-ARRIVAL-VALID", "F-PRESENCE", "F-WAIT-MARGIN", "F-RIDER-EVIDENCE"])

    # 15 CW-R11 pin, CW-R04 contact, DQ-06 amount
    if mismatch:
        tr.use("CW-R11")
    if mismatch and tr.outcome == "UPHOLD" and tr.reasons[0] == "CW-R-NOSHOW-VALID":
        tr.reasons.append("CW-R-PIN-AMBIGUOUS")
        if "CW-R11" not in tr.also:
            tr.also.append("CW-R11")
    amount = float(t["cancellation_fee"])
    if contact == "NONE":
        tr.flag("CONTACT_NOT_ATTEMPTED")
        tr.use("CW-R04")
    policy_amount, tol_m = P("NO_SHOW_FEE_SGD"), P("MONEY_TOLERANCE_SGD")
    amt_status = "equal" if abs(amount - policy_amount) <= tol_m else ("overcharged" if amount > policy_amount else "undercharged")
    if amt_status != "equal":
        tr.flag("CHARGE_AMOUNT_MISMATCH")
        tr.use("DQ-06")
    tr.finding("F-CHARGE-AMOUNT", {"charged": amount, "policy": policy_amount, "status": amt_status}, "SGD",
               basis=["E-TRP-01.cancellation_fee", "E-POL-01" if case.get("cancellation_policy") else "reference_data"], rule="DQ-06", params=["NO_SHOW_FEE_SGD", "MONEY_TOLERANCE_SGD"])
    tr.step(pb, 15, "CW-R11, CW-R04, DQ-06", f"pin mismatch {mismatch}" + (f", and the rider says they were at {tr.venue_name}" if tr.rider_at_venue_claim and mismatch else "")
            + f"; contact {contact}; charged S${amount:.2f} vs policy S${policy_amount:.2f}: {amt_status}", ["F-PIN-VENUE", "F-CONTACT", "F-CHARGE-AMOUNT"])

    # 16 CW-R09 payee, CW-R10 remedy
    payee = P("FEE_PAYEE")
    if tr.outcome == "UPHOLD":
        tr.remedy = {"amount_sgd": 0.0, "payer": None, "payee": None, "form": "NONE", "fee_stands_sgd": amount, "fee_payee": payee}
    elif tr.outcome == "WAIVE_FEE":
        tr.remedy = {"amount_sgd": amount, "payer": "PLATFORM", "payee": "RIDER", "form": P("REMEDY_FORM")}
        tr.use("CW-R10")
    else:
        tr.remedy = {"amount_sgd": None, "payer": None, "payee": None, "form": None, "provisional": "decided by a human"}
    tr.step(pb, 16, "CW-R09, CW-R10", f"fee payee {payee}; remedy {tr.remedy}", ["E-POL-01"] if case.get("cancellation_policy") else [])

    # 17 FRD-01, FRD-02 (never decisive for the outcome)
    frd, tr.fraud_detail = [], {}
    if tr.early_press:
        frd.append(("DRIVER", "FRD-01"))
        tr.fraud_detail["DRIVER"] = ("GPS showed the driver outside the pick-up area more than the timestamp tolerance after the arrival indication, "
                                     "before GPS first confirmed the driver there" if arrival != "FALSE"
                                     else "after the arrival indication, GPS showed the driver in the pick-up area only for a moment, then outside it until the cancellation"
                                     if brief_in else "arrival indicated, but no GPS point from then until the cancellation is inside the pick-up area")
    rp = case["rider_profile"]
    hist = rp.get("dispute_history", {})
    total = hist.get("total_disputes", 0)
    share = (hist.get("rejected", 0) / total) if total else 0
    if total >= P("RIDER_ABUSE_MIN_DISPUTES") and share >= P("RIDER_ABUSE_REJECT_SHARE_MIN") and rp.get("fraud_flags", 0) >= 1:
        frd.append(("RIDER", "FRD-02"))
        tr.fraud_detail["RIDER"] = (f"{hist.get('rejected', 0)} of {total} past disputes rejected; platform flag: "
                                    f"{rp.get('fraud_flag_details') or 'no detail recorded'}")
    if frd:
        tr.flag("FRAUD_SIGNAL")
    tr.fraud = frd
    tr.step(pb, 17, "FRD-01, FRD-02, GEN-R03, GEN-R06", "signals: " + ("; ".join(f"{who} ({r}: {tr.fraud_detail[who]})" for who, r in frd) if frd else "none")
            + "; for the reviewer only; history never enters the outcome; no account action", ["E-PRF-R", "E-PRF-D"])

    # 18 AUTH-05 confidence (AUTH-01..04 applied in decide_tier after the decisive tests)
    w = P("CONFIDENCE_WEIGHTS")
    penalty = P("SOFT_FLAG_PENALTY")
    M = min(1.0, abs(margin) / (2 * band)) if band else 1.0
    req = {
        "E-TKT-01": True, "E-TRP-01": True,
        "E-APP-* (" + ", ".join([x for x in ("driver_assigned", "driver_arrived", "wait_timer_started", "cancellation_fee_applied")
                                 if not any(a["event_type"] == x for a in ev)] or ["driver_assigned", "driver_arrived", "wait_timer_started", "cancellation_fee_applied"]) + ")":
            all(any(a["event_type"] == x for a in ev) for x in ("driver_assigned", "driver_arrived", "wait_timer_started", "cancellation_fee_applied")),
        "E-GPS-* during the wait": bool(win),
        "E-CHT-* (calls and messages)": "chat_logs" in case,
        "E-POL-01 (policy object or profile)": True,
    }
    if tr.rider_contests:
        req["rider-side records (required because the rider contests presence)"] = bool(rider_gps) or bool(rider_contacts) or bool(tr.rider_contact_detail.get("before_arrival_ids"))
    soft_flags = [f for f in tr.flags if f in SOFT_FLAGS]
    E_ = max(0.0, sum(req.values()) / len(req) - penalty * len(soft_flags))
    A_, R_ = 1.0, 1.0
    C = w["A_run_agreement"] * A_ + w["M_threshold_margin"] * M + w["E_evidence_completeness"] * E_ + w["R_rules_engine_agreement"] * R_
    tr.confidence = {"A": A_, "M": round(M, 3), "E": round(E_, 3), "R": R_, "C": round(C, 3),
                     "assumed": ["A = 1.0 (no LLM runs in this check)", "R = 1.0 (no LLM Judge in this check)"],
                     "soft_flags": soft_flags, "evidence_present": req}
    tr.step(pb, 18, "AUTH-05", f"C = {C:.3f} (A {A_}, M {M:.2f}, E {E_:.2f}, R {R_}; soft flags {soft_flags})", ["F-WAIT-MARGIN", "F-PRESENCE"])
    tr.amount_at_stake = amount
    tr.margin = margin
    tr.spread_max = spread_max
    return tr


# ---------------------------------------------------------------------------------------------- decisive tests and tier
def sensitivity(kb: KB, case: dict, profile: str, base: Trace) -> list[dict]:
    """Clause 2: move each C/D parameter on the path to both ends of its plausible range. Decisive if the outcome changes, or if
    the same outcome would then rest on a decision-table row rated C or D while the base row is rated A or B."""
    rows = []
    cred = {r["row"]: r.get("credibility") for r in kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]["rows"]}
    weak = lambda row: cred.get(row) in ("C", "D")
    overridden = lambda tr_: bool(tr_.reasons) and tr_.reasons[0] in ("CW-R-OUT-OF-WINDOW", "GEN-R-POLICY-GAP")
    for name, info in base.params_used.items():
        pr = info.get("plausible_range")
        if info.get("credibility") not in ("C", "D") or not pr or info.get("flag_only"):
            continue
        res, moved, weaker = {}, set(), False
        for end_name, val in (("low", pr[0]), ("high", pr[1])):
            t2 = evaluate(kb, copy.deepcopy(case), profile, {**base.overrides, name: val})
            res[end_name] = (val, t2.outcome, t2.dt_row)
            rw = (t2.outcome == base.outcome and not overridden(base) and not overridden(t2) and t2.dt_row != base.dt_row
                  and weak(t2.dt_row) and not weak(base.dt_row))
            weaker = weaker or rw
            if t2.outcome != base.outcome or rw:      # attribute the change to the path rules whose finding moved
                for code, f in base.findings.items():
                    if not code.startswith("_") and t2.findings.get(code, {}).get("value") != f.get("value") and f.get("rule"):
                        moved.add(f["rule"])
        changed = any(r[1] != base.outcome for r in res.values())
        users = [rid for rid in base.rules_on_path if name in (kb.rules.get(rid, {}).get("params") or []) and kb.rules.get(rid, {}).get("family") != "FRD"]
        if (changed or weaker) and moved & set(users):
            users = [rid for rid in users if rid in moved]
        rows.append({"param": name, "value": info["value"], "range": pr, "credibility": info["credibility"],
                     "low": f"{res['low'][0]} -> {res['low'][1]} ({res['low'][2]})", "high": f"{res['high'][0]} -> {res['high'][1]} ({res['high'][2]})",
                     "outcome_changes": changed, "weaker_row": weaker and not changed, "decisive": changed or weaker, "rules_using": users})
    return rows


def reading_test(kb: KB, case: dict, profile: str, base: Trace) -> list[dict]:
    """Clause 1: a READ rule on the path is decisive if another reading changes the outcome (CW-F06 statement)."""
    out = []
    cur = base.findings.get("F-RIDER-EVIDENCE", {}).get("value")
    if cur in ("NONE", "WEAK"):
        alt = "WEAK" if cur == "NONE" else "NONE"
        t2 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, force_reading=alt)
        out.append({"rule": "CW-F06", "kind": "statement", "reading": cur, "other_reading": alt, "outcome_other": t2.outcome,
                    "changes": t2.outcome != base.outcome})
        rcd = getattr(base, "rider_contact_detail", None) or {}
        unclear = (rcd.get("unclear_ids") or []) + (rcd.get("before_arrival_ids") or []) + (rcd.get("before_arrival_gps_ids") or [])
        if unclear:              # a call (words not recorded), a message the phrase lists cannot settle, or the rider before arrival
            t3 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, contact_reading="STRONG")
            out.append({"rule": "CW-F06", "kind": "contact", "ids": unclear,
                        "reading": f"{cur}: the rider's call, message or GPS ({', '.join(unclear)}) not read as STRONG",
                        "other_reading": "STRONG: read as placing the rider at the pick-up or contesting presence",
                        "outcome_other": t3.outcome, "changes": t3.outcome != base.outcome})
    return out


def start_test(kb: KB, case: dict, profile: str, base: Trace) -> list[dict]:
    """Clause 1 for CW-F03B, a FairRyde reading (D): do the other readings of where the wait starts change the outcome?"""
    if base.wait_start_from not in ("arrival", "ping"):
        return []
    t2 = evaluate(kb, copy.deepcopy(case), profile, base.overrides, alt_start="anchor")
    out = [{"rule": "CW-F03B", "reading": "wait counted from the GPS confirmation", "other_reading": "wait counted from the anchor, regardless of GPS",
            "outcome_other": t2.outcome, "changes": t2.outcome != base.outcome}]
    if base.wait_start_from == "ping":            # the literal reading of Ryde's GPS condition
        out.append({"rule": "CW-F03B", "reading": "wait counted from the GPS confirmation",
                    "other_reading": "no fee when arrival is indicated before GPS shows the driver there",
                    "outcome_other": "WAIVE_FEE", "changes": base.outcome != "WAIVE_FEE"})
    return out


def decide_tier(kb: KB, tr: Trace, sens: list[dict], reads: list[dict]) -> dict:
    tau = kb.pval("TAU", tr.profile, tr.overrides)
    limit = kb.pval("AUTO_LIMIT_SGD", tr.profile, tr.overrides)
    if tr.reclassified_to:
        return {"tier": f"n/a (reclassified to {tr.reclassified_to})", "decisive": [], "triggers": [], "gates": [], "runtime_only_gates": [],
                "favoured_party": None, "tau": tau, "auto_limit": limit}
    decisive = []
    for r in reads:
        if r["changes"] and r["rule"] == "CW-F03B":
            decisive.append((r["rule"], f"the other reading ({r['other_reading']}) gives {r['outcome_other']}"))
        elif r["changes"] and r.get("kind") == "contact":
            decisive.append((r["rule"], f"reading the rider's call, message or GPS ({', '.join(r['ids'])}) as placing the rider at the pick-up gives {r['outcome_other']}"))
        elif r["changes"]:
            decisive.append((r["rule"], f"reading the statement as {r['other_reading']} instead of {r['reading']} gives {r['outcome_other']}"))
    for s in sens:
        if s["decisive"]:
            why = (f"outcome changes when {s['param']} moves within {s['range']}" if s["outcome_changes"] else
                   f"the ruling would rest on a decision-table row rated C or D when {s['param']} moves within {s['range']}")
            for rid in s["rules_using"] or ["(parameter " + s["param"] + ")"]:
                decisive.append((rid, why))
    if tr.dt_row_credibility in ("C", "D") and tr.reasons and tr.reasons[0] not in ("CW-R-OUT-OF-WINDOW", "GEN-R-POLICY-GAP"):
        decisive.append((f"DT-CW-NOSHOW {tr.dt_row}", f"decision-table row rated {tr.dt_row_credibility}"))
    triggers = []
    if tr.policy_gap:
        triggers.append("policy gap: " + "; ".join(f"{r} ({why})" for r, why in tr.policy_gap))
    if decisive:
        triggers.append("decisive: " + "; ".join(f"{r} ({why})" for r, why in decisive))
    if tr.fraud:
        triggers.append("fraud signal on " + ", ".join(f"{who} ({getattr(tr, 'fraud_detail', {}).get(who, '')})" for who, _ in tr.fraud)
                        + " (symmetric trigger; the detail is for the reviewer, not for the parties)")
    if tr.amount_at_stake > limit:
        triggers.append(f"amount S${tr.amount_at_stake:.2f} above AUTO_LIMIT_SGD S${limit:.2f}")
    if tr.confidence["C"] is not None and tr.confidence["C"] < tau:
        triggers.append(f"confidence {tr.confidence['C']:.2f} below TAU {tau}")
    for f, why in (("CONTACT_NOT_ATTEMPTED", "no contact attempt"), ("RECORDS_MISSING", "records missing"),
                   ("GPS_AMBIGUOUS", "GPS cannot settle whether the driver left (GPS_AMBIGUOUS)")):
        if f in tr.flags:
            triggers.append(why)
    if tr.findings.get("F-CHARGE-AMOUNT", {}).get("value", {}).get("status") == "overcharged":
        triggers.append("overcharge (CHARGE_AMOUNT_MISMATCH)")
    upheld = tr.outcome == "UPHOLD" and tr.reasons and tr.reasons[0] == "CW-R-NOSHOW-VALID"
    if "BOUNDARY_MARGIN" in tr.flags and "MARGIN_WITHIN_SPREAD" in tr.flags:
        triggers.append(f"margin {tr.margin:+.0f} s within the boundary band, and the records disagree by up to {tr.spread_max:.0f} s")
    if upheld and tr.pin_mismatch and tr.rider_at_venue_claim:
        triggers.append(f"fee upheld, pin far from {tr.venue_name} and the rider says they were there")
    favoured = {"UPHOLD": "DRIVER", "WAIVE_FEE": "RIDER", "PARTIAL_REFUND": "RIDER", "FULL_REFUND": "RIDER"}.get(tr.outcome)
    if favoured and favoured in tr.injection_authors:
        triggers.append(f"instruction injected by the party the outcome favors ({favoured})")
    gates = []
    if "TIMER_ANCHOR_MISMATCH" in tr.flags or "GPS_DATA_ERROR" in tr.flags:
        gates.append("G1 data inconsistency" + (" (GPS implies an impossible speed)" if "GPS_DATA_ERROR" in tr.flags else ""))
    if tr.findings.get("_safety"):
        gates.append("G4 safety content")
    if tr.confidence["C"] is not None and tr.confidence["C"] < tau:
        gates.append("G5 low confidence")
    if tr.amount_at_stake > limit:
        gates.append("G6 amount above the automatic limit")
    if tr.findings.get("_safety") or tr.outcome == "ESCALATE_HUMAN":     # AUTH-03, AUTH-06: no AI ruling to approve
        tier = "HUMAN"
    elif triggers or gates:
        tier = "APPROVE"
    else:
        tier = "AUTO"
    generic = [r for r, _ in decisive if r.startswith("DT-") or r.startswith("(parameter") or kb.rules.get(r, {}).get("credibility") in ("C", "D")
               or any(s["decisive"] and r in s["rules_using"] for s in sens)]
    if generic:
        tr.flag("GENERIC_ASSUMPTION_USED")
    return {"tier": tier, "decisive": decisive, "triggers": triggers, "gates": gates, "favoured_party": favoured, "tau": tau, "auto_limit": limit,
            "runtime_only_gates": ["G2 rule conflict", "G3 history-aware vs history-blind Judge", "G7 citation and number verification", "G8 Judge runs vs rules engine"]}


def run(kb: KB, case: dict, profile: str | None = None) -> dict:
    base = evaluate(kb, copy.deepcopy(case), profile)
    if base.reclassified_to:
        return {"trace": base, "sensitivity": [], "readings": [], "tier": decide_tier(kb, base, [], []), "case": case}
    sens = sensitivity(kb, case, base.profile, base)
    reads = reading_test(kb, case, base.profile, base) + start_test(kb, case, base.profile, base)
    tier = decide_tier(kb, base, sens, reads)
    base.step("PB-CW-NOSHOW", 19, "AUTH-01 to AUTH-04, AUTH-06", f"tier {tier['tier']}" + (f"; {len(tier['triggers'])} approval trigger(s)" if tier["triggers"] else ""),
              ["F-WAIT-MARGIN", "F-PRESENCE", "F-RIDER-EVIDENCE", "F-PIN-VENUE"])
    base.step("PB-CW-NOSHOW", 20, "EXP-01 to EXP-03, META-05", "explanations drafted from findings only (see the explanation drafts)", ["F-*"])
    return {"trace": base, "sensitivity": sens, "readings": reads, "tier": tier, "case": case}


def dt_enumeration(kb: KB) -> dict:
    import itertools
    dt = kb.y["rules"]["decision_tables"]["DT-CW-NOSHOW"]
    names = list(dt["inputs"])
    out = {"combinations": 0, "unique": 0, "gaps": 0, "overlaps": 0}
    for combo in itertools.product(*[dt["inputs"][n] for n in names]):
        env = dict(zip(names, combo))
        hits = [r for r in dt["rows"] if all(env[k] in (v if isinstance(v, list) else [v]) for k, v in r["when"].items())]
        out["combinations"] += 1
        out["unique"] += len(hits) == 1
        out["gaps"] += len(hits) == 0
        out["overlaps"] += len(hits) > 1
    return out
