# Run with: python blackjack_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--confidence N] [--workers N] [--iterations N]

from __future__ import annotations
import os
import sys
parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, parent)
from blackjack import BlackjackSimulator, DealerSettingsObject
os.environ["PYTHONUNBUFFERED"] = "1"
import random
from pathlib import Path
import pandas as pd



MIN_CELL_ITERS = 1
MAX_CELL_ITERS = 1_000_000
MULTIPLIER = 1



def calc_and_save_iterations(
  folder: Path, data_dir: Path, confidence: float,
  decks: int, s17: bool, enhc: bool, das: bool,
  out_folder: Path | None = None, prefix_base: str = "", prefix_das: str = "",
  iterations_override: int | None = None,
) -> None:
  """Compute required iterations per cell at given confidence and save CSVs."""
  import json, math

  DECKS, S17, ENHC = decks, s17, enhc
  if out_folder is None:
    out_folder = folder
  out_folder = Path(out_folder)
  out_folder.mkdir(parents=True, exist_ok=True)

  if iterations_override is not None:
    up_labels = ["2","3","4","5","6","7","8","9","10","A"]
    pair_order = [10,9,8,7,6,5,4,3,2,1]
    pair_labels= ["10","9","8","7","6","5","4","3","2","A"]
    das_label = "DAS" if das else "NDAS"
    print(f"Using fixed {iterations_override:,} iterations per cell.", flush=True)
    for name, index, labels in [
      ("Hard", list(range(21,3,-1)), [str(t) for t in range(21,3,-1)]),
      ("Soft", list(range(21,12,-1)), [str(t) for t in range(21,12,-1)]),
      (f"Pairs_{das_label}", pair_order, pair_labels),
    ]:
      df = pd.DataFrame(
        [[iterations_override]*10 for _ in index],
        index=labels, columns=up_labels
      )
      df.index.name = "Hand"
      prefix = prefix_das if "Pairs" in name else prefix_base
      clean = name.replace("_DAS","").replace("_NDAS","")
      out_folder.mkdir(parents=True, exist_ok=True)
      df.to_csv(out_folder / f"{prefix}_{clean}_Iterations.csv")
      print(f" Saved -> {out_folder / f'{prefix}_{clean}_Iterations.csv'}", flush=True)
    return

  DECK_MAP = {1:"oneDeck",2:"twoDeck",4:"fourDeck",6:"sixDeck",8:"eightDeck"}

  def norm_ppf(p: float) -> float:
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

  z = norm_ppf(confidence)

  def load_json(name):
    with open(data_dir / name, "r", encoding="utf-8") as f:
      return json.load(f)

  def get_ds(data):
    return data[DECK_MAP[DECKS]]["S17" if S17 else "H17"]["enhc" if ENHC else "us"]

  def card_total(hand):
    total=aces=0
    for card in hand:
      rank=card["rank"] if isinstance(card,dict) else card
      if rank==1: total+=11;aces+=1
      else: total+=rank
    while total>21 and aces>0: total-=10;aces-=1
    return total

  def condition(probs: dict, up_card_idx: int) -> dict:
    if ENHC:
      return probs
    if up_card_idx not in (8, 9):
      return probs
    dbj = probs.get("DBJ", 0.0)
    if dbj <= 0:
      return probs
    scale = 1.0 / (1.0 - dbj) if dbj < 1.0 else 1.0
    return {
      "winProb": probs["winProb"] * scale,
      "tieProb": probs["tieProb"] * scale,
      "loseProb": probs["loseProb"] * scale,
      "DBJ": 0.0,
    }

  def s_ev(s, upcard=None):
    s = condition(s, upcard) if upcard is not None else s
    return s["winProb"]-s["loseProb"]-s["DBJ"]

  def s_var(s, upcard=None):
    s = condition(s, upcard) if upcard is not None else s
    return 1.0-s["tieProb"]-s_ev(s)**2

  def h_ev(h, upcard=None):
    h = condition(h, upcard) if upcard is not None else h
    return h["winProb"]-h["loseProb"]-h["DBJ"]

  def h_var(h, upcard=None):
    h = condition(h, upcard) if upcard is not None else h
    return 1.0-h["tieProb"]-h_ev(h)**2

  def d_ev(d, upcard=None):
    d = condition(d, upcard) if upcard is not None else d
    return 2.0*(d["winProb"]-d["loseProb"]-d["DBJ"])

  def d_var(d, upcard=None):
    d = condition(d, upcard) if upcard is not None else d
    return 4.0*(1.0-d["tieProb"])-d_ev(d)**2

  def sp_ev(sp,das):
    win_dbl=sp["double"]["winProb"];tie_dbl=sp["double"]["tieProb"];lose_dbl=sp["double"]["loseProb"]
    win=sp["noDouble"]["winProb"];tie=sp["noDouble"]["tieProb"]
    lose=sp["noDouble"]["loseProb"];dbj=sp["noDouble"]["DBJ"]
    if das:
      return(4*win_dbl**2+3*2*win_dbl*win+2*(2*win_dbl*(tie+tie_dbl)+win**2)+(2*win_dbl*lose+2*win*(tie+tie_dbl))
           -dbj-(2*lose_dbl*win+2*lose*(tie+tie_dbl))-2*(2*lose_dbl*(tie+tie_dbl)+lose**2)-3*2*lose_dbl*lose-4*lose_dbl**2)
    return 2*win**2+2*win*tie-dbj-2*lose*tie-2*lose**2

  def sp_var(sp,das):
    win_dbl=sp["double"]["winProb"];tie_dbl=sp["double"]["tieProb"];lose_dbl=sp["double"]["loseProb"]
    win=sp["noDouble"]["winProb"];tie=sp["noDouble"]["tieProb"];lose=sp["noDouble"]["loseProb"]
    ev=sp_ev(sp,das)
    if das:
      return(1+15*(win_dbl**2+lose_dbl**2)+8*(2*win_dbl*win+2*lose_dbl*lose)+3*(2*win_dbl*(tie+tie_dbl)+win**2+2*lose_dbl*(tie+tie_dbl)+lose**2)
           -(2*win_dbl*lose_dbl+2*win*lose+(tie+tie_dbl)**2)-ev**2)
    return 1+3*(win**2+lose**2)-(2*win*lose+tie**2)-ev**2

  def weighted(entries, ev_fn, var_fn, upcard_index=None):
    total_prob=sum(e[1] for e in entries)
    if total_prob==0: return 0.0,1.0
    weighted_ev=sum(ev_fn(e[2],upcard_index)*e[1] for e in entries)/total_prob
    weighted_var=sum(var_fn(e[2],upcard_index)*e[1] for e in entries)/total_prob
    weighted_var+=sum((ev_fn(e[2],upcard_index)-weighted_ev)**2*e[1] for e in entries)/total_prob
    return weighted_ev,weighted_var

  def req_n(variance_1,variance_2,delta):
    if delta<=1e-10: return MIN_CELL_ITERS
    n = math.ceil(z**2*(variance_1+variance_2)/delta**2 * 2)
    return max(MIN_CELL_ITERS, min(n, MAX_CELL_ITERS))

  def group(ds_upcard, two_card_only=False):
    by_t={}
    for e in ds_upcard:
      if two_card_only and len(e[0])!=2: continue
      t=card_total(e[0])
      by_t.setdefault(t,[]).append(e)
    return by_t

  def worst_n(evs_dict, label=""):
    items = sorted(evs_dict.items(), key=lambda x: -x[1][0])
    if len(items) < 2:
      return 1
    (c1, (e1, variance_1)) = items[0]
    (c2, (e2, variance_2)) = items[1]
    if not (math.isfinite(e1) and math.isfinite(e2)): return MIN_CELL_ITERS
    if not (math.isfinite(variance_1) and math.isfinite(variance_2)): return MIN_CELL_ITERS
    if variance_1 < 0 or variance_2 < 0: return MIN_CELL_ITERS
    n = req_n(variance_1, variance_2, abs(e1 - e2))
    if n > 1_000_000 and label:
      print(f" HIGH N={n:,} for {label}: {c1}(EV={e1:.5f},var={variance_1:.3f}) vs {c2}(EV={e2:.5f},var={variance_2:.3f}) delta={abs(e1-e2):.6f}", flush=True)
    return n

  stand_ds = get_ds(load_json("stand.json")["probs"])
  hit_ds = get_ds(load_json("hit.json")["probs"])
  dbl_ds = get_ds(load_json("double.json")["probs"])
  spl_ds = get_ds(load_json("split.json")["probs"])

  up_labels=["2","3","4","5","6","7","8","9","10","A"]

  def json_idx(upcard_index):
    return (upcard_index + 1) % 10  # up_labels=[2..A]; JSON stores ace at index 0

  def build_hsd(hand_type, totals):
    rows=[]
    for total in totals:
      row=[]
      for upcard_index in range(10):
        json_index = json_idx(upcard_index)
        double_by_total=group(dbl_ds[hand_type][json_index],two_card_only=True)
        d_entries=double_by_total.get(total,[])
        if d_entries:
          s2=group(stand_ds[hand_type][json_index],two_card_only=True).get(total,[])
          h2=group(hit_ds[hand_type][json_index],two_card_only=True).get(total,[])
          evs={}
          if s2: evs["S"]=weighted(s2,s_ev,s_var,upcard_index)
          if h2: evs["H"]=weighted(h2,h_ev,h_var,upcard_index)
          evs["D"]=weighted(d_entries,d_ev,d_var,upcard_index)
        else:
          stand_entries=group(stand_ds[hand_type][json_index]).get(total,[])
          hit_entries=group(hit_ds[hand_type][json_index]).get(total,[])
          evs={}
          if stand_entries: evs["S"]=weighted(stand_entries,s_ev,s_var,upcard_index)
          if hit_entries: evs["H"]=weighted(hit_entries,h_ev,h_var,upcard_index)
        row.append(worst_n(evs, f"{hand_type}_{total}_vs_{up_labels[upcard_index]}") if len(evs)>=2 else 1)
      rows.append(row)
    df=pd.DataFrame(rows,index=list(totals),columns=up_labels)
    df.index.name="Hand"
    return df

  def build_pairs(das):
    pair_order=[10,9,8,7,6,5,4,3,2,1]
    pair_labels=["10","9","8","7","6","5","4","3","2","A"]
    das_key="DAS" if das else "nDAS"
    rows=[]
    for pair_val in pair_order:
      pair_rank=pair_val
      ht="soft" if pair_rank==1 else "hard"
      row=[]
      for upcard_index in range(10):
        json_index = json_idx(upcard_index)

        def pe(ds_ht, json_index=json_index):
          def rank(c): return c["rank"] if isinstance(c, dict) else c
          return[e for e in ds_ht[ht][json_index]
               if len(e[0])==2 and rank(e[0][0])==pair_rank and rank(e[0][1])==pair_rank]
        stand_entries=pe(stand_ds); hit_entries=pe(hit_ds); d_e=pe(dbl_ds)
        sp=spl_ds[das_key][json_index][pair_rank-1][1]
        evs={"P":(sp_ev(sp,das),sp_var(sp,das))}
        if stand_entries: evs["S"]=weighted(stand_entries,s_ev,s_var,upcard_index)
        if hit_entries: evs["H"]=weighted(hit_entries,h_ev,h_var,upcard_index)
        if d_e: evs["D"]=weighted(d_e,d_ev,d_var,upcard_index)
        row.append(worst_n(evs, f"pair{pair_rank}_vs_{up_labels[upcard_index]}") if len(evs)>=2 else 1)
      rows.append(row)
    df=pd.DataFrame(rows,index=pair_labels,columns=up_labels)
    df.index.name="Hand"
    return df

  deck_str = {1:"1D",2:"2D",4:"4D",6:"6D",8:"8D"}.get(DECKS, f"{DECKS}D")
  rule_str = f"{deck_str} {'S17' if S17 else 'H17'} {'ENHC' if ENHC else 'US'}"
  print(f"Computing required iterations at {confidence*100:.0f}% confidence ({rule_str})...", flush=True)
  for name, df in [
    ("Hard", build_hsd("hard", range(21,3,-1))),
    ("Soft", build_hsd("soft", range(21,12,-1))),
    ("Pairs_DAS", build_pairs(das=True)),
    ("Pairs_NDAS", build_pairs(das=False)),
  ]:
    prefix = prefix_das if "Pairs" in name else prefix_base
    clean = name.replace("_DAS", "").replace("_NDAS", "")
    out = out_folder / f"{prefix}_{clean}_Iterations.csv"
    df.to_csv(out)
    print(f" Saved -> {out} (max={int(df.values.max()):,})", flush=True)



