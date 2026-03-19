"""
Parses a raw NBA injury report PDF into a state dict.

Uses extract_text() line-by-line because extract_table() only returns the
header row — the PDFs have no visible table borders for pdfplumber to detect.

Wrapping pattern in the raw text:
    'Injury/Illness-RightAnkle;Injury'   ← reason prefix (right column, read first)
    'Gafford,Daniel Out'                 ← player + status (no inline reason)
    'Management'                         ← reason suffix

State dict shape:
    {
        (player_name, team): {
            "status": str,
            "reason": str,
            "body_region": str | None,
            "report_date": date,
        },
        ...
    }
"""

import io
import re
from datetime import date

import pdfplumber

from config import VALID_STATUSES
from transform import extract_body_region

STATUS_RE = re.compile(r'\b(Out|Available|Questionable|Doubtful|Probable|GTD)\b')
DATE_RE = re.compile(r'^\d{2}/\d{2}/\d{4}')
TIME_RE = re.compile(r'\d{2}:\d{2}\(ET\)')
MATCHUP_RE = re.compile(r'[A-Z]{2,3}@[A-Z]{2,3}')


def _is_skip_line(line: str) -> bool:
    if not line:
        return True
    if re.search(r'Page\s*\d+\s*of\s*\d+', line, re.IGNORECASE):
        return True
    if re.search(r'Injury Report:', line, re.IGNORECASE):
        return True
    if 'PlayerName' in line or 'GameDate' in line:
        return True
    if 'NOTYETSUBMITTED' in line.upper().replace(' ', ''):
        return True
    return False


def _parse_player_line(line: str) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Extract (player, status, reason_inline, team_in_line) from a line.
    Returns (None, None, None, None) if line is not a player row.
    """
    if ',' not in line:
        return None, None, None, None

    m = STATUS_RE.search(line)
    if not m:
        return None, None, None, None

    status = m.group(1)
    before_status = line[:m.start()].strip()
    after_status = line[m.end():].strip()

    # Normalize placeholder reasons
    if after_status == '-':
        after_status = ''

    tokens = before_status.split()

    # Find the player token — the one with a comma
    player = None
    player_idx = None
    for idx, token in enumerate(tokens):
        if ',' in token:
            player = token
            player_idx = idx
            break

    if player is None:
        return None, None, None, None

    # Tokens before the player: may include date, time, matchup, team name
    before_player = tokens[:player_idx]
    team_in_line = _extract_team_from_tokens(before_player)

    return player, status, after_status, team_in_line


def _extract_team_from_tokens(tokens: list[str]) -> str | None:
    """Strip date/time/matchup tokens, return the rest as a team name."""
    team_tokens = []
    for token in tokens:
        if DATE_RE.match(token):
            continue
        if TIME_RE.search(token):
            continue
        if MATCHUP_RE.match(token):
            continue
        team_tokens.append(token)
    return ' '.join(team_tokens) if team_tokens else None


def _is_player_line(line: str) -> bool:
    return ',' in line and bool(STATUS_RE.search(line))


def parse_pdf(pdf_bytes: bytes, report_date: date) -> dict:
    # Collect all lines from every page
    all_lines: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_lines.extend(text.split('\n'))

    state: dict = {}
    current_team: str | None = None
    pending_reason_prefix: str | None = None

    i = 0
    while i < len(all_lines):
        line = all_lines[i].strip()
        i += 1

        if _is_skip_line(line):
            pending_reason_prefix = None
            continue

        player, status, reason_inline, team_in_line = _parse_player_line(line)

        if player and status:
            # Update team context if this line carries a team name
            if team_in_line:
                current_team = team_in_line

            # Build full reason from prefix + inline + optional suffix
            reason_parts = []

            if pending_reason_prefix:
                reason_parts.append(pending_reason_prefix)
                pending_reason_prefix = None

            if reason_inline:
                reason_parts.append(reason_inline)
            else:
                # No inline reason — look ahead one line for the suffix
                if i < len(all_lines):
                    next_line = all_lines[i].strip()
                    if next_line and not _is_player_line(next_line) and not _is_skip_line(next_line):
                        reason_parts.append(next_line)
                        i += 1  # consume the suffix line

            reason = ' '.join(reason_parts).strip()

            if current_team:
                state[(player, current_team)] = {
                    "status": status,
                    "reason": reason,
                    "body_region": extract_body_region(reason),
                    "report_date": report_date,
                }
        else:
            # Not a player line — treat as potential reason prefix for the next player
            pending_reason_prefix = line

    return state
