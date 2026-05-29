# Run with: python blackjack_rl.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--episodes N]

from __future__ import annotations
import math
import random
from pathlib import Path
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from blackjack import (
  BlackjackSimulator, DealerSettingsObject,
  _STAND, _HIT, _DOUBLE, _SPLIT, _NONE,
)



STAND = _STAND
HIT = _HIT
DOUBLE = _DOUBLE
SPLIT = _SPLIT

ACTION_NAMES = {STAND: "S", HIT: "H", DOUBLE: "DH", SPLIT: "P"}
HARD_ACTIONS = [STAND, HIT, DOUBLE]
PAIR_DAS_ACTIONS = [STAND, HIT, DOUBLE, SPLIT]
PAIR_NDAS_ACTIONS= [STAND, HIT, SPLIT]



_N_ACTIONS = 4

def empty_table(n_rows: int) -> list:
  def init():
    return [1.0] * _N_ACTIONS
  return [[init() for _ in range(10)] for _ in range(n_rows)]



class QTable:
  def __init__(self, das: bool) -> None:
    self.das = das
    self.hard = empty_table(18)
    self.soft = empty_table(9)
    self.pairs = empty_table(10)
    self.hard_visits = [[[0] * _N_ACTIONS for _ in range(10)] for _ in range(18)]
    self.soft_visits = [[[0] * _N_ACTIONS for _ in range(10)] for _ in range(9)]
    self.pairs_visits = [[[0] * _N_ACTIONS for _ in range(10)] for _ in range(10)]
    self._dirty = True
    self._hard_dbl = [_NONE] * 22
    self._hard_nodbl = [_NONE] * 22
    self._soft_dbl = [_NONE] * 22
    self._soft_nodbl = [_NONE] * 22
    self.rebuild_strategy()

  def row(self, table: str, key: int) -> int:
    if table == "hard": return key - 4   # totals 4-21 → indices 0-17
    if table == "soft": return key - 13  # totals 13-21 → indices 0-8
    return key - 1                       # pairs 1-10 → indices 0-9

  def tbl(self, table: str) -> list:
    if table == "hard": return self.hard
    if table == "soft": return self.soft
    return self.pairs

  def visits_tbl(self, table: str) -> list:
    if table == "hard": return self.hard_visits
    if table == "soft": return self.soft_visits
    return self.pairs_visits



  def actions(self, table: str) -> list[int]:
    if table == "pairs_das": return PAIR_DAS_ACTIONS
    if table == "pairs_ndas": return PAIR_NDAS_ACTIONS
    return HARD_ACTIONS

  def best_action(self, table: str, key: int, upcard: int) -> int:
    row = self.row(table, key)
    col = upcard - 1
    q = self.tbl(table)[row][col]
    return max(self.actions(table), key=lambda a: q[a])

  def update(self, table: str, key: int, upcard: int,
         action: int, reward: float) -> None:
    row = self.row(table, key)
    col = upcard - 1
    tbl = self.tbl(table)
    visits = self.visits_tbl(table)
    visits[row][col][action] += 1
    alpha = 1.0 / visits[row][col][action]
    tbl[row][col][action] += alpha * (reward - tbl[row][col][action])
    self._dirty = True

  def rebuild_strategy(self) -> None:
    for total in range(4, 22):
      acts = [self.best_action("hard", total, upcard) for upcard in range(1, 11)]
      modal = max(set(acts), key=acts.count)
      self._hard_dbl[total] = modal
      self._hard_nodbl[total] = HIT if modal == DOUBLE else modal
    for total in range(13, 22):
      acts = [self.best_action("soft", total, upcard) for upcard in range(1, 11)]
      modal = max(set(acts), key=acts.count)
      self._soft_dbl[total] = modal
      self._soft_nodbl[total] = HIT if modal == DOUBLE else modal
    self._dirty = False

  def get_strategy_arrays(self):
    if self._dirty:
      self.rebuild_strategy()
    return (self._hard_dbl, self._soft_dbl,
        self._hard_nodbl, self._soft_nodbl)

  def action_code(self, table: str, key: int, upcard: int) -> str:
    """Return strategy code including DS vs DH distinction for doubles."""
    best = self.best_action(table, key, upcard)
    if best != DOUBLE:
      return ACTION_NAMES[best]
    actions = self.actions(table)
    row = self.row(table, key)
    col = upcard - 1
    q = self.tbl(table)[row][col]
    others = [a for a in actions if a != DOUBLE]
    second = max(others, key=lambda a: q[a])
    return "DS" if second == STAND else "DH"

  def to_strategy_dicts(self) -> dict:
    result = {"hard": {}, "soft": {}, "pairs": {}}
    for upcard in range(1, 11):
      uc_label = "A" if upcard == 1 else str(upcard)
      for total in range(4, 22):
        result["hard"].setdefault(total, {})[uc_label] = self.action_code("hard", total, upcard)
      for total in range(13, 22):
        result["soft"].setdefault(total, {})[uc_label] = self.action_code("soft", total, upcard)
      for pair_rank in range(1, 11):
        result["pairs"].setdefault(pair_rank, {})[uc_label] = self.action_code(
          "pairs_das" if self.das else "pairs_ndas", pair_rank, upcard)
    return result



