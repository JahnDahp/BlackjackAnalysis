"""
basic_strategy.py

Reads hit.json, stand.json, double.json, and split.json and prints the
optimal basic strategy decision for every hand vs every dealer upcard.

Tables printed:
  1. Hard hands  (totals 4–21)  vs dealer upcards 2–10, A
  2. Soft hands  (totals 12–21) vs dealer upcards 2–10, A
  3. Split pairs (A–A … 10–10)  vs dealer upcards 2–10, A

Decision codes
  H  = Hit
  S  = Stand
  Dh = Double, else Hit
  Ds = Double, else Stand
  P  = Split
  Ph = Split if DAS, otherwise Hit
  Pd = Split if DAS, otherwise Double

Usage
  python basic_strategy.py [--data-dir PATH] [--decks N]
                           [--s17 | --h17] [--enhc | --us]
                           [--das | --ndas] [--no-color]

Defaults: data_dir=../Data, decks=6, S17, US peek, DAS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

# ── ANSI colour helpers ────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
WHITE  = "\033[97m"
DIM    = "\033[2m"

DECISION_COLOUR = {
    "H":  RED,
    "S":  GREEN,
    "Dh": YELLOW,
    "Ds": YELLOW,
    "P":  CYAN,
    "Ph": CYAN,
    "Pd": CYAN,
}

def coloured(text: str, code: str, use_colour: bool) -> str:
    if not use_colour:
        return text
    colour = DECISION_COLOUR.get(code, WHITE)
    return f"{colour}{BOLD}{text}{RESET}"


# ── JSON loading helpers ───────────────────────────────────────────────────

def load_json(data_dir: str, filename: str) -> Any:
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        sys.exit(f"ERROR: {path} not found.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def deck_key(decks: int) -> str:
    return {1: "oneDeck", 2: "twoDeck", 4: "fourDeck",
            6: "sixDeck", 8: "eightDeck"}[decks]


def get_dataset(data: dict, key: str, decks: int, s17: bool, enhc: bool) -> Any:
    rule  = "S17" if s17 else "H17"
    peek  = "enhc" if enhc else "us"
    return data[key][deck_key(decks)][rule][peek]


# ── EV extractors ─────────────────────────────────────────────────────────

def _ev_from_probs(probs: dict) -> float:
    return probs["winProb"] - probs["loseProb"] - probs["DBJ"]


def stand_ev(probs: dict, hand: list[dict]) -> float:
    """Replicate calcStandEV: BJ pays BJPay, otherwise win-lose-DBJ."""
    total = _hand_total(hand)
    if len(hand) == 2 and total == 21:          # blackjack — not a real strategy row
        return (1 - probs["DBJ"]) * 1.5
    return probs["winProb"] - probs["loseProb"] - probs["DBJ"]


def hit_ev(probs: dict) -> float:
    return _ev_from_probs(probs)


def double_ev(probs: dict) -> float:
    return 2.0 * _ev_from_probs(probs)


def split_ev(probs: dict) -> float:
    """Replicate calcSplitEV (non-DAS path for comparison)."""
    w = probs["noDouble"]["winProb"]
    t = probs["noDouble"]["tieProb"]
    l = probs["noDouble"]["loseProb"]
    d = probs["noDouble"]["DBJ"]
    return 2 * w**2 + 2*w*t - d - 2*l*t - 2*l**2


# ── Hand total utility ─────────────────────────────────────────────────────

def _hand_total(hand: list[dict]) -> int:
    total, aces = 0, 0
    for card in hand:
        r = card["rank"] if isinstance(card, dict) else card
        if r == 1:
            total += 11
            aces += 1
        else:
            total += r
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def _is_soft(hand: list[dict]) -> bool:
    total, aces = 0, 0
    for card in hand:
        r = card["rank"] if isinstance(card, dict) else card
        if r == 1:
            total += 11
            aces += 1
        else:
            total += r
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return aces > 0


# ── Build lookup tables from JSONs ─────────────────────────────────────────
# Each data file stores rows as  [hand_cards, totalProb, probs_dict]
# We need: for each (soft/hard, upcard, total) → best EV per decision

def _build_ev_table(
    stand_ds: dict,
    hit_ds: dict,
    double_ds: dict,
    soft: bool,
) -> dict[tuple[int, int], dict[str, float]]:
    """
    Returns {(upcard_idx 0-9, total): {"S": ev, "H": ev, "Dh": ev, "Ds": ev}}
    upcard_idx: 0=A,1=2,...,9=10  (matches the JSON array order)
    total: 4-21 for hard, 12-21 for soft

    Double is tracked as two separate keys:
      "Dh" -- double; fallback is Hit  (hit EV > stand EV for that composition)
      "Ds" -- double; fallback is Stand (stand EV >= hit EV for that composition)

    EVs are probability-weighted averages across all hand compositions
    that reach the given total.
    """
    accum: dict[tuple[int, int], dict[str, list]] = {}
    key = "soft" if soft else "hard"

    def _hkey(hand_cards):
        return tuple(sorted(
            c["rank"] if isinstance(c, dict) else c for c in hand_cards
        ))

    for upcard_idx in range(10):
        stand_rows  = stand_ds[key][upcard_idx]
        hit_rows    = hit_ds[key][upcard_idx]
        double_rows = double_ds[key][upcard_idx]

        stand_map  = {_hkey(r[0]): (r[1], r[2]) for r in stand_rows}
        hit_map    = {_hkey(r[0]): (r[1], r[2]) for r in hit_rows}
        double_map = {_hkey(r[0]): (r[1], r[2]) for r in double_rows}

        all_keys = set(stand_map) | set(hit_map) | set(double_map)

        for hk in all_keys:
            hand = [{"rank": r} for r in hk]
            total = _hand_total(hand)
            is_s  = _is_soft(hand)
            if soft != is_s:
                continue

            cell_key = (upcard_idx, total)
            if cell_key not in accum:
                accum[cell_key] = {}

            if hk in stand_map:
                prob, probs_dict = stand_map[hk]
                ev = stand_ev(probs_dict, hand)
                acc = accum[cell_key].setdefault("S", [0.0, 0.0])
                acc[0] += ev * prob
                acc[1] += prob

            if hk in hit_map:
                prob, probs_dict = hit_map[hk]
                ev = hit_ev(probs_dict)
                acc = accum[cell_key].setdefault("H", [0.0, 0.0])
                acc[0] += ev * prob
                acc[1] += prob

            if hk in double_map:
                prob, probs_dict = double_map[hk]
                ev = double_ev(probs_dict)
                # Determine fallback by comparing hit vs stand for this composition
                h_ev = hit_ev(hit_map[hk][1]) if hk in hit_map else -999.0
                s_ev = stand_ev(stand_map[hk][1], hand) if hk in stand_map else -999.0
                d_key = "Dh" if h_ev > s_ev else "Ds"
                acc = accum[cell_key].setdefault(d_key, [0.0, 0.0])
                acc[0] += ev * prob
                acc[1] += prob

    result: dict[tuple[int, int], dict[str, float]] = {}
    for cell_key, decisions in accum.items():
        result[cell_key] = {}
        for decision, (ev_sum, prob_sum) in decisions.items():
            result[cell_key][decision] = ev_sum / prob_sum if prob_sum > 0 else 0.0

    return result


def _best_non_split(evs: dict[str, float]) -> str:
    """
    Return the best decision code given {decision: weighted_avg_ev}.
    Keys: S, H, Dh (double/else hit), Ds (double/else stand).
    """
    if not evs:
        return "S"
    return max(evs, key=lambda k: evs[k])


# ── Split decision ─────────────────────────────────────────────────────────

def _split_decision(
    split_ds_das: Any,
    split_ds_ndas: Any,
    stand_ds: dict,
    hit_ds: dict,
    double_ds: dict,
    pair_val: int,     # 1-10
    upcard_idx: int,   # 0=A … 9=10
) -> str:
    """
    Returns P, Ph, Pd, H, S, or D.

    Logic:
      - Compute split EV (DAS) and non-split best EV.
      - If split (DAS) > best non-split → at least split.
      - Check split (nDAS):
          * nDAS > best non-split AND DAS > best non-split → P  (split regardless)
          * DAS > non-split but nDAS ≤ non-split → Ph or Pd depending on fallback
          * Neither beats non-split → best non-split decision
    """
    das_key = "DAS"
    ndas_key = "nDAS"

    def _get_split_ev(ds: Any) -> float | None:
        rows = ds[upcard_idx]  # list of [[{rank:v},{rank:v}], probs_dict]
        for row in rows:
            hand_cards = row[0]
            rv = hand_cards[0]["rank"] if isinstance(hand_cards[0], dict) else hand_cards[0]
            if rv == pair_val:
                return split_ev(row[1])
        return None

    das_ev  = _get_split_ev(split_ds_das)
    ndas_ev = _get_split_ev(split_ds_ndas)

    # Best non-split EV
    hand = [{"rank": pair_val}, {"rank": pair_val}]
    total = _hand_total(hand)
    is_s = _is_soft(hand)

    def _key(h): return tuple(sorted(
        c["rank"] if isinstance(c, dict) else c for c in h
    ))
    hk = _key(hand)

    ns_evs: dict[str, float] = {}
    key_type = "soft" if is_s else "hard"

    # Stand and hit lookups
    for label, ds in (("S", stand_ds), ("H", hit_ds)):
        rows = ds[key_type][upcard_idx]
        for row in rows:
            if _key(row[0]) == hk:
                if label == "S":
                    ns_evs["S"] = stand_ev(row[2], hand)
                elif label == "H":
                    ns_evs["H"] = hit_ev(row[2])
                break

    # Double lookup — determine Dh vs Ds by comparing hit and stand for this pair
    rows = double_ds[key_type][upcard_idx]
    for row in rows:
        if _key(row[0]) == hk:
            d_ev = double_ev(row[2])
            h_ev = ns_evs.get("H", -999.0)
            s_ev = ns_evs.get("S", -999.0)
            d_key = "Dh" if h_ev > s_ev else "Ds"
            ns_evs[d_key] = d_ev
            break

    best_ns_ev   = max(ns_evs.values()) if ns_evs else 0.0
    best_ns_code = _best_non_split(ns_evs)

    das_beats  = das_ev  is not None and das_ev  > best_ns_ev
    ndas_beats = ndas_ev is not None and ndas_ev > best_ns_ev

    if das_beats and ndas_beats:
        return "P"
    if das_beats and not ndas_beats:
        # DAS-only split: Ph if fallback is H/Dh/S, Pd if fallback is Ds
        if best_ns_code == "Ds":
            return "Pd"
        return "Ph"
    return best_ns_code


# ── Table printer ──────────────────────────────────────────────────────────

# Upcard display order: 2,3,4,5,6,7,8,9,10,A  →  JSON indices 1,2,3,4,5,6,7,8,9,0
UPCARD_ORDER   = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]   # indices into the JSON arrays
UPCARD_LABELS  = ["2","3","4","5","6","7","8","9","10","A"]


def _pad(s: str, width: int, use_colour: bool) -> str:
    """Centre-pad ignoring ANSI escape codes."""
    visible = len(s) if not use_colour else len(
        s.replace(RESET,"").replace(BOLD,"")
         .replace(RED,"").replace(GREEN,"")
         .replace(YELLOW,"").replace(CYAN,"")
         .replace(WHITE,"").replace(DIM,"")
    )
    pad = max(0, width - visible)
    left  = pad // 2
    right = pad - left
    return " " * left + s + " " * right


def print_table(
    title: str,
    row_labels: list[str],
    rows: list[list[str]],    # rows[i][j] = decision code
    use_colour: bool,
) -> None:
    col_w  = 5
    row_lw = 6

    sep_line = DIM + "─" * (row_lw + 1 + (col_w + 1) * len(UPCARD_LABELS)) + RESET \
               if use_colour else \
               "─" * (row_lw + 1 + (col_w + 1) * len(UPCARD_LABELS))

    header_row = (
        f"{'':>{row_lw}} │"
        + "│".join(_pad(l, col_w, False) for l in UPCARD_LABELS)
    )

    if use_colour:
        print(f"\n{BOLD}{WHITE}{title}{RESET}")
    else:
        print(f"\n{title}")
    print(sep_line)
    print(header_row)
    print(sep_line)

    for label, row in zip(row_labels, rows):
        cells = "│".join(
            _pad(coloured(code, code, use_colour), col_w, use_colour)
            for code in row
        )
        print(f"{label:>{row_lw}} │{cells}")

    print(sep_line)


def print_legend(use_colour: bool) -> None:
    items = [
        ("H",  "Hit"),
        ("S",  "Stand"),
        ("Dh", "Double, else Hit"),
        ("Ds", "Double, else Stand"),
        ("P",  "Split"),
        ("Ph", "Split if DAS, else Hit"),
        ("Pd", "Split if DAS, else Double"),
    ]
    if use_colour:
        print(f"\n{BOLD}Legend{RESET}")
    else:
        print("\nLegend")
    for code, desc in items:
        print(f"  {coloured(code, code, use_colour):<20} {desc}")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Print blackjack basic strategy tables.")
    parser.add_argument("--data-dir", default="../Data",
                        help="Directory containing the four decision JSON files (default: ../Data)")
    parser.add_argument("--decks", type=int, default=6, choices=[1, 2, 4, 6, 8],
                        help="Number of decks (default: 6)")
    parser.add_argument("--s17",  dest="s17", action="store_true",  default=True,
                        help="Dealer stands on soft 17 (default)")
    parser.add_argument("--h17",  dest="s17", action="store_false",
                        help="Dealer hits on soft 17")
    parser.add_argument("--enhc", dest="enhc", action="store_true",  default=False,
                        help="European No Hole Card rules")
    parser.add_argument("--us",   dest="enhc", action="store_false",
                        help="US peek rules (default)")
    parser.add_argument("--das",  dest="das", action="store_true",  default=True,
                        help="Double After Split allowed (default)")
    parser.add_argument("--ndas", dest="das", action="store_false",
                        help="No Double After Split")
    parser.add_argument("--no-color", dest="colour", action="store_false", default=True,
                        help="Disable ANSI colour output")
    args = parser.parse_args()

    data_dir  = args.data_dir
    decks     = args.decks
    s17       = args.s17
    enhc      = args.enhc
    das       = args.das
    use_colour = args.colour and sys.stdout.isatty() or not args.colour and False
    # Honour explicit --no-color even when not a tty
    use_colour = args.colour

    # Load JSON files
    stand_json  = load_json(data_dir, "stand.json")
    hit_json    = load_json(data_dir, "hit.json")
    double_json = load_json(data_dir, "double.json")
    split_json  = load_json(data_dir, "split.json")

    # Extract the right dataset slice
    stand_ds  = get_dataset(stand_json,  "probs", decks, s17, enhc)
    hit_ds    = get_dataset(hit_json,    "probs", decks, s17, enhc)
    double_ds = get_dataset(double_json, "probs", decks, s17, enhc)
    split_ds_full = get_dataset(split_json, "probs", decks, s17, enhc)
    split_ds_das  = split_ds_full["DAS"]
    split_ds_ndas = split_ds_full["nDAS"]

    rule_str = (
        f"{decks} deck{'s' if decks > 1 else ''}, "
        f"{'S17' if s17 else 'H17'}, "
        f"{'ENHC' if enhc else 'US peek'}, "
        f"{'DAS' if das else 'nDAS'}"
    )

    if use_colour:
        print(f"\n{BOLD}{WHITE}Basic Strategy — {rule_str}{RESET}")
    else:
        print(f"\nBasic Strategy — {rule_str}")

    # ── Build EV tables ─────────────────────────────────────────────────
    hard_ev_table = _build_ev_table(stand_ds, hit_ds, double_ds, soft=False)
    soft_ev_table = _build_ev_table(stand_ds, hit_ds, double_ds, soft=True)

    # ── Hard hands table ────────────────────────────────────────────────
    hard_row_labels = [str(t) for t in range(4, 22)]
    hard_rows: list[list[str]] = []
    for total in range(4, 22):
        row = []
        for ui in UPCARD_ORDER:
            evs = hard_ev_table.get((ui, total), {})
            row.append(_best_non_split(evs) if evs else "S")
        hard_rows.append(row)

    print_table("Hard Hands", hard_row_labels, hard_rows, use_colour)

    # ── Soft hands table ────────────────────────────────────────────────
    soft_row_labels = [f"A,{t - 11}" if t <= 21 else "A,10" for t in range(12, 22)]
    soft_rows: list[list[str]] = []
    for total in range(12, 22):
        row = []
        for ui in UPCARD_ORDER:
            evs = soft_ev_table.get((ui, total), {})
            row.append(_best_non_split(evs) if evs else "S")
        soft_rows.append(row)

    print_table("Soft Hands", soft_row_labels, soft_rows, use_colour)

    # ── Pairs table ─────────────────────────────────────────────────────
    pair_labels = ["A,A","2,2","3,3","4,4","5,5","6,6","7,7","8,8","9,9","10,10"]
    pair_rows: list[list[str]] = []
    for pair_val in range(1, 11):   # 1=A … 10=10
        row = []
        for ui in UPCARD_ORDER:
            decision = _split_decision(
                split_ds_das, split_ds_ndas,
                stand_ds, hit_ds, double_ds,
                pair_val, ui,
            )
            row.append(decision)
        pair_rows.append(row)

    print_table("Pairs (Split)", pair_labels, pair_rows, use_colour)

    print_legend(use_colour)
    print()


if __name__ == "__main__":
    main()