def strategy_folder(base_dir: str, decks: int, s17: bool, enhc: bool) -> Path:
  deck_str = "1D" if decks == 1 else ("2D" if decks == 2 else "MD")
  rule_str = "S17" if s17 else "H17"
  peek_str = "ENHC" if enhc else "US"
  return Path(base_dir) / deck_str / rule_str / peek_str



def output_folder(base_dir: str) -> Path:
  from datetime import datetime
  now = datetime.now()
  stamp = now.strftime(f"SIM_{now.month}_{now.day}_{now.year}_%H-%M")
  return Path(base_dir) / "outputs" / "outputs_sim" / stamp



def rule_prefix(decks: int, s17: bool, enhc: bool, das: bool | None = None) -> str:
  deck_str = "1D" if decks == 1 else ("2D" if decks == 2 else "MD")
  rule_str = "S17" if s17 else "H17"
  peek_str = "ENHC" if enhc else "US"
  if das is None:
    return f"{deck_str}_{rule_str}_{peek_str}"
  return f"{deck_str}_{rule_str}_{peek_str}_{'DAS' if das else 'NDAS'}"



def load_strategy_csv(folder: Path, name: str, das: bool | None = None) -> pd.DataFrame | None:
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



def make_flat_iterations_df(n: int, name: str) -> pd.DataFrame:
  up_labels = ["2","3","4","5","6","7","8","9","10","A"]
  pair_labels = ["10","9","8","7","6","5","4","3","2","A"]
  if "Pairs" in name:
    index = pair_labels
  elif "Soft" in name:
    index = [str(t) for t in range(21, 12, -1)]
  else:
    index = [str(t) for t in range(21, 3, -1)]
  df = pd.DataFrame([[n]*10 for _ in index], index=index, columns=up_labels)
  df.index.name = "Hand"
  return df



