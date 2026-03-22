"""
Maps raw PDF player names to player_ids via fuzzy matching.

PDFs use "Last,First" format with no spaces, while the players table uses "First Last".
We normalize first, then fuzzy match — anything below 85/100 confidence returns None.
"""

from thefuzz import process


def normalize_pdf_name(raw: str) -> str:
    """Converts "Last,First" → "First Last" so we can match against the players table."""
    raw = raw.strip()
    if "," in raw:
        last, first = raw.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return raw


def build_player_index(conn) -> dict[str, int]:
    """Loads the players table into a {full_name: player_id} dict for fast lookups."""
    cursor = conn.execute("SELECT player_id, full_name FROM players")
    index = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"  [resolver] Loaded {len(index)} players from DB")
    return index


def resolve_player_id(raw_name: str, index: dict[str, int], threshold: int = 85) -> int | None:
    """Fuzzy-matches a PDF name against the player index. Returns the player_id or None if no confident match."""
    if not index or not raw_name:
        return None

    normalized = normalize_pdf_name(raw_name)
    result = process.extractOne(normalized, index.keys())

    if result and result[1] >= threshold:
        return index[result[0]]

    return None