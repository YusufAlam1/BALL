"""
Data transformation helpers.

- extract_body_region: parses body part from a reason string
- diff_states: compares two state dicts and returns DB-ready change events

Ported and adapted from injury_clustering/body_region_extraction.ipynb
"""

import re
from collections import OrderedDict
from datetime import date


# ---------------------------------------------------------------------------
# Body region extraction
# ---------------------------------------------------------------------------

BODY_PART_PATTERNS = OrderedDict([
    ("back", [r"\blumbar\b", r"\bback\b", r"\blower back\b", r"\bspine\b", r"\bspinal\b",
              r"\bsciatica\b", r"\bthoracic\b", r"\bdisc\b", r"\bdisk\b", r"\blumbosacral\b"]),
    ("neck", [r"\bneck\b", r"\bcervical\b"]),
    ("head", [r"\bhead\b", r"\bskull\b", r"\bconcussion\b"]),
    ("eye", [r"\beye\b", r"\borbital\b"]),
    ("nose", [r"\bnose\b", r"\bnasal\b"]),
    ("shoulder", [r"\bshoulder\b", r"\brotator cuff\b", r"\bclavicle\b", r"\bscapula\b", r"\bdeltoid\b"]),
    ("elbow", [r"\belbow\b", r"\bolecranon\b"]),
    ("wrist", [r"\bwrist\b", r"\bcarpal\b"]),
    ("finger", [r"\bfinger\b", r"\bthumb\b", r"\bdigit\b"]),
    ("hand", [r"\bhand\b", r"\bmetacarpal\b", r"\bpalm\b"]),
    ("arm", [r"\barm\b", r"\bbicep\b", r"\btricep\b", r"\bhumerus\b", r"\bforearm\b"]),
    ("chest", [r"\bchest\b", r"\bpectoral\b", r"\bsternum\b"]),
    ("ribs", [r"\brib\b", r"\bribs\b", r"\bcostal\b"]),
    ("abdomen", [r"\babdomen\b", r"\babdominal\b", r"\boblique\b", r"\bcore\b", r"\bhernia\b"]),
    ("groin", [r"\bgroin\b", r"\badductor\b", r"\binguinal\b", r"\bhip flexor\b"]),
    ("hip", [r"\bhip\b", r"\blabrum\b", r"\btrochanter\b", r"\babductor\b"]),
    ("pelvis", [r"\bpelvis\b", r"\bpelvic\b", r"\bsacroiliac\b"]),
    ("acl", [r"\bACL\b", r"\banterior cruciate\b"]),
    ("mcl", [r"\bMCL\b", r"\bmedial collateral\b"]),
    ("meniscus", [r"\bmeniscus\b", r"\bmeniscal\b"]),
    ("knee", [r"\bknee\b", r"\bpatella\b", r"\bpatellar\b", r"\bPCL\b", r"\bLCL\b"]),
    ("hamstring", [r"\bhamstring\b", r"\bbiceps femoris\b"]),
    ("quadriceps", [r"\bquad\b", r"\bquadriceps\b", r"\bquadricep\b"]),
    ("thigh", [r"\bthigh\b", r"\bfemur\b", r"\bfemoral\b"]),
    ("achilles", [r"\bachilles\b"]),
    ("calf", [r"\bcalf\b", r"\bgastrocnemius\b", r"\bsoleus\b"]),
    ("shin", [r"\bshin\b", r"\btibia\b", r"\bfibula\b"]),
    ("ankle", [r"\bankle\b", r"\bmalleolus\b"]),
    ("foot", [r"\bfoot\b", r"\bfeet\b", r"\bmetatarsal\b", r"\bplantar\b", r"\bfascia\b"]),
    ("heel", [r"\bheel\b", r"\bcalcaneus\b"]),
    ("toe", [r"\btoe\b", r"\bbig toe\b", r"\bhallux\b"]),
    ("leg", [r"\bleg\b", r"\btibia\b"]),
])

EXCLUSION_RULES = {
    "finger": ["hand"],
    "wrist": ["hand", "arm"],
    "toe": ["foot"],
    "heel": ["foot"],
    "achilles": ["foot", "calf", "leg"],
    "ankle": ["foot", "leg"],
    "shin": ["leg"],
    "calf": ["leg"],
    "acl": ["knee", "leg"],
    "mcl": ["knee", "leg"],
    "meniscus": ["knee", "leg"],
    "knee": ["leg"],
    "hamstring": ["thigh", "leg"],
    "quadriceps": ["thigh", "leg"],
    "thigh": ["leg"],
    "elbow": ["arm"],
    "shoulder": ["arm"],
    "groin": ["hip", "abdomen"],
}


def _split_camel(text: str) -> str:
    """Insert spaces before uppercase letters so 'LeftKnee' → 'Left Knee'."""
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)


def extract_body_region(reason: str) -> str | None:
    if not reason:
        return None
    notes_lower = _split_camel(reason).lower()
    detected = []
    for body_part, patterns in BODY_PART_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, notes_lower, re.IGNORECASE):
                detected.append(body_part)
                break
    excluded = set()
    for part in detected:
        for excl in EXCLUSION_RULES.get(part, []):
            excluded.add(excl)
    seen = set()
    result = []
    for part in detected:
        if part not in excluded and part not in seen:
            seen.add(part)
            result.append(part)
    return ",".join(result) if result else None


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def diff_states(previous: dict, current: dict, report_date: date) -> list[dict]:
    """
    Compare two state dicts, return DB-ready change events for the injury_list table.

    New player in current  → relinquished (went onto report)
    Player gone from current → acquired (cleared from report)
    """
    events = []

    for (player, team), data in current.items():
        if (player, team) not in previous:
            events.append({
                "Date": report_date,
                "Team": team,
                "Acquired": None,
                "Relinquished": player,
                "Notes": data["reason"],
                "player_name": player,
                "player_id": None,
                "body_region": data["body_region"],
            })

    for (player, team), data in previous.items():
        if (player, team) not in current:
            events.append({
                "Date": report_date,
                "Team": team,
                "Acquired": player,
                "Relinquished": None,
                "Notes": data["reason"],
                "player_name": player,
                "player_id": None,
                "body_region": data["body_region"],
            })

    return events