def load_iterations_csv(folder: Path, name: str, prefix: str = "",
             iterations_override: int | None = None) -> pd.DataFrame:
  if iterations_override is not None:
    return make_flat_iterations_df(iterations_override, name)
  clean = name.replace("_DAS", "").replace("_NDAS", "")
  candidates = []
  if prefix:
    candidates.append(folder / f"{prefix}_{clean}_Iterations.csv")
  candidates.append(folder / f"{name}_Iterations.csv")
  candidates.append(folder / f"{clean}_Iterations.csv")
  for path in candidates:
    if path.exists():
      return pd.read_csv(path, index_col="Hand")
  raise FileNotFoundError(
    f"Iterations CSV not found in {folder}\n"
    f"Run with --confidence to generate it first."
  )



def get_iterations_for_cell(iter_df: pd.DataFrame, total, up_card: int) -> int:
  col = "A" if up_card == 1 else str(up_card)
  key = str(total)
  for index in iter_df.index:
    if str(index).strip() == key:
      try:
        return max(1, int(iter_df.loc[index, col]))
      except (KeyError, ValueError):
        pass
  raise KeyError(f"Cell ({total}, {col}) not found in iterations CSV")






def resolve_ev_to_code(stand_ev: float, hit_ev: float, double_ev: float) -> str:
  double_ev_normalized = double_ev / 2.0
  if double_ev_normalized >= stand_ev and double_ev_normalized >= hit_ev:
    return "DH" if hit_ev > stand_ev else "DS"
  if hit_ev >= stand_ev:
    return "H"
  return "S"



