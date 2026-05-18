from __future__ import annotations

import os
import sys
os.environ["PYTHONUNBUFFERED"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
from pathlib import Path

import pandas as pd

from BlackjackSimulator import BlackjackSimulator, DealerSettingsObject

# ---------------------------------------------------------------------------
# Inline iteration calculator (mirrors CalcIterations.py logic)
# ---------------------------------------------------------------------------

def _calc_and_save_iterations(
    folder: Path, data_dir: Path, confidence: float,
    decks: int, s17: bool, enhc: bool, das: bool,
) -> None:
    """Compute required iterations per cell at given confidence and save CSVs."""
    import json, math

    DECKS, S17, ENHC = decks, s17, enhc

    DECK_MAP = {1:"oneDeck",2:"twoDeck",4:"fourDeck",6:"sixDeck",8:"eightDeck"}

    def _norm_ppf(p: float) -> float:
        a=[0,-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
           1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
        b=[0,-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
           6.680131188771972e+01,-1.328068155288572e+01]
        c=[0,-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
           -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
        d=[0,7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
        p_low,p_high=0.02425,1-0.02425
        if p<p_low:
            q=math.sqrt(-2*math.log(p))
            return(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6])/((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
        elif p<=p_high:
            q=p-0.5;r=q*q
            return(((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q/(((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
        else:
            q=math.sqrt(-2*math.log(1-p))
            return-(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6])/((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)

    z = _norm_ppf(confidence)

    def _load_json(name):
        with open(data_dir / name, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_ds(data):
        return data[DECK_MAP[DECKS]]["S17" if S17 else "H17"]["enhc" if ENHC else "us"]

    def _card_total(hand):
        t=aces=0
        for c in hand:
            r=c["rank"] if isinstance(c,dict) else c
            if r==1: t+=11;aces+=1
            else: t+=r
        while t>21 and aces>0: t-=10;aces-=1
        return t

    def _condition(probs: dict, up_card_idx: int) -> dict:
        """
        For US peek rules, upcards A (idx=9) and 10 (idx=8) have unconditional
        win/tie/lose probs that include dealer BJ. Condition on no dealer BJ so
        EV deltas match what the simulator measures (post-peek conditional EVs).
        For ENHC, dealer BJ is a real outcome — no conditioning needed.
        """
        if ENHC:
            return probs  # ENHC: unconditional probs are correct
        if up_card_idx not in (8, 9):  # only A and 10 need conditioning
            return probs
        dbj = probs.get("DBJ", 0.0)
        if dbj <= 0:
            return probs
        scale = 1.0 / (1.0 - dbj) if dbj < 1.0 else 1.0
        return {
            "winProb":  probs["winProb"]  * scale,
            "tieProb":  probs["tieProb"]  * scale,
            "loseProb": probs["loseProb"] * scale,
            "DBJ":      0.0,  # conditioned out
        }

    def _s_ev(s, uc=None):
        s = _condition(s, uc) if uc is not None else s
        return s["winProb"]-s["loseProb"]-s["DBJ"]
    def _s_var(s, uc=None):
        s = _condition(s, uc) if uc is not None else s
        return 1.0-s["tieProb"]-_s_ev(s)**2
    def _h_ev(h, uc=None):
        h = _condition(h, uc) if uc is not None else h
        return h["winProb"]-h["loseProb"]-h["DBJ"]
    def _h_var(h, uc=None):
        h = _condition(h, uc) if uc is not None else h
        return 1.0-h["tieProb"]-_h_ev(h)**2
    def _d_ev(d, uc=None):
        d = _condition(d, uc) if uc is not None else d
        return 2.0*(d["winProb"]-d["loseProb"]-d["DBJ"])
    def _d_var(d, uc=None):
        d = _condition(d, uc) if uc is not None else d
        return 4.0*(1.0-d["tieProb"])-_d_ev(d)**2

    def _sp_ev(sp,das):
        w2=sp["double"]["winProb"];t2=sp["double"]["tieProb"];l2=sp["double"]["loseProb"]
        w=sp["noDouble"]["winProb"];t=sp["noDouble"]["tieProb"]
        l=sp["noDouble"]["loseProb"];d=sp["noDouble"]["DBJ"]
        if das:
            return(4*w2**2+3*2*w2*w+2*(2*w2*(t+t2)+w**2)+(2*w2*l+2*w*(t+t2))
                   -d-(2*l2*w+2*l*(t+t2))-2*(2*l2*(t+t2)+l**2)-3*2*l2*l-4*l2**2)
        return 2*w**2+2*w*t-d-2*l*t-2*l**2

    def _sp_var(sp,das):
        w2=sp["double"]["winProb"];t2=sp["double"]["tieProb"];l2=sp["double"]["loseProb"]
        w=sp["noDouble"]["winProb"];t=sp["noDouble"]["tieProb"];l=sp["noDouble"]["loseProb"]
        ev=_sp_ev(sp,das)
        if das:
            return(1+15*(w2**2+l2**2)+8*(2*w2*w+2*l2*l)+3*(2*w2*(t+t2)+w**2+2*l2*(t+t2)+l**2)
                   -(2*w2*l2+2*w*l+(t+t2)**2)-ev**2)
        return 1+3*(w**2+l**2)-(2*w*l+t**2)-ev**2

    def _weighted(entries, ev_fn, var_fn, uc_idx=None):
        tp=sum(e[1] for e in entries)
        if tp==0: return 0.0,1.0
        w_ev=sum(ev_fn(e[2],uc_idx)*e[1] for e in entries)/tp
        w_var=sum(var_fn(e[2],uc_idx)*e[1] for e in entries)/tp
        w_var+=sum((ev_fn(e[2],uc_idx)-w_ev)**2*e[1] for e in entries)/tp
        return w_ev,w_var

    MIN_CELL_ITERS = 100_000    # floor: always run at least this many iterations
    MAX_CELL_ITERS = 5_000_000  # cap: beyond this the decision margin is negligible

    def _req_n(v1,v2,delta):
        if delta<=1e-10: return MIN_CELL_ITERS
        n = math.ceil(z**2*(v1+v2)/delta**2 * 2)
        return max(MIN_CELL_ITERS, min(n, MAX_CELL_ITERS))

    def _group(ds_upcard, two_card_only=False):
        by_t={}
        for e in ds_upcard:
            if two_card_only and len(e[0])!=2: continue
            t=_card_total(e[0])
            by_t.setdefault(t,[]).append(e)
        return by_t

    def _worst_n(evs_dict, label=""):
        items=sorted(evs_dict.items(),key=lambda x:-x[1][0])
        ns = []
        for i,(c1,(e1,v1)) in enumerate(items):
            for j,(c2,(e2,v2)) in enumerate(items):
                if i >= j: continue
                if not (math.isfinite(e1) and math.isfinite(e2)): continue
                if not (math.isfinite(v1) and math.isfinite(v2)): continue
                if v1 < 0 or v2 < 0: continue
                n = _req_n(v1, v2, abs(e1-e2))
                if n > 1_000_000 and label:
                    print(f"    HIGH N={n:,} for {label}: {c1}(EV={e1:.5f},var={v1:.3f}) vs {c2}(EV={e2:.5f},var={v2:.3f}) delta={abs(e1-e2):.6f}", flush=True)
                ns.append(n)
        return max(ns) if ns else 1

    stand_ds = _get_ds(_load_json("stand.json")["probs"])
    hit_ds   = _get_ds(_load_json("hit.json")["probs"])
    dbl_ds   = _get_ds(_load_json("double.json")["probs"])
    spl_ds   = _get_ds(_load_json("split.json")["probs"])

    up_labels=["2","3","4","5","6","7","8","9","10","A"]

    # JSON stores upcards as: [0]=Ace, [1]=2, [2]=3, ..., [9]=10
    # up_labels order: ["2","3","4","5","6","7","8","9","10","A"]
    # So uc_idx -> json_idx: 0->1, 1->2, ..., 8->9, 9->0
    def _json_idx(uc_idx):
        return (uc_idx + 1) % 10

    def _build_hsd(hand_type, totals):
        rows=[]
        for total in totals:
            row=[]
            for uc_idx in range(10):
                ji = _json_idx(uc_idx)
                d_by_t=_group(dbl_ds[hand_type][ji],two_card_only=True)
                d_entries=d_by_t.get(total,[])
                if d_entries:
                    s2=_group(stand_ds[hand_type][ji],two_card_only=True).get(total,[])
                    h2=_group(hit_ds[hand_type][ji],two_card_only=True).get(total,[])
                    evs={}
                    if s2: evs["S"]=_weighted(s2,_s_ev,_s_var,uc_idx)
                    if h2: evs["H"]=_weighted(h2,_h_ev,_h_var,uc_idx)
                    evs["D"]=_weighted(d_entries,_d_ev,_d_var,uc_idx)
                else:
                    s_e=_group(stand_ds[hand_type][ji]).get(total,[])
                    h_e=_group(hit_ds[hand_type][ji]).get(total,[])
                    evs={}
                    if s_e: evs["S"]=_weighted(s_e,_s_ev,_s_var,uc_idx)
                    if h_e: evs["H"]=_weighted(h_e,_h_ev,_h_var,uc_idx)
                row.append(_worst_n(evs, f"{hand_type}_{total}_vs_{up_labels[uc_idx]}") if len(evs)>=2 else 1)
            rows.append(row)
        df=pd.DataFrame(rows,index=list(totals),columns=up_labels)
        df.index.name="Hand"
        return df

    def _build_pairs(das):
        pair_order=[10,9,8,7,6,5,4,3,2,1]
        pair_labels=["10","9","8","7","6","5","4","3","2","A"]
        das_key="DAS" if das else "nDAS"
        rows=[]
        for pair_val in pair_order:
            pair_rank=pair_val
            ht="soft" if pair_rank==1 else "hard"
            row=[]
            for uc_idx in range(10):
                ji = _json_idx(uc_idx)
                def _pe(ds_ht, ji=ji):
                    return[e for e in ds_ht[ht][ji]
                           if len(e[0])==2 and e[0][0]["rank"]==pair_rank and e[0][1]["rank"]==pair_rank]
                s_e=_pe(stand_ds); h_e=_pe(hit_ds); d_e=_pe(dbl_ds)
                sp=spl_ds[das_key][ji][pair_rank-1][1]
                evs={"P":(_sp_ev(sp,das),_sp_var(sp,das))}
                if s_e: evs["S"]=_weighted(s_e,_s_ev,_s_var,uc_idx)
                if h_e: evs["H"]=_weighted(h_e,_h_ev,_h_var,uc_idx)
                if d_e: evs["D"]=_weighted(d_e,_d_ev,_d_var,uc_idx)
                row.append(_worst_n(evs, f"pair{pair_rank}_vs_{up_labels[uc_idx]}") if len(evs)>=2 else 1)
            rows.append(row)
        df=pd.DataFrame(rows,index=pair_labels,columns=up_labels)
        df.index.name="Hand"
        return df

    deck_str = {1:"1D",2:"2D",4:"4D",6:"6D",8:"8D"}.get(DECKS, f"{DECKS}D")
    rule_str = f"{deck_str} {'S17' if S17 else 'H17'} {'ENHC' if ENHC else 'US'}"
    print(f"Computing required iterations at {confidence*100:.0f}% confidence ({rule_str})...", flush=True)
    for name, df in [
        ("Hard",       _build_hsd("hard", range(21,3,-1))),
        ("Soft",       _build_hsd("soft", range(21,12,-1))),
        ("Pairs_DAS",  _build_pairs(das=True)),
        ("Pairs_NDAS", _build_pairs(das=False)),
    ]:
        out = folder / f"{name}_Iterations.csv"
        df.to_csv(out)
        print(f"  Saved -> {out}  (max={int(df.values.max()):,})", flush=True)


# ---------------------------------------------------------------------------
# Folder resolution
# ---------------------------------------------------------------------------

def _strategy_folder(base_dir: str, decks: int, s17: bool, enhc: bool) -> Path:
    deck_str = "1D" if decks == 1 else ("2D" if decks == 2 else "MD")
    rule_str = "S17" if s17 else "H17"
    peek_str = "ENHC" if enhc else "US"
    return Path(base_dir) / deck_str / rule_str / peek_str


def _load_strategy_csv(folder: Path, name: str, das: bool | None = None) -> pd.DataFrame | None:
    """
    Tries to find a strategy CSV in the folder. Checks naming patterns:
      1. <prefix>_DAS_<name>.csv  or  <prefix>_NDAS_<name>.csv  (DAS-specific)
      2. <prefix>_<name>.csv      e.g. 1D_S17_US_Hard.csv
      3. <name>.csv               e.g. Hard.csv
    where <prefix> is inferred from the folder path (e.g. 1D_S17_US).
    Pairs CSVs have string indices so int cast is skipped.
    """
    parts = folder.parts
    prefix = "_".join(parts[-3:]) if len(parts) >= 3 else ""
    das_str = ("DAS" if das else "NDAS") if das is not None else None

    candidates = []
    if das_str:
        candidates.append(f"{prefix}_{das_str}_{name}.csv")
    candidates += [f"{prefix}_{name}.csv", f"{name}.csv"]

    for candidate in candidates:
        path = folder / candidate
        if path.exists():
            df = pd.read_csv(path, index_col="Hand")
            if name != "Pairs":
                try:
                    df.index = df.index.astype(int)
                except (ValueError, TypeError):
                    pass
            return df
    return None


def _load_iterations_csv(folder: Path, name: str) -> pd.DataFrame:
    """Load a precomputed iterations CSV (e.g. Hard_Iterations.csv).
    Raises FileNotFoundError if not found."""
    path = folder / f"{name}_Iterations.csv"
    if path.exists():
        return pd.read_csv(path, index_col="Hand")
    raise FileNotFoundError(
        f"Iterations CSV not found: {path}\n"
        f"Run with --confidence to generate it first."
    )


def _get_iterations_for_cell(iter_df: pd.DataFrame, total, up_card: int) -> int:
    """Look up the required iterations for one (total, upcard) cell."""
    col = "A" if up_card == 1 else str(up_card)
    key = str(total)
    for idx in iter_df.index:
        if str(idx).strip() == key:
            try:
                return max(1, int(iter_df.loc[idx, col]))
            except (KeyError, ValueError):
                pass
    raise KeyError(f"Cell ({total}, {col}) not found in iterations CSV")


def _get_series(df: pd.DataFrame | None, up_card: int) -> pd.Series | None:
    if df is None:
        return None
    col = "A" if up_card == 1 else str(up_card)
    if col not in df.columns:
        return None
    s = df[col].copy()
    # Map index to int, treating "A" as 1
    def _to_int(v):
        s = str(v).strip()
        return 1 if s == "A" else int(s)
    s.index = s.index.map(_to_int)
    return s


# ---------------------------------------------------------------------------
# Code resolution
# ---------------------------------------------------------------------------

def _resolve_ev_to_code(stand_ev: float, hit_ev: float, double_ev: float) -> str:
    """
    Returns the best strategy code. Double is always DH or DS — never bare D.
      DH = double is best, fallback is hit  (hit EV > stand EV)
      DS = double is best, fallback is stand (stand EV >= hit EV)
      H  = hit is best
      S  = stand is best

    double_ev is on a 2-unit bet — normalized to 1-unit before comparing.
    EVs are already conditional on no dealer BJ (NaN resampling in run()).
    """
    double_ev_normalized = double_ev / 2.0
    if double_ev_normalized >= stand_ev and double_ev_normalized >= hit_ev:
        return "DH" if hit_ev > stand_ev else "DS"
    if hit_ev >= stand_ev:
        return "H"
    return "S"


# ---------------------------------------------------------------------------
# Simulator class
# ---------------------------------------------------------------------------

class Simulator:
    STAND  = 0
    HIT    = 1
    DOUBLE = 2

    def __init__(self, dealer_settings: DealerSettingsObject) -> None:
        self.dealer_settings = dealer_settings
        self.hard_hands = self.get_only_top_compositions(soft=False)
        self.soft_hands = self.get_only_top_compositions(soft=True)

    @classmethod
    def create(cls, dealer_settings: DealerSettingsObject) -> "Simulator":
        return cls(dealer_settings)

    def run(self, iterations, hand, up_card, choice, hard_choices, soft_choices) -> float:
        sim = BlackjackSimulator(self.dealer_settings)
        total_gain = 0.0
        for _ in range(iterations):
            total_gain += sim.start_sim(hand, up_card, choice, hard_choices, soft_choices)
        return total_gain / iterations

    def calc_error(self, iterations: int) -> None:
        sim = BlackjackSimulator(self.dealer_settings)
        actual_stand = 0.453917
        actual_double = -1.700555
        for k in range(4):
            stand_error = double_error = 0.0
            for _ in range(10):
                tg = sum(sim.start_sim([10,10], 10, Simulator.STAND, [], []) for _ in range(iterations * 10**k))
                stand_error += abs(tg / (iterations * 10**k) - actual_stand)
            for _ in range(10):
                tg = sum(sim.start_sim([10,10], 10, Simulator.DOUBLE, [], []) for _ in range(iterations * 10**k))
                double_error += abs(tg / (iterations * 10**k) - actual_double)
            print(f"Iterations: {iterations*10**k}  standError: {stand_error/10}  doubleError: {double_error/10}")

    # ------------------------------------------------------------------
    # run_hand_sim
    # ------------------------------------------------------------------

    def run_hand_sim(self, total_target: int, up_card: int, soft_hands: bool) -> dict:
        all_hands: list[dict] = []
        next_card_probs = [0.0] * 10
        seen_combos: set[str] = set()

        total_cards = self.dealer_settings.decks * 52
        rank_counts = [0] * 11
        for r in range(1, 11):
            rank_counts[r] = self.dealer_settings.decks * 16 if r == 10 else self.dealer_settings.decks * 4

        for player_rank in range(1, 11):
            player_count = rank_counts[player_rank]
            if player_count == 0:
                continue
            prob_player = player_count / total_cards
            counts_after_player = list(rank_counts)
            counts_after_player[player_rank] -= 1
            total_after_player = total_cards - 1
            up_card_count = counts_after_player[up_card]
            if up_card_count == 0:
                continue
            prob_up_card = up_card_count / total_after_player
            counts_after_dealer = list(counts_after_player)
            counts_after_dealer[up_card] -= 1
            total_after_dealer = total_after_player - 1

            def recurse(hand, counts, remaining, hand_probs, min_rank):
                t = self.total(hand)
                is_soft = self.is_soft(hand)
                if not soft_hands and is_soft and total_target > 11:
                    t -= 10
                if t > total_target:
                    return
                if t == total_target and len(hand) > 1:
                    if (soft_hands and is_soft) or (not soft_hands):
                        total_prob = 1.0
                        for p in hand_probs:
                            total_prob *= p
                        key = ",".join(str(r) for r in sorted(hand))
                        if key not in seen_combos:
                            seen_combos.add(key)
                            all_hands.append({"hand": list(hand), "totalProb": total_prob})
                            for nr in range(1, 11):
                                if counts[nr] == 0:
                                    continue
                                next_card_probs[nr - 1] += (counts[nr] / remaining) * total_prob
                    return
                for rank in range(min_rank, 11):
                    if counts[rank] == 0:
                        continue
                    nc = list(counts)
                    nc[rank] -= 1
                    recurse(hand + [rank], nc, remaining - 1,
                            hand_probs + [counts[rank] / remaining], rank)

            recurse([player_rank], counts_after_dealer, total_after_dealer,
                    [prob_player * prob_up_card], 1)

        total = sum(next_card_probs)
        if total > 0:
            next_card_probs = [p / total for p in next_card_probs]
        return {"allHands": all_hands, "nextCardProbs": next_card_probs}

    # ------------------------------------------------------------------
    # calc — unified single-pool runner
    # ------------------------------------------------------------------

    def calc(
        self,
        strategy_folder: str | Path,
        workers: int | None = None,
        modes: list[str] | None = None,
    ) -> dict[str, pd.DataFrame]:
        """
        Run all requested modes in a single pool so workers move directly
        from one table to the next without sitting idle between tables.
        modes: subset of ["hard", "soft", "pairs"]; defaults to all three.
        """
        import multiprocessing
        folder = Path(strategy_folder)
        das = self.dealer_settings.DAS
        modes = modes or ["hard", "soft", "pairs"]

        hard_strat_df = _load_strategy_csv(folder, "Hard")
        soft_strat_df = _load_strategy_csv(folder, "Soft")
        das_pairs_df  = _load_strategy_csv(folder, "Pairs", das=das)

        all_tasks: list[dict] = []

        # Build tasks in priority order: pairs and soft first (most expensive),
        # hard last. imap_unordered means workers pick up the next task as soon
        # as they finish, so submitting expensive tasks first keeps all workers busy.
        if "pairs" in modes:
            das_label = "DAS" if das else "NDAS"
            iter_df = _load_iterations_csv(folder, f"Pairs_{das_label}")
            for uc in range(1, 11):
                all_tasks.append({
                    "dealer_settings": self.dealer_settings,
                    "up_card": uc,
                    "iter_df": iter_df,
                    # Use hard/soft strategy CSVs for continuation play after splits
                    "hard_series": _get_series(hard_strat_df, uc),
                    "soft_series": _get_series(soft_strat_df, uc),
                    "mode": "pairs",
                })

        if "soft" in modes:
            iter_df = _load_iterations_csv(folder, "Soft")
            for uc in range(1, 11):
                all_tasks.append({
                    "dealer_settings": self.dealer_settings,
                    "up_card": uc,
                    "hands_for_upcard": self.soft_hands[uc - 1],
                    "iter_df": iter_df,
                    "hard_series": _get_series(hard_strat_df, uc),
                    "soft_series": _get_series(soft_strat_df, uc),
                    "mode": "soft",
                })

        if "hard" in modes:
            iter_df = _load_iterations_csv(folder, "Hard")
            for uc in range(1, 11):
                all_tasks.append({
                    "dealer_settings": self.dealer_settings,
                    "up_card": uc,
                    "hands_for_upcard": self.hard_hands[uc - 1],
                    "iter_df": iter_df,
                    "hard_series": _get_series(hard_strat_df, uc),
                    "soft_series": _get_series(soft_strat_df, uc),
                    "mode": "hard",
                })

        mw = _resolve_workers(workers)
        print(f"[Sim] {mw} workers, {len(all_tasks)} tasks across {modes}", flush=True)

        hard_results, soft_results, pairs_results = [], [], []
        with multiprocessing.Pool(processes=mw) as pool:
            for result in pool.imap_unordered(_worker, all_tasks):
                mode = result["mode"]
                if mode == "hard":   hard_results.append(result)
                elif mode == "soft": soft_results.append(result)
                else:                pairs_results.append(result)

        out_dfs: dict[str, pd.DataFrame] = {}

        if hard_results:
            df, ev_lookup = _build_matrix(hard_results, totals=list(range(21, 3, -1)))
            df.attrs["ev_lookup"] = ev_lookup
            out = folder / "Hard_SIM.csv"
            df.to_csv(out)
            print(f"\nSaved -> {out}\n")
            print(df.to_string())
            out_dfs["Hard"] = df

        if soft_results:
            df, ev_lookup = _build_matrix(soft_results, totals=list(range(21, 12, -1)))
            df.attrs["ev_lookup"] = ev_lookup
            out = folder / "Soft_SIM.csv"
            df.to_csv(out)
            print(f"\nSaved -> {out}\n")
            print(df.to_string())
            out_dfs["Soft"] = df

        if pairs_results:
            up_card_order = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
            col_labels    = [str(u) if u != 1 else "A" for u in up_card_order]
            pair_order    = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
            pair_labels   = ["10", "9", "8", "7", "6", "5", "4", "3", "2", "A"]
            result_map    = {r["up_card"]: r["pair_results"] for r in pairs_results}
            evs_map       = {r["up_card"]: r.get("pair_evs", {}) for r in pairs_results}
            rows = [[result_map[uc].get(pv, "H") for uc in up_card_order] for pv in pair_order]
            df = pd.DataFrame(rows, index=pair_labels, columns=col_labels)
            df.index.name = "Hand"
            ev_lookup = {
                (pl, col): evs_map.get(uc, {}).get(pv, {})
                for pv, pl in zip(pair_order, pair_labels)
                for uc, col in zip(up_card_order, col_labels)
            }
            df.attrs["ev_lookup"] = ev_lookup
            das_label = "DAS" if das else "NDAS"
            out = folder / f"Pairs_{das_label}_SIM.csv"
            df.to_csv(out)
            print(f"\nSaved -> {out}\n")
            print(df.to_string())
            out_dfs["Pairs"] = df

        return out_dfs

    def calc_hard(self, strategy_folder: str | Path, workers: int | None = None, **_) -> pd.DataFrame:
        return self.calc(strategy_folder, workers=workers, modes=["hard"])["Hard"]

    def calc_soft(self, strategy_folder: str | Path, workers: int | None = None, **_) -> pd.DataFrame:
        return self.calc(strategy_folder, workers=workers, modes=["soft"])["Soft"]

    def calc_pairs(self, strategy_folder: str | Path, workers: int | None = None, **_) -> pd.DataFrame:
        return self.calc(strategy_folder, workers=workers, modes=["pairs"])["Pairs"]
    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------

    def order_most_probable_hands(self, total_target, up_card, soft):
        all_hands = self.run_hand_sim(total_target, up_card, soft)["allHands"]
        if not all_hands:
            return []
        tp = sum(h["totalProb"] for h in all_hands)
        result = [{"hand": h["hand"], "normalizedProb": h["totalProb"] / tp if tp > 0 else 0.0} for h in all_hands]
        result.sort(key=lambda x: x["normalizedProb"], reverse=True)
        return result

    def get_only_top_compositions(self, soft):
        """Return ALL compositions per total/upcard, normalised probabilities summing to 1."""
        totals = list(range(12, 22)) if soft else list(range(4, 22))
        result = []
        for uc in range(1, 11):
            upcard_row = []
            for total in totals:
                comps = self.order_most_probable_hands(total, uc, soft)
                upcard_row.append(comps)  # already normalised in order_most_probable_hands
            result.append(upcard_row)
        return result

    def is_soft(self, cards):
        total = num_aces = 0
        for card in cards:
            total += 11 if card == 1 else card
            if card == 1:
                num_aces += 1
        while total > 21 and num_aces > 0:
            total -= 10
            num_aces -= 1
        return num_aces > 0

    def total(self, cards):
        t = num_aces = 0
        for card in cards:
            if card == 1:
                t += 11
                num_aces += 1
            else:
                t += card
        while t > 21 and num_aces > 0:
            t -= 10
            num_aces -= 1
        return t

    def shuffle(self, array):
        result = list(array)
        for i in range(len(result) - 1, 0, -1):
            j = random.randint(0, i)
            result[i], result[j] = result[j], result[i]
        return result


# ---------------------------------------------------------------------------
# Pool helpers
# ---------------------------------------------------------------------------

def _resolve_workers(workers):
    import multiprocessing
    cpu = multiprocessing.cpu_count() or 1
    mw = min(workers if workers is not None else max(1, cpu - 4), 20)
    print(f"Detected {cpu} logical CPUs. Running with {mw} parallel workers.", flush=True)
    print("Use --workers N to adjust if your computer becomes unresponsive.", flush=True)
    return mw


def _build_matrix(results: list[dict], totals: list[int]) -> tuple[pd.DataFrame, dict]:
    """Returns (strategy_df, ev_dict) where ev_dict[(total, col)] = {S, H, D} EVs."""
    up_card_order = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
    col_labels = [str(u) if u != 1 else "A" for u in up_card_order]
    result_map = {r["up_card"]: r["totals"] for r in results}
    ev_map = {r["up_card"]: r.get("evs", {}) for r in results}
    rows = [[result_map[uc].get(t, "H") for uc in up_card_order] for t in totals]
    df = pd.DataFrame(rows, index=totals, columns=col_labels)
    df.index.name = "Hand"
    # Build flat ev lookup: (str(total), col_label) -> evs dict
    ev_lookup: dict[tuple, dict] = {}
    for uc, col in zip(up_card_order, col_labels):
        for t in totals:
            ev_lookup[(str(t), col)] = ev_map.get(uc, {}).get(t, {})
    return df, ev_lookup


# ---------------------------------------------------------------------------
# Unified pool worker
# ---------------------------------------------------------------------------

def _worker(task: dict) -> dict:
    dealer_settings: DealerSettingsObject = task["dealer_settings"]
    up_card: int       = task["up_card"]
    iterations: int    = task.get("iterations", 10_000)
    hard_series        = task.get("hard_series")
    soft_series        = task.get("soft_series")
    mode: str          = task["mode"]

    STAND  = 0
    HIT    = 1
    DOUBLE = 2

    iter_df = task.get("iter_df")  # precomputed iterations CSV or None

    # Re-cast index to int inside the worker after unpickling, since
    # multiprocessing on Windows can lose the int dtype on Series index.
    if hard_series is not None:
        hard_series = hard_series.copy()
        hard_series.index = hard_series.index.astype(int)
    if soft_series is not None:
        soft_series = soft_series.copy()
        soft_series.index = soft_series.index.astype(int)

    hard_choices = hard_series if hard_series is not None else [-1] * 18
    soft_choices = soft_series if soft_series is not None else [-1] * 10

    def _run_n(hand: list[int], choice: int, n: int) -> float:
        """Run exactly n non-BJ iterations."""
        import math
        sim = BlackjackSimulator(dealer_settings)
        tg = 0.0
        count = 0
        attempts = 0
        max_attempts = n * 10
        while count < n and attempts < max_attempts:
            result = sim.start_sim(hand, up_card, choice, hard_choices, soft_choices)
            attempts += 1
            if math.isnan(result):
                continue
            tg += result
            count += 1
        return tg / count if count > 0 else 0.0

    def run(hand: list[int], choice: int) -> float:
        return _run_n(hand, choice, iterations)

    up_label = "A" if up_card == 1 else str(up_card)
    print(f"[{mode}|upCard={up_label}] Starting", flush=True)

    # ── Pairs ────────────────────────────────────────────────────────────
    if mode == "pairs":
        pair_results: dict[int, str] = {}
        pair_evs: dict[int, dict] = {}

        # For split EV: simulate a single card drawn to one split hand,
        # play it optimally using the perfect strategy continuation choices,
        # then double that EV (symmetric hands). This avoids the issue of
        # start_sim SPLIT advancing through both hands with broken choices.
        def split_hand_ev(pair_val: int, n: int) -> float:
            """Simulate split EV conditional on no dealer BJ (resample on NaN)."""
            import math
            sim = BlackjackSimulator(dealer_settings)
            tg = 0.0
            count = 0
            attempts = 0
            max_attempts = n * 10
            while count < n and attempts < max_attempts:
                result = sim.start_sim(
                    [pair_val, pair_val], up_card,
                    BlackjackSimulator.SPLIT,
                    hard_choices, soft_choices
                )
                attempts += 1
                if math.isnan(result):
                    continue
                tg += result
                count += 1
            return tg / count if count > 0 else 0.0

        for pair_val in range(1, 11):
            hand = [pair_val, pair_val]
            pair_label = "A" if pair_val == 1 else str(pair_val)
            cell_iters = _get_iterations_for_cell(iter_df, pair_label, up_card)
            stand_ev  = _run_n(hand, STAND,  cell_iters)
            hit_ev    = _run_n(hand, HIT,    cell_iters)
            # 5,5 should never be split (treated as hard 10) — double is valid
            double_ev = _run_n(hand, DOUBLE, cell_iters)
            # best_no_split_ev computed after double normalization below

            # Only consider split if the hand can actually be split
            split_ev = split_hand_ev(pair_val, cell_iters)
            # double_ev is on 2-unit bet; normalize to 1-unit for fair comparison
            double_ev_norm = double_ev / 2.0
            best_no_split_ev = max(stand_ev, hit_ev, double_ev_norm)
            code = "P" if split_ev > best_no_split_ev else _resolve_ev_to_code(stand_ev, hit_ev, double_ev)

            pl = "A" if pair_val == 1 else str(pair_val)
            print(f"[pairs|upCard={up_label}] {pl},{pl}: {code}  "
                  f"(S={stand_ev:.4f} H={hit_ev:.4f} D={double_ev:.4f} P={split_ev:.4f})", flush=True)
            pair_results[pair_val] = code
            pair_evs[pair_val] = {"S": stand_ev, "H": hit_ev, "D": double_ev_norm, "P": split_ev}
        print(f"[pairs|upCard={up_label}] Done", flush=True)
        return {"mode": mode, "up_card": up_card, "pair_results": pair_results, "pair_evs": pair_evs}

    # ── Hard / Soft ───────────────────────────────────────────────────────
    hands_for_upcard: list = task["hands_for_upcard"]
    is_soft = (mode == "soft")
    # Build from HIGH to LOW: when computing total N, all totals N+1..21
    # are already in hard_choices/soft_choices, giving correct hit continuation.
    # e.g. computing 16: hitting gives 17-26; strategy for 17+ already known.
    totals_range = range(21, 12, -1) if is_soft else range(21, 3, -1)
    totals_out: dict[int, str] = {}
    evs_out: dict[int, dict] = {}

    for hand_total in totals_range:
        idx = (hand_total - 12) if is_soft else (hand_total - 4)
        comps = hands_for_upcard[idx]

        # Look up required iterations for this (total, upcard) cell.
        # Falls back to the fixed `iterations` argument if no CSV loaded.
        cell_iters = _get_iterations_for_cell(iter_df, hand_total, up_card)

        # Probability-weighted allocation across compositions:
        # each comp gets max(1, round(prob * cell_iters)) iterations.
        stand_ev = hit_ev = double_ev = 0.0
        for comp in comps:
            p = comp["normalizedProb"]
            comp_iters = max(1, round(p * cell_iters))
            stand_ev  += _run_n(comp["hand"], STAND,  comp_iters) * p
            hit_ev    += _run_n(comp["hand"], HIT,    comp_iters) * p
            double_ev += _run_n(comp["hand"], DOUBLE, comp_iters) * p

        code = _resolve_ev_to_code(stand_ev, hit_ev, double_ev)

        # Update incremental list choices if no perfect strategy provided
        if isinstance(hard_choices, list) and not is_soft:
            int_choice = STAND if "S" in code else (HIT if "H" in code else DOUBLE)
            hard_choices[hand_total - 4] = int_choice
        if isinstance(soft_choices, list) and is_soft:
            int_choice = STAND if "S" in code else (HIT if "H" in code else DOUBLE)
            soft_choices[hand_total - 12] = int_choice

        totals_out[hand_total] = code
        evs_out[hand_total] = {"S": stand_ev, "H": hit_ev, "D": double_ev / 2.0}
        print(f"[{mode}|upCard={up_label}] {hand_total}: {code}  "
              f"(S={stand_ev:.4f} H={hit_ev:.4f} D={double_ev / 2.0:.4f})", flush=True)

    print(f"[{mode}|upCard={up_label}] Done", flush=True)
    return {"mode": mode, "up_card": up_card, "totals": totals_out, "evs": evs_out}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Run blackjack strategy simulation.")
    parser.add_argument("--decks",        type=int,   default=1)
    parser.add_argument("--s17",          action="store_true", default=True)
    parser.add_argument("--h17",          dest="s17", action="store_false")
    parser.add_argument("--enhc",         action="store_true", default=False)
    parser.add_argument("--das",          action="store_true", default=True)
    parser.add_argument("--ndas",         dest="das", action="store_false")
    parser.add_argument("--bj-pay",       type=float, default=1.5)
    parser.add_argument("--draw-aces",    action="store_true", default=False)
    parser.add_argument("--confidence",   type=float, default=0.95,
                        help="Confidence level for iteration calculation e.g. 0.95 or 0.99")
    parser.add_argument("--data-dir",     dest="data_dir", default=None,
                        help="Path to JSON data directory for iteration calc (default: ../data)")
    parser.add_argument("--workers",      type=int,   default=None)
    parser.add_argument("--mode",         choices=["hard", "soft", "pairs", "all"], default="all")
    parser.add_argument("--matrices-dir", dest="matrices_dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "VerifiedStrategyMatrices"))
    args = parser.parse_args()

    dealer_settings = DealerSettingsObject(
        decks=args.decks, S17=args.s17, ENHC=args.enhc,
        DAS=args.das, BJPay=args.bj_pay, drawAces=args.draw_aces,
    )

    folder = _strategy_folder(args.matrices_dir, args.decks, args.s17, args.enhc)
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    data_dir = Path(args.data_dir) if args.data_dir else (script_dir / ".." / "data").resolve()

    print(f"Settings : {args.decks}D  {'S17' if args.s17 else 'H17'}  {'ENHC' if args.enhc else 'US'}  {'DAS' if args.das else 'nDAS'}  BJ={args.bj_pay}x")
    print(f"Folder   : {folder}")
    print(f"Mode     : {args.mode}  |  Confidence: {args.confidence*100:.0f}%")

    # Step 1: compute and save iteration CSVs
    _calc_and_save_iterations(
        folder, data_dir, args.confidence,
        decks=args.decks, s17=args.s17, enhc=args.enhc, das=args.das,
    )

    # Step 2: build hand compositions
    print("\nBuilding hand compositions...")
    sim = Simulator.create(dealer_settings)
    print("Done. Starting simulation...\n")

    mode_map = {
        "all":   ["hard", "soft", "pairs"],
        "hard":  ["hard"],
        "soft":  ["soft"],
        "pairs": ["pairs"],
    }
    results_dfs = sim.calc(folder, workers=args.workers, modes=mode_map[args.mode])

    # ── Accuracy report ──────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("ACCURACY REPORT")
    print("=" * 50)
    def _sim_key(hand, is_pairs: bool) -> str:
        """Normalise a SIM df index value to match the verified CSV index."""
        s = str(hand).strip()
        if is_pairs:
            return s  # already plain e.g. "10", "9", "A"
        return s  # hard/soft: already int-like string e.g. "16"

    total_wrong = 0
    for table_name, sim_df in results_dfs.items():
        verified_df = _load_strategy_csv(folder, table_name, das=args.das)
        if verified_df is None:
            print(f"{table_name}: no verified CSV found at {folder}, skipping")
            continue

        is_pairs = (table_name == "Pairs")
        # Build lookup: normalised key -> verified index value
        v_lookup = {str(i).strip(): i for i in verified_df.index}

        wrong: list[str] = []
        for hand in sim_df.index:
            key = _sim_key(hand, is_pairs)
            if key not in v_lookup:
                continue
            v_hand = v_lookup[key]
            for col in sim_df.columns:
                if col not in verified_df.columns:
                    continue
                sim_val      = str(sim_df.loc[hand, col]).strip().upper()
                verified_val = str(verified_df.loc[v_hand, col]).strip().upper()
                if sim_val != verified_val:
                    ev_note = ""
                    ev_lookup = sim_df.attrs.get("ev_lookup", {})
                    evs = ev_lookup.get((key, col), {})
                    if evs:
                        got_ev   = evs.get(sim_val[0], evs.get("P", None))  # first char S/H/D/P
                        want_ev  = evs.get(verified_val[0], None)
                        if got_ev is not None and want_ev is not None:
                            diff = got_ev - want_ev
                            ev_note = f"  (margin: {diff:.4f})"
                    wrong.append(f"  {table_name} {key} vs {col}: got={sim_val}  expected={verified_val}{ev_note}")

        total_wrong += len(wrong)
        status = "✓ Perfect" if not wrong else f"✗ {len(wrong)} incorrect"
        print(f"{table_name}: {status}")
        for w in wrong:
            print(w)

    print("-" * 50)
    print(f"Total incorrect decisions: {total_wrong}")
    print("=" * 50)