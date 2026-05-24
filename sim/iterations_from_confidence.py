"""
CalcIterations.py

Calculates the minimum Monte Carlo iterations required per strategy cell
to distinguish the best decision from the second-best at a given confidence.

Uses worst-case rules (8D H17 ENHC) as an upper bound — any other rule set
will require fewer iterations. Outputs four CSVs into the Simulator folder:
  Hard_Iterations.csv, Soft_Iterations.csv,
  Pairs_DAS_Iterations.csv, Pairs_NDAS_Iterations.csv

Usage:
    python CalcIterations.py --data-dir ../Data
    python CalcIterations.py --data-dir ../Data --confidence 0.99
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
DECKS      = 8
S17        = False   # H17
ENHC       = True
BJ_PAY     = 1.5
CONFIDENCE = 0.95

DECK_MAP = {1:"oneDeck", 2:"twoDeck", 4:"fourDeck", 6:"sixDeck", 8:"eightDeck"}

# JSON stores upcards as: [0]=Ace, [1]=2, [2]=3, ..., [9]=10
# up_labels order:        idx 0 =2, idx 1 =3, ..., idx 8 =10, idx 9 =A
# Mapping: uc_idx -> json_idx = (uc_idx + 1) % 10
def _json_idx(uc_idx: int) -> int:
    return (uc_idx + 1) % 10


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
        return (1 + 15*(w2**2+l2**2) + 8*(2*w2*w+2*l2*l)
                + 3*(2*w2*(t+t2)+w**2+2*l2*(t+t2)+l**2)
                - (2*w2*l2+2*w*l+(t+t2)**2) - ev**2)
    return 1 + 3*(w**2+l**2) - (2*w*l+t**2) - ev**2


# ---------------------------------------------------------------------------
# Iteration formula  N = z² × (σ₁² + σ₂²) / Δ²
# Only computed for best vs second-best — the only comparison that matters.
# ---------------------------------------------------------------------------

def required_n(var1: float, var2: float, delta: float, z: float) -> int:
    if delta <= 1e-10:
        return 0
    return math.ceil(z**2 * (var1 + var2) / delta**2)


def _worst_n(evs: dict[str, tuple[float, float]], z: float) -> int:
    """Return iterations needed to distinguish best from second-best action."""
    items = sorted(evs.items(), key=lambda x: -x[1][0])
    if len(items) < 2:
        return 0
    _, (e1, v1) = items[0]
    _, (e2, v2) = items[1]
    if not (math.isfinite(e1) and math.isfinite(e2)): return 0
    if not (math.isfinite(v1) and math.isfinite(v2)): return 0
    if v1 < 0 or v2 < 0: return 0
    return required_n(v1, v2, abs(e1 - e2), z)


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
# Build matrices
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
            ji = _json_idx(uc_idx)
            d_by_t = _group_by_total(double_ds[hand_type][ji], two_card_only=True)
            d_entries = d_by_t.get(total, [])

            if d_entries:
                s2 = _group_by_total(stand_ds[hand_type][ji], two_card_only=True).get(total, [])
                h2 = _group_by_total(hit_ds[hand_type][ji],   two_card_only=True).get(total, [])
                evs: dict[str, tuple[float, float]] = {}
                if s2: evs["S"] = _weighted(s2, stand_ev, stand_var)
                if h2: evs["H"] = _weighted(h2, hit_ev,   hit_var)
                evs["D"] = _weighted(d_entries, double_ev, double_var)
            else:
                s_e = _group_by_total(stand_ds[hand_type][ji]).get(total, [])
                h_e = _group_by_total(hit_ds[hand_type][ji]).get(total, [])
                evs = {}
                if s_e: evs["S"] = _weighted(s_e, stand_ev, stand_var)
                if h_e: evs["H"] = _weighted(h_e, hit_ev,   hit_var)

            row.append(_worst_n(evs, z))
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
        pair_rank = pair_val
        ht = "soft" if pair_rank == 1 else "hard"

        for uc_idx in range(10):
            ji = _json_idx(uc_idx)

            def _pair_entries(ds_ht, ji=ji):
                return [e for e in ds_ht[ht][ji]
                        if len(e[0]) == 2
                        and e[0][0]["rank"] == pair_rank
                        and e[0][1]["rank"] == pair_rank]

            s_entries = _pair_entries(stand_ds)
            h_entries = _pair_entries(hit_ds)
            d_entries = _pair_entries(double_ds)

            sp_dict  = split_pairs[ji][pair_rank - 1][1]
            sp_ev_v  = split_ev(sp_dict, das)
            sp_var_v = split_var(sp_dict, das)

            evs: dict[str, tuple[float, float]] = {"P": (sp_ev_v, sp_var_v)}
            if s_entries: evs["S"] = _weighted(s_entries, stand_ev, stand_var)
            if h_entries: evs["H"] = _weighted(h_entries, hit_ev,   hit_var)
            if d_entries: evs["D"] = _weighted(d_entries, double_ev, double_var)

            row.append(_worst_n(evs, z))
        rows.append(row)

    df = pd.DataFrame(rows, index=pair_labels, columns=up_labels)
    df.index.name = "Hand"
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir",   dest="data_dir", default=None)
    parser.add_argument("--out-dir",    dest="out_dir",  default=None)
    parser.add_argument("--confidence", type=float, default=CONFIDENCE)
    args = parser.parse_args()

    def norm_ppf(p: float) -> float:
        a=[0,-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
           1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
        b=[0,-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
           6.680131188771972e+01,-1.328068155288572e+01]
        c=[0,-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
           -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
        d=[0,7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
        p_low, p_high = 0.02425, 1 - 0.02425
        if p < p_low:
            q = math.sqrt(-2*math.log(p))
            return (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6])/((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
        elif p <= p_high:
            q = p-0.5; r = q*q
            return (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q/(((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
        else:
            q = math.sqrt(-2*math.log(1-p))
            return -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6])/((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)

    z = norm_ppf(args.confidence)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir  = args.out_dir  or script_dir
    data_dir = args.data_dir or os.path.normpath(os.path.join(script_dir, "..", "Data"))

    print(f"Worst-case rules : {DECKS}D  {'S17' if S17 else 'H17'}  {'ENHC' if ENHC else 'US'}")
    print(f"Confidence       : {args.confidence*100:.0f}%  (z={z:.3f})")
    print(f"Data dir         : {data_dir}\n")

    stand_ds  = _get_ds(_load(data_dir, "stand.json")["probs"],  DECKS, S17, ENHC)
    hit_ds    = _get_ds(_load(data_dir, "hit.json")["probs"],    DECKS, S17, ENHC)
    double_ds = _get_ds(_load(data_dir, "double.json")["probs"], DECKS, S17, ENHC)
    split_ds  = _get_ds(_load(data_dir, "split.json")["probs"],  DECKS, S17, ENHC)

    tables = [
        ("Hard",        _build_hsd_matrix(stand_ds, hit_ds, double_ds, "hard", range(21, 3,  -1), z)),
        ("Soft",        _build_hsd_matrix(stand_ds, hit_ds, double_ds, "soft", range(21, 12, -1), z)),
        ("Pairs_DAS",   _build_pairs_matrix(stand_ds, hit_ds, double_ds, split_ds["DAS"],  das=True,  z=z)),
        ("Pairs_NDAS",  _build_pairs_matrix(stand_ds, hit_ds, double_ds, split_ds["nDAS"], das=False, z=z)),
    ]

    overall_max = 0
    for name, df in tables:
        path = os.path.join(out_dir, f"{name}_Iterations.csv")
        df.to_csv(path)
        mx = int(df.values.max())
        overall_max = max(overall_max, mx)
        idx = df.stack().idxmax()
        print(f"{name}: max={mx:>10,}  (Hand={idx[0]} vs {idx[1]})  -> {path}")
        print(df.to_string())
        print()

    print(f"Overall max: {overall_max:,}")


if __name__ == "__main__":
    main()