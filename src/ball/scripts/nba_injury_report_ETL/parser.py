"""
Parses a raw NBA injury report PDF into a state dict keyed by (player_name, team).

We use line-by-line text extraction because pdfplumber's extract_table() doesn't
work here — the PDFs have no visible borders. One quirk: the reason string sometimes
appears on the line *before* the player row, so we carry it forward as a prefix.

Two PDF formats exist across seasons:
    New (2025-26+): names are "Last,First" (no space), time tokens are "07:00(ET)"
    Old (pre-2025):  names are "Last, First" (space after comma), time is "07:00 (ET)"
                     and older PDFs often pack multiple players on a single line.
"""

import io
import re
from datetime import date

import pdfplumber

from config import VALID_STATUSES
from transform import extract_body_region, extract_diagnosis

STATUS_RE  = re.compile(r'\b(Out|Available|Questionable|Doubtful|Probable|GTD)\b')
DATE_RE    = re.compile(r'^\d{2}/\d{2}/\d{4}')
TIME_RE    = re.compile(r'^\d{2}:\d{2}')   # matches "07:00" and "07:00(ET)"
MATCHUP_RE = re.compile(r'[A-Z]{2,3}@[A-Z]{2,3}')

# Name suffixes that appear as a separate token before the comma in older PDFs
# e.g. "Bagley III, Marvin" → tokens ["Bagley", "III,", "Marvin"]
SUFFIXES = {'Jr', 'Jr.', 'Sr', 'Sr.', 'II', 'III', 'IV', 'V'}

# Regex to find the start of each player entry in older PDFs where multiple
# players are concatenated on one line: "Banton, Dalano Out Dowtin Jr., Jeff Out ..."
_ENTRY_RE = re.compile(
    r'[A-Z][a-zA-Z\'\-]+'                        # last name (or suffix lead)
    r'(?:\s+(?:Jr\.?|Sr\.?|II|III|IV|V))?'       # optional suffix
    r',\s*'                                        # comma
    r'[A-Z][a-zA-Z\'\.\-]+'                       # first name
    r'\s+(?:Out|Available|Questionable|Doubtful|Probable|GTD)'  # status
)


def _is_skip_line(line: str) -> bool:
    if not line:
        return True
    if re.search(r'Page\s*\d+\s*of\s*\d+', line, re.IGNORECASE):
        return True
    if re.search(r'Injury Report:', line, re.IGNORECASE):
        return True
    # Header row — both old and new format variations
    if 'PlayerName' in line or 'Player Name' in line or 'GameDate' in line or 'Game Date' in line:
        return True
    if 'NOTYETSUBMITTED' in line.upper().replace(' ', ''):
        return True
    return False


def _split_player_entries(line: str) -> list[str]:
    """
    Split a line that has multiple players packed together (common in older PDFs).
    e.g. "Banton, Dalano Out Dowtin Jr., Jeff Out Koloko, Christian Out"
    → ["Banton, Dalano Out", "Dowtin Jr., Jeff Out", "Koloko, Christian Out"]
    If only one (or zero) player entries found, returns the line as-is.
    """
    matches = list(_ENTRY_RE.finditer(line))
    if len(matches) <= 1:
        return [line]
    result = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        result.append(line[m.start():end].strip())
    return result


def _extract_team_from_tokens(tokens: list[str]) -> str | None:
    """Strips date/time/matchup tokens and returns whatever's left as the team name."""
    team_tokens = []
    for token in tokens:
        if DATE_RE.match(token):
            continue
        if TIME_RE.match(token):
            continue
        if token == '(ET)':          # older PDFs have this as a standalone token
            continue
        if MATCHUP_RE.match(token):
            continue
        team_tokens.append(token)
    return ' '.join(team_tokens) if team_tokens else None


def _parse_player_line(line: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns (player, status, reason_inline, team) from a player line, or all None if it's not one."""
    if ',' not in line:
        return None, None, None, None

    m = STATUS_RE.search(line)
    if not m:
        return None, None, None, None

    status = m.group(1)
    before_status = line[:m.start()].strip()
    after_status  = line[m.end():].strip()

    if after_status == '-':
        after_status = ''

    tokens = before_status.split()

    # Find the comma-containing token — marks the player name boundary
    player = None
    player_idx = None
    for idx, token in enumerate(tokens):
        if ',' in token:
            player = token
            player_idx = idx
            break

    if player is None:
        return None, None, None, None

    name_start = player_idx

    # Old format: the comma token ends with "," meaning name and first name are separate.
    # e.g. "Banton," + "Dalano" or suffix case "III," with "Bagley" before and "Marvin" after.
    if player.endswith(','):
        token_core = player.rstrip(',')

        # If this token is a suffix (Jr., III, etc.), the real last name is one token back
        if token_core in SUFFIXES and player_idx > 0:
            player = tokens[player_idx - 1] + ' ' + player  # "Bagley III,"
            name_start = player_idx - 1

        # Look ahead one token for the first name
        first_idx = player_idx + 1
        if first_idx < len(tokens):
            next_tok = tokens[first_idx]
            if next_tok and not STATUS_RE.match(next_tok):
                player = player + next_tok  # "Banton,Dalano" or "Bagley III,Marvin"

    before_player  = tokens[:name_start]
    team_in_line   = _extract_team_from_tokens(before_player)

    return player, status, after_status, team_in_line


def _is_player_line(line: str) -> bool:
    return ',' in line and bool(STATUS_RE.search(line))


def parse_pdf(pdf_bytes: bytes, report_date: date) -> dict:
    # Collect all lines from every page, splitting multi-player lines as we go
    raw_lines: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    raw_lines.extend(_split_player_entries(line.strip()))

    state: dict = {}
    current_team: str | None = None
    pending_reason_prefix: str | None = None

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].strip()
        i += 1

        if _is_skip_line(line):
            pending_reason_prefix = None
            continue

        player, status, reason_inline, team_in_line = _parse_player_line(line)

        if player and status:
            if team_in_line:
                current_team = team_in_line

            reason_parts = []

            if pending_reason_prefix:
                reason_parts.append(pending_reason_prefix)
                pending_reason_prefix = None

            if reason_inline:
                reason_parts.append(reason_inline)
            else:
                # No inline reason — look ahead one line for it
                if i < len(raw_lines):
                    next_line = raw_lines[i].strip()
                    if next_line and not _is_player_line(next_line) and not _is_skip_line(next_line):
                        reason_parts.append(next_line)
                        i += 1

            reason = ' '.join(reason_parts).strip() or None

            if current_team:
                state[(player, current_team)] = {
                    "status":      status,
                    "reason":      reason,
                    "body_region": extract_body_region(reason),
                    "diagnosis":   extract_diagnosis(reason),
                    "report_date": report_date,
                }
        else:
            # Not a player line — could be a reason prefix for the next player
            pending_reason_prefix = line

    return state