class Simulator:
  STAND = 0
  HIT = 1
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
        total_gain = sum(sim.start_sim([10,10], 10, Simulator.STAND, [], []) for _ in range(iterations * 10**k))
        stand_error += abs(total_gain / (iterations * 10**k) - actual_stand)
      for _ in range(10):
        total_gain = sum(sim.start_sim([10,10], 10, Simulator.DOUBLE, [], []) for _ in range(iterations * 10**k))
        double_error += abs(total_gain / (iterations * 10**k) - actual_double)
      print(f"Iterations: {iterations*10**k} standError: {stand_error/10} doubleError: {double_error/10}")



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
          new_counts = list(counts)
          new_counts[rank] -= 1
          recurse(hand + [rank], new_counts, remaining - 1,
              hand_probs + [counts[rank] / remaining], rank)

      recurse([player_rank], counts_after_dealer, total_after_dealer,
          [prob_player * prob_up_card], 1)

    total = sum(next_card_probs)
    if total > 0:
      next_card_probs = [p / total for p in next_card_probs]
    return {"allHands": all_hands, "nextCardProbs": next_card_probs}



  def calc(
    self,
    strategy_folder: str | Path,
    out_folder: Path | None = None,
    prefix_base: str = "",
    prefix_das: str = "",
    workers: int | None = None,
    modes: list[str] | None = None,
  ) -> dict[str, pd.DataFrame]:
    import multiprocessing
    folder = Path(strategy_folder)
    das = self.dealer_settings.DAS
    modes = modes or ["hard", "soft", "pairs"]
    if out_folder is None:
      out_folder = folder
    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    max_workers = resolve_workers(workers)

    hard_results: list[dict] = []
    soft_results: list[dict] = []
    pairs_results: list[dict] = []

    das_label = "DAS" if das else "NDAS"
    _iters_ovr = getattr(self, '_iterations_override', None)
    iter_hard = load_iterations_csv(out_folder, "Hard", prefix_base, _iters_ovr) if "hard" in modes else None
    iter_soft = load_iterations_csv(out_folder, "Soft", prefix_base, _iters_ovr) if "soft" in modes else None
    iter_pairs = load_iterations_csv(out_folder, f"Pairs_{das_label}", prefix_das, _iters_ovr) if "pairs" in modes else None

    upcard_tasks = [
      {
        "dealer_settings": self.dealer_settings,
        "up_card": upcard,
        "hard_hands": self.hard_hands[upcard - 1],
        "soft_hands": self.soft_hands[upcard - 1],
        "iter_hard": iter_hard,
        "iter_soft": iter_soft,
        "iter_pairs": iter_pairs,
        "modes": modes,
        "das": das,
      }
      for upcard in range(1, 11)
    ]

    print(f"[Sim] {max_workers} workers, 10 upcards, phases: {modes}", flush=True)
    with multiprocessing.Pool(processes=max_workers) as pool:
      for result in pool.imap_unordered(upcard_worker, upcard_tasks):
        hard_results.extend(result.get("hard", []))
        soft_results.extend(result.get("soft", []))
        pairs_results.extend(result.get("pairs", []))

    out_dfs: dict[str, pd.DataFrame] = {}

    if hard_results:
      df, ev_lookup = build_matrix(hard_results, totals=list(range(21, 3, -1)))
      df.attrs["ev_lookup"] = ev_lookup
      out = out_folder / f"{prefix_base}_Hard_SIM.csv"
      df.to_csv(out)
      print(f"\nSaved -> {out}\n")
      print(df.to_string())
      out_dfs["Hard"] = df

    if soft_results:
      df, ev_lookup = build_matrix(soft_results, totals=list(range(21, 12, -1)))
      df.attrs["ev_lookup"] = ev_lookup
      out = out_folder / f"{prefix_base}_Soft_SIM.csv"
      df.to_csv(out)
      print(f"\nSaved -> {out}\n")
      print(df.to_string())
      out_dfs["Soft"] = df

    if pairs_results:
      up_card_order = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
      col_labels = [str(u) if u != 1 else "A" for u in up_card_order]
      pair_order = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
      pair_labels = ["10", "9", "8", "7", "6", "5", "4", "3", "2", "A"]
      result_map = {r["up_card"]: r["pair_results"] for r in pairs_results}
      evs_map = {r["up_card"]: r.get("pair_evs", {}) for r in pairs_results}
      rows = [[result_map[upcard].get(pv, "H") for upcard in up_card_order] for pv in pair_order]
      df = pd.DataFrame(rows, index=pair_labels, columns=col_labels)
      df.index.name = "Hand"
      ev_lookup = {
        (pair_label, col): evs_map.get(upcard, {}).get(pv, {})
        for pv, pair_label in zip(pair_order, pair_labels)
        for upcard, col in zip(up_card_order, col_labels)
      }
      df.attrs["ev_lookup"] = ev_lookup
      out = out_folder / f"{prefix_das}_Pairs_SIM.csv"
      df.to_csv(out)
      print(f"\nSaved -> {out}\n")
      print(df.to_string())
      out_dfs["Pairs"] = df

    return out_dfs

  def calc_hard(self, strategy_folder: str | Path, out_folder: Path | None = None, prefix_base: str = "", prefix_das: str = "", workers: int | None = None, **_) -> pd.DataFrame:
    return self.calc(strategy_folder, out_folder=out_folder, prefix_base=prefix_base, prefix_das=prefix_das, workers=workers, modes=["hard"])["Hard"]

  def calc_soft(self, strategy_folder: str | Path, out_folder: Path | None = None, prefix_base: str = "", prefix_das: str = "", workers: int | None = None, **_) -> pd.DataFrame:
    return self.calc(strategy_folder, out_folder=out_folder, prefix_base=prefix_base, prefix_das=prefix_das, workers=workers, modes=["soft"])["Soft"]

  def calc_pairs(self, strategy_folder: str | Path, out_folder: Path | None = None, prefix_base: str = "", prefix_das: str = "", workers: int | None = None, **_) -> pd.DataFrame:
    return self.calc(strategy_folder, out_folder=out_folder, prefix_base=prefix_base, prefix_das=prefix_das, workers=workers, modes=["pairs"])["Pairs"]



  def order_most_probable_hands(self, total_target, up_card, soft):
    all_hands = self.run_hand_sim(total_target, up_card, soft)["allHands"]
    if not all_hands:
      return []
    total_prob = sum(h["totalProb"] for h in all_hands)
    result = [{"hand": h["hand"], "normalizedProb": h["totalProb"] / total_prob if total_prob > 0 else 0.0} for h in all_hands]
    result.sort(key=lambda x: x["normalizedProb"], reverse=True)
    return result

  def get_only_top_compositions(self, soft):
    totals = list(range(13, 22)) if soft else list(range(4, 22))
    result = []
    for upcard in range(1, 11):
      upcard_row = []
      for total in totals:
        comps = self.order_most_probable_hands(total, upcard, soft)
        upcard_row.append(comps)
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



