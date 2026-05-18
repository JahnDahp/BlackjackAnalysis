"""
CalcIterations.py

Calculates the minimum Monte Carlo iterations required per strategy cell
to distinguish the best decision from the second-best at 95% confidence.

Uses worst-case rules (8D H17 ENHC) as an upper bound — any other rule set
will require fewer iterations. Outputs four CSVs into the Simulator folder:
  Hard_Iterations.csv, Soft_Iterations.csv,
  Pairs_DAS_Iterations.csv, Pairs_NDAS_Iterations.csv

Usage:
    python CalcIterations.py --data-dir ../data
    python CalcIterations.py --data-dir ../data --confidence 0.99
"""

from __future__ import annotations

import argparse
import json
import math
import os
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Worst-case settings (8D H17 ENHC)
# ---------------------------------------------------------------------------
DECKS   = 8
S17     = False   # H17
ENHC    = True
BJ_PAY  = 1.5
CONFIDENCE = 0.95   # overrideable from CLI

DECK_MAP = {1:"oneDeck", 2:"twoDeck", 4:"fourDeck", 6:"sixDeck", 8:"eightDeck"}


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load(data_dir: str, filename: str) -> dict:
    with open(os.path.join(data_dir, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def _get_ds(data: dict, decks: int, s17: bool, enhc: bool) -> Any:
    return data[DECK_MAP[decks]]["S17" if s17 else "H17"]["enhc" if enhc else "us"]


# ---------------------------------------------------------------------------
# EV / Variance formulas
# ---------------------------------------------------------------------------

def stand_ev(s: dict) -> float:
    return s["winProb"] - s["loseProb"] - s["DBJ"]

def stand_var(s: dict) -> float:
    return 1.0 - s["tieProb"] - stand_ev(s) ** 2

def hit_ev(h: dict) -> float:
    return h["winProb"] - h["loseProb"] - h["DBJ"]

def hit_var(h: dict) -> float:
    return 1.0 - h["tieProb"] - hit_ev(h) ** 2

def double_ev(d: dict) -> float:
    return 2.0 * (d["winProb"] - d["loseProb"] - d["DBJ"])

def double_var(d: dict) -> float:
    return 4.0 * (1.0 - d["tieProb"]) - double_ev(d) ** 2

def split_ev(sp: dict, das: bool) -> float:
    w2=sp["double"]["winProb"]; t2=sp["double"]["tieProb"]; l2=sp["double"]["loseProb"]
    w=sp["noDouble"]["winProb"]; t=sp["noDouble"]["tieProb"]
    l=sp["noDouble"]["loseProb"]; d=sp["noDouble"]["DBJ"]
    if das:
        return (4*w2**2 + 3*2*w2*w + 2*(2*w2*(t+t2)+w**2) + (2*w2*l+2*w*(t+t2))
                - d - (2*l2*w+2*l*(t+t2)) - 2*(2*l2*(t+t2)+l**2) - 3*2*l2*l - 4*l2**2)
    return 2*w**2 + 2*w*t - d - 2*l*t - 2*l**2

def split_var(sp: dict, das: bool) -> float:
    w2=sp["double"]["winProb"]; t2=sp["double"]["tieProb"]; l2=sp["double"]["loseProb"]
    w=sp["noDouble"]["winProb"]; t=sp["noDouble"]["tieProb"]; l=sp["noDouble"]["loseProb"]
    ev = split_ev(sp, das)
    if das:
        win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2
        tie=2*w2*l2+2*w*l+(t+t2)**2
        lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
        return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie-ev**2
    return 1+3*(w**2+l**2)-(2*w*l+t**2)-ev**2


# ---------------------------------------------------------------------------
# Iteration formula  N = z² × (σ₁² + σ₂²) / Δ²
# ---------------------------------------------------------------------------

def required_n(var1: float, var2: float, delta: float, z: float) -> int:
    if delta <= 1e-10:
        return 0
    return math.ceil(z**2 * (var1 + var2) / delta**2)


# ---------------------------------------------------------------------------
# Weighted EV/Var across compositions for one total
# ---------------------------------------------------------------------------

def _card_total(hand: list) -> int:
    t = aces = 0
    for c in hand:
        r = c["rank"] if isinstance(c, dict) else c
        if r == 1: t += 11; aces += 1
        else: t += r
    while t > 21 and aces > 0: t -= 10; aces -= 1
    return t


def _weighted(entries: list, ev_fn, var_fn) -> tuple[float, float]:
    tp = sum(e[1] for e in entries)
    if tp == 0: return 0.0, 1.0
    w_ev  = sum(ev_fn(e[2]) * e[1] for e in entries) / tp
    w_var = sum(var_fn(e[2]) * e[1] for e in entries) / tp
    w_var += sum((ev_fn(e[2]) - w_ev)**2 * e[1] for e in entries) / tp
    return w_ev, w_var


def _group_by_total(ds_upcard: list, two_card_only: bool = False) -> dict[int, list]:
    by_total: dict[int, list] = {}
    for entry in ds_upcard:
        if two_card_only and len(entry[0]) != 2:
            continue
        t = _card_total(entry[0])
        by_total.setdefault(t, []).append(entry)
    return by_total


# ---------------------------------------------------------------------------
# Build one matrix of iteration counts
# ---------------------------------------------------------------------------

def _build_hsd_matrix(
    stand_ds, hit_ds, double_ds,
    hand_type: str,
    totals: range,
    z: float,
) -> pd.DataFrame:
    up_labels = ["2","3","4","5","6","7","8","9","10","A"]
    rows = []

    for total in totals:
        row = []
        for uc_idx in range(10):
            s_by_t = _group_by_total(stand_ds[hand_type][uc_idx])
            h_by_t = _group_by_total(hit_ds[hand_type][uc_idx])
            d_by_t = _group_by_total(double_ds[hand_type][uc_idx], two_card_only=True)

            s_entries = s_by_t.get(total, [])
            h_entries = h_by_t.get(total, [])
            d_entries = d_by_t.get(total, [])

            if not s_entries:
                row.append(0)
                continue

            evs = {}
            if d_entries:
                # Double only available on 2-card hands — use 2-card entries for all
                s2 = _group_by_total(stand_ds[hand_type][uc_idx], two_card_only=True).get(total, [])
                h2 = _group_by_total(hit_ds[hand_type][uc_idx],   two_card_only=True).get(total, [])
                if s2: evs["S"] = _weighted(s2, stand_ev, stand_var)
                if h2: evs["H"] = _weighted(h2, hit_ev, hit_var)
                evs["D"] = _weighted(d_entries, double_ev, double_var)
            else:
                # No double available — use all-card stand/hit
                evs["S"] = _weighted(s_entries, stand_ev, stand_var)
                if h_entries: evs["H"] = _weighted(h_entries, hit_ev, hit_var)

            sorted_evs = sorted(evs.items(), key=lambda x: x[1][0], reverse=True)
            _, (best_ev, best_var)   = sorted_evs[0]
            _, (second_ev, second_var) = sorted_evs[1]

            delta = best_ev - second_ev
            # Worst case per total = max N across all decision pairs
            pairs_for_n = [
                (required_n(v1, v2, abs(e1-e2), z), abs(e1-e2),
                 c1, c2, e1, e2, v1, v2)
                for i, (c1, (e1,v1)) in enumerate(sorted_evs)
                for j, (c2, (e2,v2)) in enumerate(sorted_evs)
                if i < j
            ]
            worst = max(pairs_for_n, key=lambda x: x[0])
            n = worst[0]
            row.append(n)
        rows.append(row)

    df = pd.DataFrame(rows, index=list(totals), columns=up_labels)
    df.index.name = "Hand"
    return df


def _build_pairs_matrix(
    stand_ds, hit_ds, double_ds, split_pairs,
    das: bool, z: float,
) -> pd.DataFrame:
    up_labels  = ["2","3","4","5","6","7","8","9","10","A"]
    pair_order = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    pair_labels= ["10","9","8","7","6","5","4","3","2","A"]

    rows = []
    for pair_val in pair_order:
        row = []
        pair_rank = pair_val  # 1=A, 2-10 as-is
        is_soft   = (pair_rank == 1)
        ht        = "soft" if is_soft else "hard"

        for uc_idx in range(10):
            # Stand/Hit/Double: find the [pair_rank, pair_rank] entry
            def _pair_entries(ds_ht):
                return [e for e in ds_ht[ht][uc_idx]
                        if len(e[0]) == 2
                        and e[0][0]["rank"] == pair_rank
                        and e[0][1]["rank"] == pair_rank]

            s_entries = _pair_entries(stand_ds)
            h_entries = _pair_entries(hit_ds)
            d_entries = _pair_entries(double_ds)

            # Split
            sp_entry = split_pairs[uc_idx][pair_rank - 1]
            sp_dict  = sp_entry[1]
            sp_ev_v  = split_ev(sp_dict, das)
            sp_var_v = split_var(sp_dict, das)

            evs = {"P": (sp_ev_v, sp_var_v)}
            if s_entries: evs["S"] = _weighted(s_entries, stand_ev, stand_var)
            if h_entries: evs["H"] = _weighted(h_entries, hit_ev, hit_var)
            if d_entries: evs["D"] = _weighted(d_entries, double_ev, double_var)

            if len(evs) < 2:
                row.append(0)
                continue

            sorted_evs = sorted(evs.items(), key=lambda x: x[1][0], reverse=True)

            pairs_for_n = [
                (required_n(v1, v2, abs(e1-e2), z), abs(e1-e2),
                 c1, c2, e1, e2, v1, v2)
                for i, (c1, (e1,v1)) in enumerate(sorted_evs)
                for j, (c2, (e2,v2)) in enumerate(sorted_evs)
                if i < j
            ]
            worst = max(pairs_for_n, key=lambda x: x[0])
            n = worst[0]
            row.append(n)
        rows.append(row)

    df = pd.DataFrame(rows, index=pair_labels, columns=up_labels)
    df.index.name = "Hand"
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate worst-case Monte Carlo iterations per strategy cell "
            "(assumes 8D H17 ENHC as upper bound). Outputs CSVs to Simulator folder."
        )
    )
    parser.add_argument("--data-dir",   dest="data_dir", default=None,
                        help="Path to JSON data directory (default: ../data relative to this script)")
    parser.add_argument("--out-dir",    dest="out_dir",  default=None,
                        help="Output directory (default: same folder as this script)")
    parser.add_argument("--confidence", type=float, default=CONFIDENCE)
    args = parser.parse_args()

    # Inverse normal CDF via rational approximation (Beasley-Springer-Moro)
    def norm_ppf(p: float) -> float:
        a = [0, -3.969683028665376e+01, 2.209460984245205e+02,
             -2.759285104469687e+02, 1.383577518672690e+02,
             -3.066479806614716e+01, 2.506628277459239e+00]
        b = [0, -5.447609879822406e+01, 1.615858368580409e+02,
             -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
        c = [0, -7.784894002430293e-03, -3.223964580411365e-01,
             -2.400758277161838e+00, -2.549732539343734e+00,
              4.374664141464968e+00, 2.938163982698783e+00]
        d = [0, 7.784695709041462e-03, 3.224671290700398e-01,
             2.445134137142996e+00, 3.754408661907416e+00]
        p_low, p_high = 0.02425, 1 - 0.02425
        if p < p_low:
            q = math.sqrt(-2 * math.log(p))
            return (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) /                    ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
        elif p <= p_high:
            q = p - 0.5; r = q*q
            return (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q /                    (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
        else:
            q = math.sqrt(-2 * math.log(1 - p))
            return -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) /                     ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)

    z = norm_ppf(args.confidence)
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(__file__))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = args.data_dir or os.path.normpath(os.path.join(script_dir, "..", "data"))

    print(f"Worst-case rules: {DECKS}D  {'S17' if S17 else 'H17'}  {'ENHC' if ENHC else 'US'}")
    print(f"Confidence: {args.confidence*100:.0f}%  (z={z:.3f})")
    print(f"Loading JSON data from: {data_dir}\n")

    stand_raw  = _load(data_dir, "stand.json")
    hit_raw    = _load(data_dir, "hit.json")
    double_raw = _load(data_dir, "double.json")
    split_raw  = _load(data_dir, "split.json")

    stand_ds  = _get_ds(stand_raw["probs"],  DECKS, S17, ENHC)
    hit_ds    = _get_ds(hit_raw["probs"],    DECKS, S17, ENHC)
    double_ds = _get_ds(double_raw["probs"], DECKS, S17, ENHC)
    split_ds  = _get_ds(split_raw["probs"],  DECKS, S17, ENHC)

    # ── Hard ──────────────────────────────────────────────────────────────
    print("Computing Hard...")
    hard_df = _build_hsd_matrix(stand_ds, hit_ds, double_ds, "hard", range(21, 3, -1), z)
    hard_path = os.path.join(out_dir, "Hard_Iterations.csv")
    hard_df.to_csv(hard_path)
    print(f"  Saved -> {hard_path}")
    print(hard_df.to_string())

    # ── Soft ──────────────────────────────────────────────────────────────
    print("\nComputing Soft...")
    soft_df = _build_hsd_matrix(stand_ds, hit_ds, double_ds, "soft", range(21, 12, -1), z)
    soft_path = os.path.join(out_dir, "Soft_Iterations.csv")
    soft_df.to_csv(soft_path)
    print(f"  Saved -> {soft_path}")
    print(soft_df.to_string())

    # ── Pairs DAS ─────────────────────────────────────────────────────────
    print("\nComputing Pairs DAS...")
    pairs_das_df = _build_pairs_matrix(stand_ds, hit_ds, double_ds, split_ds["DAS"], das=True, z=z)
    pairs_das_path = os.path.join(out_dir, "Pairs_DAS_Iterations.csv")
    pairs_das_df.to_csv(pairs_das_path)
    print(f"  Saved -> {pairs_das_path}")
    print(pairs_das_df.to_string())

    # ── Pairs nDAS ────────────────────────────────────────────────────────
    print("\nComputing Pairs nDAS...")
    pairs_ndas_df = _build_pairs_matrix(stand_ds, hit_ds, double_ds, split_ds["nDAS"], das=False, z=z)
    pairs_ndas_path = os.path.join(out_dir, "Pairs_NDAS_Iterations.csv")
    pairs_ndas_df.to_csv(pairs_ndas_path)
    print(f"  Saved -> {pairs_ndas_path}")
    print(pairs_ndas_df.to_string())

    # ── Summary ───────────────────────────────────────────────────────────
    all_dfs = {
        "Hard": hard_df, "Soft": soft_df,
        "Pairs_DAS": pairs_das_df, "Pairs_NDAS": pairs_ndas_df,
    }
    # Compute per-cell deltas for diagnostic output
    def _cell_details(stand_ds, hit_ds, double_ds, hand_type, total, uc_idx, z):
        """Return all EVs and the worst-case delta for one cell."""
        up_labels = ["2","3","4","5","6","7","8","9","10","A"]
        d_by_t = _group_by_total(double_ds[hand_type][uc_idx], two_card_only=True)
        d_entries = d_by_t.get(total, [])
        if d_entries:
            s2 = _group_by_total(stand_ds[hand_type][uc_idx], two_card_only=True).get(total, [])
            h2 = _group_by_total(hit_ds[hand_type][uc_idx],   two_card_only=True).get(total, [])
            evs = {}
            if s2: evs["S"] = _weighted(s2, stand_ev, stand_var)
            if h2: evs["H"] = _weighted(h2, hit_ev, hit_var)
            evs["D"] = _weighted(d_entries, double_ev, double_var)
        else:
            s_entries = _group_by_total(stand_ds[hand_type][uc_idx]).get(total, [])
            h_entries = _group_by_total(hit_ds[hand_type][uc_idx]).get(total, [])
            evs = {}
            if s_entries: evs["S"] = _weighted(s_entries, stand_ev, stand_var)
            if h_entries: evs["H"] = _weighted(h_entries, hit_ev, hit_var)
        return evs

    print("\n" + "="*50)
    print("SUMMARY — Max iterations per table:")
    overall_max = 0
    for name, df in all_dfs.items():
        mx = int(df.values.max())
        overall_max = max(overall_max, mx)
        idx = df.stack().idxmax()
        hand_str, col = str(idx[0]), idx[1]
        uc_idx = ["2","3","4","5","6","7","8","9","10","A"].index(col)

        # Get EVs for diagnostic
        detail_str = ""
        if name in ("Hard", "Soft"):
            ht = name.lower()
            total_val = int(hand_str) if hand_str.isdigit() else None
            if total_val:
                evs = _cell_details(stand_ds, hit_ds, double_ds, ht, total_val, uc_idx, z)
                ev_parts = "  ".join(f"{k}={v[0]:.4f}(var={v[1]:.3f})" for k,v in sorted(evs.items(), key=lambda x:-x[1][0]))
                sorted_evs = sorted(evs.items(), key=lambda x:-x[1][0])
                if len(sorted_evs) >= 2:
                    delta = sorted_evs[0][1][0] - sorted_evs[1][1][0]
                    detail_str = f"  delta={delta:.5f}  [{ev_parts}]"

        print(f"  {name:<14}: {mx:>14,}  (Hand={hand_str} vs {col}){detail_str}")
    print(f"  {'OVERALL':<14}: {overall_max:>14,}")
    print("="*50)


if __name__ == "__main__":
    main()