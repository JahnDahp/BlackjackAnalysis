# Run with: python plot_sim.py [--decks N] [--s17|--h17] [--enhc] [--das|--ndas] [--workers N]

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from blackjack_sim import (
  strategy_folder, load_strategy_csv,
  rule_prefix, Simulator as blackjack_simulator,
)
from blackjack import DealerSettingsObject



ITERATION_COUNTS = [100, 1_000, 10_000, 100_000]



def count_errors(results_dfs: dict, folder: Path, das: bool) -> int:
  total_wrong = 0
  for table_name, sim_df in results_dfs.items():
    verified_df = load_strategy_csv(folder, table_name, das=das)
    if verified_df is None:
      continue
    v_lookup = {str(i).strip(): i for i in verified_df.index}
    for hand in sim_df.index:
      key = str(hand).strip()
      if key not in v_lookup:
        continue
      v_hand = v_lookup[key]
      for col in sim_df.columns:
        if col not in verified_df.columns:
          continue
        sim_val = str(sim_df.loc[hand, col]).strip().upper()
        ver_val = str(verified_df.loc[v_hand, col]).strip().upper()
        if sim_val != ver_val:
          total_wrong += 1
  return total_wrong



def main() -> None:
  import multiprocessing
  multiprocessing.freeze_support()

  parser = argparse.ArgumentParser()
  parser.add_argument("--decks", type=int, default=6)
  parser.add_argument("--s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", action="store_true", default=False)
  parser.add_argument("--das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")
  parser.add_argument("--workers", type=int, default=None)
  args = parser.parse_args()

  rules = DealerSettingsObject(
    decks=args.decks, S17=args.s17, ENHC=args.enhc,
    DAS=args.das, BJPay=1.5,
  )

  matrices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "strategy_matrices")
  output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_convergence_plot.png")
  folder = strategy_folder(matrices_dir, args.decks, args.s17, args.enhc)
  prefix_base = rule_prefix(args.decks, args.s17, args.enhc)
  prefix_das = rule_prefix(args.decks, args.s17, args.enhc, args.das)

  print(f"Settings: {args.decks}D {'S17' if args.s17 else 'H17'} "
      f"{'ENHC' if args.enhc else 'US'} {'DAS' if args.das else 'nDAS'}")
  print(f"Building hand compositions...")
  sim = blackjack_simulator.create(rules)
  print(f"Done. Testing {len(ITERATION_COUNTS)} iteration counts...\n")

  error_counts = []
  iter_times = []

  import time
  total_start = time.time()

  import tempfile
  import pandas as _pd

  for iters in ITERATION_COUNTS:
    iter_start = time.time()
    print(f"── {iters:>10,} iterations ──────────────────────────", flush=True)

    up_labels = ["2","3","4","5","6","7","8","9","10","A"]
    das_label = "DAS" if args.das else "NDAS"

    with tempfile.TemporaryDirectory() as tmp_dir:
      from pathlib import Path as _Path
      tmp = _Path(tmp_dir)
      for name, index in [
        ("Hard", list(range(21, 3, -1))),
        ("Soft", list(range(21, 12, -1))),
        (f"Pairs_{das_label}", ["10","9","8","7","6","5","4","3","2","A"]),
      ]:
        df = _pd.DataFrame(
          [[iters] * 10 for _ in index],
          index=[str(i) for i in index],
          columns=up_labels,
        )
        df.index.name = "Hand"
        df.to_csv(tmp / f"{name}_Iterations.csv")

      results_dfs = sim.calc(
        folder,
        out_folder=tmp,
        prefix_base=prefix_base,
        prefix_das=prefix_das,
        workers=args.workers,
        modes=["hard", "soft", "pairs"],
      )

    errors = count_errors(results_dfs, folder, args.das)
    elapsed = time.time() - iter_start
    iter_times.append(elapsed)
    error_counts.append(errors)
    print(f" → {errors} incorrect decisions ({elapsed:.1f}s | {iters:,} iters/cell)\n", flush=True)

  total_elapsed = time.time() - total_start
  print(f"Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)\n")
  print("\nSummary:")
  print(f" {'Iterations':<12} {'Errors':>6} {'Time':>8}")
  print("  " + "-"*32)
  for it, er, tm in zip(ITERATION_COUNTS, error_counts, iter_times):
    print(f" {it:<12,} {er:>6} {tm:>7.1f}s")
  print(f" {'TOTAL':<12} {'':<6} {total_elapsed:>7.1f}s")

  print("Generating plot...")

  rule_str = (f"{args.decks}D {'S17' if args.s17 else 'H17'} "
        f"{'ENHC' if args.enhc else 'US'} {'DAS' if args.das else 'nDAS'}")

  def fmt(count): return f"{count/1_000_000:.3g}M" if count >= 1_000_000 else (f"{count//1000}K" if count >= 1000 else str(count))

  figure, axes = plt.subplots()
  axes.plot(ITERATION_COUNTS, error_counts, marker="o", label="Monte Carlo Simulator")
  axes.set_xscale("log")
  axes.set_xticks(ITERATION_COUNTS)
  axes.set_xticklabels([fmt(count) for count in ITERATION_COUNTS])
  axes.set_xlabel("Iterations per cell")
  axes.set_ylabel("Incorrect Decisions")
  axes.set_title(f"Monte Carlo Simulator Convergence  |  {rule_str}")
  axes.legend()
  plt.tight_layout()
  plt.savefig(output, dpi=150)
  plt.close()

  print(f"\nPlot saved -> {output}")
  print("\nResults summary:")
  for iters, errors in zip(ITERATION_COUNTS, error_counts):
    print(f" {iters:>10,} iters: {errors} incorrect")



if __name__ == "__main__":
  main()