def resolve_workers(workers):
  import multiprocessing
  cpu = multiprocessing.cpu_count() or 1
  max_workers = min(workers if workers is not None else max(1, cpu - 4), 20)
  print(f"Detected {cpu} logical CPUs. Running with {max_workers} parallel workers.", flush=True)
  print("Use --workers N to adjust if your computer becomes unresponsive.", flush=True)
  return max_workers



def build_matrix(results: list[dict], totals: list[int]) -> tuple[pd.DataFrame, dict]:
  up_card_order = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
  col_labels = [str(u) if u != 1 else "A" for u in up_card_order]
  result_map: dict[int, dict] = {}
  ev_map: dict[int, dict] = {}
  for r in results:
    upcard = r["up_card"]
    result_map.setdefault(upcard, {}).update(r["totals"])
    ev_map.setdefault(upcard, {}).update(r.get("evs", {}))
  rows = [[result_map[upcard].get(t, "H") for upcard in up_card_order] for t in totals]
  df = pd.DataFrame(rows, index=totals, columns=col_labels)
  df.index.name = "Hand"
  ev_lookup: dict[tuple, dict] = {}
  for upcard, col in zip(up_card_order, col_labels):
    for t in totals:
      ev_lookup[(str(t), col)] = ev_map.get(upcard, {}).get(t, {})
  return df, ev_lookup