def strategy_folder(base_dir: str, decks: int, s17: bool, enhc: bool, das: bool) -> Path:
  deck_str = "1D" if decks == 1 else ("2D" if decks == 2 else "MD")
  return (Path(base_dir) / deck_str / ("S17" if s17 else "H17")
      / ("ENHC" if enhc else "US"))



def output_folder(base_dir: str) -> Path:
  from datetime import datetime
  now = datetime.now()
  stamp = now.strftime(f"RL_{now.month}_{now.day}_{now.year}_%H-%M")
  return Path(base_dir) / "outputs" / "outputs_rl" / stamp

def rule_prefix(decks: int, s17: bool, enhc: bool, das: bool | None = None) -> str:
  deck_str = "1D" if decks == 1 else ("2D" if decks == 2 else "MD")
  rule_str = "S17" if s17 else "H17"
  peek_str = "ENHC" if enhc else "US"
  if das is None:
    return f"{deck_str}_{rule_str}_{peek_str}"
  return f"{deck_str}_{rule_str}_{peek_str}_{'DAS' if das else 'NDAS'}"



def load_strategy_csv(folder: Path, name: str, das: bool | None = None) -> pd.DataFrame | None:
  parts = folder.parts
  clean_parts = [p for p in parts[-4:] if p not in ("DAS", "NDAS")][-3:]
  prefix = "_".join(clean_parts) if len(clean_parts) >= 3 else "_".join(parts[-3:])
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



def upcard_weights(decks: int) -> list[float]:
  counts = [decks * 4] * 10
  counts[9] = decks * 16
  total = sum(counts)
  return [c / total for c in counts]



def sample_upcard(weights: list[float]) -> int:
  r = random.random()
  cumul = 0.0
  for i, w in enumerate(weights):
    cumul += w
    if r < cumul:
      return i + 1
  return 10



def sample_hand(decks: int, upcard: int) -> list[int]:
  counts = [0] + [decks * 4] * 9 + [decks * 16]
  counts[upcard] -= 1
  total = sum(counts[1:])

  def draw() -> int:
    r = random.randrange(total)
    for rank in range(1, 11):
      r -= counts[rank]
      if r < 0:
        return rank
    return 10

  c1 = draw(); counts[c1] -= 1
  c2 = draw()
  return [c1, c2]



def classify(cards: list[int]) -> tuple[str, int]:
  if len(cards) == 2 and cards[0] == cards[1]:
    return "pair", cards[0]
  total = aces = 0
  for rank in cards:
    if rank == 1: total += 11; aces += 1
    else: total += rank
  while total > 21 and aces > 0: total -= 10; aces -= 1
  return ("soft" if aces > 0 else "hard"), total



def run_episode(
  sim: BlackjackSimulator,
  q: QTable,
  upcard: int,
  hand: list[int],
  epsilon: float,
  hard_dbl: list[int],
  soft_dbl: list[int],
) -> None:
  table_type, key = classify(hand)
  table = ("pairs_das" if sim.rules.DAS else "pairs_ndas") if table_type == "pair" else table_type

  actions = q.actions(table)
  action = random.choice(actions) if random.random() < epsilon else q.best_action(table, key, upcard)

  gain = math.nan
  for _ in range(20):
    gain = sim.start_sim(hand, upcard, action, hard_dbl, soft_dbl)
    if not math.isnan(gain):
      break
  if math.isnan(gain):
    return



  q.update(table, key, upcard, action, gain)



