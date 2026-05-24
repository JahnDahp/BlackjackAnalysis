"""
plot_sim_convergence.py

Runs the Monte Carlo simulator at fixed iteration counts and plots
number of incorrect decisions vs iterations.

Usage:
    python plot_sim_convergence.py
    python plot_sim_convergence.py --decks 1 --s17 --das
    python plot_sim_convergence.py --matrices-dir ../VerifiedStrategyMatrices
    python plot_sim_convergence.py --output convergence.png

Iteration counts tested: 100, 1000, 10000, 100000, 500000, 1000000
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from blackjack_sim import (
    _strategy_folder, _load_strategy_csv,
    _rule_prefix, blackjack_simulator,
)
from blackjack import DealerSettingsObject


ITERATION_COUNTS = [100, 1_000, 10_000, 100_000]


# ---------------------------------------------------------------------------
# Error counting
# ---------------------------------------------------------------------------

def _count_errors(results_dfs: dict, folder: Path, das: bool) -> int:
    total_wrong = 0
    for table_name, sim_df in results_dfs.items():
        verified_df = _load_strategy_csv(folder, table_name, das=das)
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser()
    parser.add_argument("--decks",        type=int,   default=6)
    parser.add_argument("--s17",          action="store_true", default=False)
    parser.add_argument("--h17",          dest="s17", action="store_false")  # default
    parser.add_argument("--enhc",         action="store_true", default=False)
    parser.add_argument("--das",          action="store_true", default=True)
    parser.add_argument("--ndas",         dest="das", action="store_false")
    parser.add_argument("--bj-pay",       type=float, default=1.5)
    parser.add_argument("--workers",      type=int,   default=None)
    parser.add_argument("--matrices-dir", dest="matrices_dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", "VerifiedStrategyMatrices"))
    parser.add_argument("--output", default=os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "sim_convergence_plot.png"))
    args = parser.parse_args()

    rules = DealerSettingsObject(
        decks=args.decks, S17=args.s17, ENHC=args.enhc,
        DAS=args.das, BJPay=args.bj_pay,
    )

    folder       = _strategy_folder(args.matrices_dir, args.decks, args.s17, args.enhc)
    prefix_base  = _rule_prefix(args.decks, args.s17, args.enhc)
    prefix_das   = _rule_prefix(args.decks, args.s17, args.enhc, args.das)

    print(f"Settings: {args.decks}D  {'S17' if args.s17 else 'H17'}  "
          f"{'ENHC' if args.enhc else 'US'}  {'DAS' if args.das else 'nDAS'}")
    print(f"Building hand compositions...")
    sim = blackjack_simulator.create(rules)
    print(f"Done. Testing {len(ITERATION_COUNTS)} iteration counts...\n")

    error_counts = []
    iter_times  = []

    import time
    total_start = time.time()

    for iters in ITERATION_COUNTS:
        iter_start = time.time()
        print(f"── {iters:>10,} iterations ──────────────────────────", flush=True)

        # Write flat iteration CSVs directly into the strategy folder
        import pandas as _pd
        up_labels  = ["2","3","4","5","6","7","8","9","10","A"]
        pair_labels = ["10","9","8","7","6","5","4","3","2","A"]
        das_label  = "DAS" if args.das else "NDAS"
        for name, index in [
            ("Hard",           list(range(21, 3,  -1))),
            ("Soft",           list(range(21, 12, -1))),
            (f"Pairs_{das_label}", ["10","9","8","7","6","5","4","3","2","A"]),
        ]:
            df = _pd.DataFrame(
                [[iters] * 10 for _ in index],
                index=[str(i) for i in index],
                columns=up_labels,
            )
            df.index.name = "Hand"
            df.to_csv(folder / f"{name}_Iterations.csv")

        results_dfs = sim.calc(
            folder,
            out_folder=folder,
            prefix_base=prefix_base,
            prefix_das=prefix_das,
            workers=args.workers,
            modes=["hard", "soft", "pairs"],
        )

        errors = _count_errors(results_dfs, folder, args.das)
        elapsed = time.time() - iter_start
        iter_times.append(elapsed)
        error_counts.append(errors)
        print(f"  → {errors} incorrect decisions  ({elapsed:.1f}s  |  {iters:,} iters/cell)\n", flush=True)

    # ---------------------------------------------------------------------------
    total_elapsed = time.time() - total_start
    print(f"Total time: {total_elapsed:.1f}s  ({total_elapsed/60:.1f} min)\n")
    print("\nSummary:")
    print(f"  {'Iterations':<12}  {'Errors':>6}  {'Time':>8}")
    print("  " + "-"*32)
    for it, er, tm in zip(ITERATION_COUNTS, error_counts, iter_times):
        print(f"  {it:<12,}  {er:>6}  {tm:>7.1f}s")
    print(f"  {'TOTAL':<12}  {'':<6}  {total_elapsed:>7.1f}s")

    # Plot
    # ---------------------------------------------------------------------------
    print("Generating plot...")

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d27")

    x = np.array(ITERATION_COUNTS)

    ax.plot(x, error_counts,
            color="#4FC3F7", linewidth=2.5,
            marker="o", markersize=8,
            markerfacecolor="#4FC3F7", markeredgecolor="#0f1117", markeredgewidth=1.5,
            label="Monte Carlo Simulator", zorder=3)

    ax.fill_between(x, error_counts, alpha=0.12, color="#4FC3F7")

    # Annotate each point
    for xi, yi in zip(x, error_counts):
        ax.annotate(str(yi),
                    xy=(xi, yi),
                    xytext=(0, 12), textcoords="offset points",
                    ha="center", fontsize=11, color="#4FC3F7")

    # Zero line
    ax.set_xscale("log")
    ax.set_xlabel("Iterations per cell", fontsize=13, color="#cccccc", labelpad=10)
    ax.set_ylabel("Incorrect Decisions", fontsize=13, color="#cccccc", labelpad=10)

    rule_str = (f"{args.decks}D  {'S17' if args.s17 else 'H17'}  "
                f"{'ENHC' if args.enhc else 'US'}  {'DAS' if args.das else 'nDAS'}")
    ax.set_title(f"Monte Carlo Simulator Convergence\n{rule_str}",
                 fontsize=15, color="#ffffff", pad=18, fontweight="bold")

    tick_labels = ["100", "1K", "10K", "100K", "500K", "1M"]
    completed = ITERATION_COUNTS[:len(error_counts)]
    completed_labels = tick_labels[:len(error_counts)]
    ax.set_xticks(completed)
    ax.set_xticklabels(completed_labels, fontsize=11)
    ax.tick_params(colors="#888888", labelsize=11)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333344")

    ax.grid(True, which="both", color="#252535", linewidth=0.8, alpha=0.8)
    ax.set_ylim(bottom=-0.5)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax.legend(fontsize=12, framealpha=0.25, facecolor="#1a1d27",
              edgecolor="#444455", labelcolor="#dddddd", loc="upper right")

    fig.text(0.99, 0.01,
             f"Total time: {total_elapsed:.1f}s  ({total_elapsed/60:.1f} min)",
             ha="right", va="bottom", fontsize=10,
             color="#666677", fontstyle="italic")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()

    print(f"\nPlot saved -> {args.output}")
    print("\nResults summary:")
    for iters, errors in zip(ITERATION_COUNTS, error_counts):
        print(f"  {iters:>10,} iters: {errors} incorrect")


if __name__ == "__main__":
    main()