def upcard_worker(task: dict) -> dict:
  upcard = task["up_card"]
  modes = task["modes"]
  das = task["das"]
  hard_hands = task["hard_hands"]
  soft_hands = task["soft_hands"]
  iter_hard = task["iter_hard"]
  iter_soft = task["iter_soft"]
  iter_pairs = task["iter_pairs"]
  dealer_settings = task["dealer_settings"]

  hard_built = [-1] * 18
  soft_built = [-1] * 10

  code_map = {0: "S", 1: "H", 2: "DH"}

  def series(built, offset):
    import pandas as pd
    d = {i + offset: code_map[v] for i, v in enumerate(built) if v != -1}
    return pd.Series(d) if d else None

  def absorb_hard(result):
    for total, code in result["totals"].items():
      hard_built[total - 4] = 0 if "S" in code else (1 if code == "H" else 2)

  def absorb_soft(result):
    for total, code in result["totals"].items():
      soft_built[total - 12] = 0 if "S" in code else (1 if code == "H" else 2)

  def make_task(mode, hands=None, iter_df=None, totals_override=None):
    t = {
      "dealer_settings": dealer_settings,
      "up_card": upcard,
      "iter_df": iter_df,
      "hard_series": series(hard_built, 4),
      "soft_series": series(soft_built, 12),
      "mode": mode,
    }
    if hands is not None:
      t["hands_for_upcard"] = hands
    if totals_override is not None:
      t["totals_override"] = totals_override
    return t

  out = {"hard": [], "soft": [], "pairs": []}

  if "hard" in modes:
    r = worker(make_task("hard", hard_hands, iter_hard, range(21, 10, -1)))
    absorb_hard(r); out["hard"].append(r)

  if "soft" in modes:
    r = worker(make_task("soft", soft_hands, iter_soft))
    absorb_soft(r); out["soft"].append(r)

  if "hard" in modes:
    r = worker(make_task("hard", hard_hands, iter_hard, range(10, 3, -1)))
    absorb_hard(r); out["hard"].append(r)

  if "pairs" in modes:
    r = worker(make_task("pairs", None, iter_pairs))
    out["pairs"].append(r)

  return out