def train(
  rules: DealerSettingsObject,
  n_episodes: int = 50_000_000,
  epsilon_start: float = 0.1,
  epsilon_end: float = 0.01,
) -> QTable:
  sim = BlackjackSimulator(rules)
  q = QTable(das=rules.DAS)
  upcard_weights = upcard_weights(rules.decks)
  hard_dbl, soft_dbl, _, _ = q.get_strategy_arrays()

  rebuild_every = 10_000
  log_every = max(1, n_episodes // 10)

  for ep in range(1, n_episodes + 1):
    epsilon = epsilon_start + (epsilon_end - epsilon_start) * ep / n_episodes
    upcard = sample_upcard(upcard_weights)
    hand = sample_hand(rules.decks, upcard)

    run_episode(sim, q, upcard, hand, epsilon, hard_dbl, soft_dbl)

    if ep % rebuild_every == 0:
      hard_dbl, soft_dbl, _, _ = q.get_strategy_arrays()

    if ep % log_every == 0:
      percent = 100 * ep // n_episodes
      print(f" {ep:>12,} / {n_episodes:,} ({percent:3d}%) eps={epsilon:.3f}", flush=True)

  return q



def export_csvs(q: QTable, folder: Path, out_folder: Path | None = None, prefix_base: str = "", prefix_das: str = "") -> dict[str, pd.DataFrame]:
  if out_folder is None:
    out_folder = folder
  out_folder = Path(out_folder)
  out_folder.mkdir(parents=True, exist_ok=True)
  strat = q.to_strategy_dicts()
  upcards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
  up_labels = ["2","3","4","5","6","7","8","9","10","A"]
  out_dfs = {}

  pair_ranks = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
  pair_labels = ["10","9","8","7","6","5","4","3","2","A"]

  for name, keys, key_labels, table_key in [
    ("Hard", list(range(21,3,-1)), [str(t) for t in range(21,3,-1)], "hard"),
    ("Soft", list(range(21,12,-1)), [str(t) for t in range(21,12,-1)], "soft"),
    ("Pairs", pair_ranks, pair_labels, "pairs"),
  ]:
    rows = [[strat[table_key].get(k, {}).get("A" if upcard==1 else str(upcard), "H")
         for upcard in upcards] for k in keys]
    df = pd.DataFrame(rows, index=key_labels, columns=up_labels)
    df.index.name = "Hand"
    if name in ("Hard", "Soft"):
      try: df.index = df.index.astype(int)
      except: pass
    prefix = prefix_das if name == "Pairs" else prefix_base
    file_name = f"{prefix}_{name}_RL.csv" if prefix else f"{name}_RL.csv"
    path = out_folder / file_name
    df.to_csv(path)
    print(f"\nSaved -> {path}\n")
    print(df.to_string())
    out_dfs[name] = df

  return out_dfs



def accuracy_report(out_dfs: dict[str, pd.DataFrame], folder: Path, das: bool) -> None:
  print("\n" + "=" * 50)
  print("ACCURACY REPORT")
  print("=" * 50)

  table_map = {
    "Hard": ("Hard", None),
    "Soft": ("Soft", None),
    "Pairs": ("Pairs", das),
  }

  total_wrong = 0
  for rl_name, (csv_name, das_flag) in table_map.items():
    rl_df = out_dfs.get(rl_name)
    if rl_df is None:
      continue
    verified_df = load_strategy_csv(folder, csv_name, das=das_flag)
    if verified_df is None:
      print(f"{rl_name}: no verified CSV found, skipping")
      continue

    v_lookup = {str(i).strip(): i for i in verified_df.index}
    wrong: list[str] = []

    for hand in rl_df.index:
      key = str(hand).strip()
      if key not in v_lookup:
        continue
      v_hand = v_lookup[key]
      for col in rl_df.columns:
        if col not in verified_df.columns:
          continue
        rl_val = str(rl_df.loc[hand, col]).strip().upper()
        ver_val = str(verified_df.loc[v_hand, col]).strip().upper()
        if rl_val != ver_val:
          wrong.append(f" {rl_name} {key} vs {col}: got={rl_val} expected={ver_val}")

    total_wrong += len(wrong)
    print(f"{rl_name}: {'✓ Perfect' if not wrong else f'✗ {len(wrong)} incorrect'}")
    for w in wrong:
      print(w)

  print("-" * 50)
  print(f"Total incorrect decisions: {total_wrong}")
  print("=" * 50)



if __name__ == "__main__":
  import argparse, time

  parser = argparse.ArgumentParser()
  parser.add_argument("--decks", type=int, default=6)
  parser.add_argument("--s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", action="store_true", default=False)
  parser.add_argument("--das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")

  parser.add_argument("--episodes", type=int, default=50_000_000)
  args = parser.parse_args()

  rules = DealerSettingsObject(
    decks=args.decks, S17=args.s17, ENHC=args.enhc,
    DAS=args.das, BJPay=1.5,
  )

  matrices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategy_matrices")
  folder = strategy_folder(matrices_dir, args.decks, args.s17, args.enhc, args.das)
  folder.mkdir(parents=True, exist_ok=True)

  print(f"Settings : {args.decks}D {'S17' if args.s17 else 'H17'} "
      f"{'ENHC' if args.enhc else 'US'} {'DAS' if args.das else 'nDAS'}")
  print(f"Folder : {folder}")
  print(f"Episodes : {args.episodes:,}\n")

  t0 = time.time()
  q = train(rules,
        n_episodes=args.episodes)
  elapsed = time.time() - t0

  print(f"\nTraining complete in {elapsed:.1f}s ({args.episodes/elapsed:,.0f} episodes/sec)")

  out_folder = output_folder(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
  prefix_base = rule_prefix(args.decks, args.s17, args.enhc)
  prefix_das = rule_prefix(args.decks, args.s17, args.enhc, args.das)
  out_dfs = export_csvs(q, folder, out_folder=out_folder, prefix_base=prefix_base, prefix_das=prefix_das)
  accuracy_report(out_dfs, folder, das=args.das)