def worker(task: dict) -> dict:
  dealer_settings: DealerSettingsObject = task["dealer_settings"]
  up_card: int = task["up_card"]
  iterations: int = task.get("iterations", 10_000)
  hard_series = task.get("hard_series")
  soft_series = task.get("soft_series")
  mode: str = task["mode"]

  STAND = 0
  HIT = 1
  DOUBLE = 2

  iter_df = task.get("iter_df")

  if hard_series is not None:
    hard_series = hard_series.copy()
    hard_series.index = hard_series.index.astype(int)
  if soft_series is not None:
    soft_series = soft_series.copy()
    soft_series.index = soft_series.index.astype(int)

  hard_choices = hard_series if hard_series is not None else [-1] * 18
  soft_choices = soft_series if soft_series is not None else [-1] * 10

  def run_n(hand: list[int], choice: int, n: int) -> float:
    import math
    sim = BlackjackSimulator(dealer_settings)
    total_gain = 0.0
    count = 0
    attempts = 0
    max_attempts = n * 10
    while count < n and attempts < max_attempts:
      result = sim.start_sim(hand, up_card, choice, hard_choices, soft_choices)
      attempts += 1
      if math.isnan(result):
        continue
      total_gain += result
      count += 1
    return total_gain / count if count > 0 else 0.0

  up_label = "A" if up_card == 1 else str(up_card)
  print(f"[{mode}|upCard={up_label}] Starting", flush=True)

  if mode == "pairs":
    pair_results: dict[int, str] = {}
    pair_evs: dict[int, dict] = {}

    def split_hand_ev(pair_val: int, n: int) -> float:
      import math
      sim = BlackjackSimulator(dealer_settings)
      total_gain = 0.0
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
        total_gain += result
        count += 1
      return total_gain / count if count > 0 else 0.0

    for pair_val in range(1, 11):
      hand = [pair_val, pair_val]
      pair_label = "A" if pair_val == 1 else str(pair_val)
      cell_iters = get_iterations_for_cell(iter_df, pair_label, up_card)
      stand_ev = run_n(hand, STAND, cell_iters)
      hit_ev = run_n(hand, HIT, cell_iters)
      double_ev = run_n(hand, DOUBLE, cell_iters)

      split_ev = split_hand_ev(pair_val, cell_iters)
      double_ev_norm = double_ev / 2.0
      best_no_split_ev = max(stand_ev, hit_ev, double_ev_norm)
      code = "P" if split_ev > best_no_split_ev else resolve_ev_to_code(stand_ev, hit_ev, double_ev)

      pair_label = "A" if pair_val == 1 else str(pair_val)
      print(f"[pairs|upCard={up_label}] {pair_label},{pair_label}: {code} "
          f"(S={stand_ev:.4f} H={hit_ev:.4f} D={double_ev_norm:.4f} P={split_ev:.4f})", flush=True)
      pair_results[pair_val] = code
      pair_evs[pair_val] = {"S": stand_ev, "H": hit_ev, "D": double_ev_norm, "P": split_ev}
    print(f"[pairs|upCard={up_label}] Done", flush=True)
    return {"mode": mode, "up_card": up_card, "pair_results": pair_results, "pair_evs": pair_evs}

  hands_for_upcard: list = task["hands_for_upcard"]
  is_soft = (mode == "soft")
  totals_range = task.get("totals_override") or (range(21, 12, -1) if is_soft else range(21, 3, -1))
  totals_out: dict[int, str] = {}
  evs_out: dict[int, dict] = {}

  for hand_total in totals_range:
    index = (hand_total - 13) if is_soft else (hand_total - 4)
    comps = hands_for_upcard[index]

    cell_iters = get_iterations_for_cell(iter_df, hand_total, up_card)

    stand_ev = hit_ev = double_ev = 0.0
    for comp in comps:
      p = comp["normalizedProb"]
      comp_iters = max(1, round(p * cell_iters))
      stand_ev += run_n(comp["hand"], STAND, comp_iters) * p
      hit_ev += run_n(comp["hand"], HIT, comp_iters) * p
      double_ev += run_n(comp["hand"], DOUBLE, comp_iters) * p

    code = resolve_ev_to_code(stand_ev, hit_ev, double_ev)

    if isinstance(hard_choices, list) and not is_soft:
      int_choice = STAND if "S" in code else (HIT if "H" in code else DOUBLE)
      hard_choices[hand_total - 4] = int_choice
    if isinstance(soft_choices, list) and is_soft:
      int_choice = STAND if "S" in code else (HIT if "H" in code else DOUBLE)
      soft_choices[hand_total - 12] = int_choice

    totals_out[hand_total] = code
    evs_out[hand_total] = {"S": stand_ev, "H": hit_ev, "D": double_ev / 2.0}
    print(f"[{mode}|upCard={up_label}] {hand_total}: {code} "
        f"(S={stand_ev:.4f} H={hit_ev:.4f} D={double_ev / 2.0:.4f})", flush=True)

  print(f"[{mode}|upCard={up_label}] Done", flush=True)
  return {"mode": mode, "up_card": up_card, "totals": totals_out, "evs": evs_out}



if __name__ == "__main__":
  import argparse
  import multiprocessing
  multiprocessing.freeze_support()

  parser = argparse.ArgumentParser(description="Run blackjack strategy simulation.")
  parser.add_argument("--decks", type=int, default=6)
  parser.add_argument("--s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", action="store_true", default=False)
  parser.add_argument("--das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")
  parser.add_argument("--confidence", type=float, default=0.95)
  parser.add_argument("--workers", type=int, default=None)
  parser.add_argument("--iterations", type=int, default=None)
  args = parser.parse_args()

  dealer_settings = DealerSettingsObject(
    decks=args.decks, S17=args.s17, ENHC=args.enhc,
    DAS=args.das, BJPay=1.5,
  )

  matrices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategy_matrices")
  folder = strategy_folder(matrices_dir, args.decks, args.s17, args.enhc)
  script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
  data_dir = (script_dir / ".." / "Data").resolve()

  print(f"Settings : {args.decks}D {'S17' if args.s17 else 'H17'} {'ENHC' if args.enhc else 'US'} {'DAS' if args.das else 'nDAS'}")
  print(f"Folder : {folder}")
  print(f"Confidence: {args.confidence*100:.0f}%")

  out_folder = output_folder(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
  prefix_base = rule_prefix(args.decks, args.s17, args.enhc)
  prefix_das = rule_prefix(args.decks, args.s17, args.enhc, args.das)

  if args.iterations is None:
    calc_and_save_iterations(
      folder, data_dir, args.confidence,
      decks=args.decks, s17=args.s17, enhc=args.enhc, das=args.das,
      out_folder=out_folder, prefix_base=prefix_base, prefix_das=prefix_das,
    )
  else:
    print(f"Using fixed {args.iterations:,} iterations per cell (skipping iteration calculation).", flush=True)

  print("\nBuilding hand compositions...")
  sim = Simulator.create(dealer_settings)
  print("Done. Starting simulation...\n")

  sim._iterations_override = args.iterations
  results_dfs = sim.calc(folder, out_folder=out_folder,
               prefix_base=prefix_base, prefix_das=prefix_das,
               workers=args.workers, modes=["hard", "soft", "pairs"])

  print("\n" + "=" * 50)
  print("ACCURACY REPORT")
  print("=" * 50)

  def sim_key(hand, is_pairs: bool) -> str:
    return str(hand).strip()

  total_wrong = 0
  for table_name, sim_df in results_dfs.items():
    verified_df = load_strategy_csv(folder, table_name, das=args.das)
    if verified_df is None:
      print(f"{table_name}: no verified CSV found at {folder}, skipping")
      continue

    is_pairs = (table_name == "Pairs")
    v_lookup = {str(i).strip(): i for i in verified_df.index}

    wrong: list[str] = []
    for hand in sim_df.index:
      key = sim_key(hand, is_pairs)
      if key not in v_lookup:
        continue
      v_hand = v_lookup[key]
      for col in sim_df.columns:
        if col not in verified_df.columns:
          continue
        sim_val = str(sim_df.loc[hand, col]).strip().upper()
        verified_val = str(verified_df.loc[v_hand, col]).strip().upper()
        if sim_val != verified_val:
          ev_note = ""
          ev_lookup = sim_df.attrs.get("ev_lookup", {})
          evs = ev_lookup.get((key, col), {})
          if evs:
            got_ev = evs.get(sim_val[0], evs.get("P", None))
            want_ev = evs.get(verified_val[0], None)
            if got_ev is not None and want_ev is not None:
              ev_note = f" (margin: {got_ev - want_ev:.4f})"
          wrong.append(f" {table_name} {key} vs {col}: got={sim_val} expected={verified_val}{ev_note}")

    total_wrong += len(wrong)
    status = "✓ Perfect" if not wrong else f"✗ {len(wrong)} incorrect"
    print(f"{table_name}: {status}")
    for w in wrong:
      print(w)

  print("-" * 50)
  print(f"Total incorrect decisions: {total_wrong}")
  print("=" * 50)

