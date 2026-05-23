"""
plot_rl_convergence.py

Runs the RL agent at episode counts equivalent to the Monte Carlo simulator's
iteration counts (scaled by 1210 total simulator calls per iteration count).

Episode counts: 121000, 1210000, 12100000, 121000000, 605000000, 1210000000
Equivalent MC:  100,    1000,    10000,    100000,    500000,    1000000

Usage:
    python plot_rl_convergence.py
    python plot_rl_convergence.py --decks 1 --s17 --das
    python plot_rl_convergence.py --output rl_convergence.png
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from BlackjackRL import (
    QTable, _train_worker, _load_strategy_csv,
    _strategy_folder, _rule_prefix, _N_ACTIONS,
    _upcard_weights, _sample_hand, _run_episode,
)
from Simulator.BlackjackSimulator import BlackjackSimulator, DealerSettingsObject


# 1210 = 180*3 (hard) + 90*3 (soft) + 100*4 (pairs)
MC_TO_RL_SCALE  = 1210
MC_ITER_COUNTS  = [100, 1_000, 10_000, 100_000]
RL_EPISODE_COUNTS = [mc * MC_TO_RL_SCALE for mc in MC_ITER_COUNTS]


# ---------------------------------------------------------------------------
# Error counting
# ---------------------------------------------------------------------------

def _count_errors(q: QTable, folder: Path, das: bool) -> int:
    strat     = q.to_strategy_dicts()
    upcards   = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
    up_labels = ["2","3","4","5","6","7","8","9","10","A"]
    pair_ranks  = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    pair_labels = ["10","9","8","7","6","5","4","3","2","A"]

    table_map = {
        "Hard":  (list(range(21,3,-1)),  [str(t) for t in range(21,3,-1)],  "hard",  None),
        "Soft":  (list(range(21,12,-1)), [str(t) for t in range(21,12,-1)], "soft",  None),
        "Pairs": (pair_ranks,            pair_labels,                        "pairs", das),
    }

    total_wrong = 0
    for csv_name, (keys, key_labels, strat_key, das_flag) in table_map.items():
        verified_df = _load_strategy_csv(folder, csv_name, das=das_flag)
        if verified_df is None:
            continue
        v_lookup = {str(i).strip(): i for i in verified_df.index}
        for k, kl in zip(keys, key_labels):
            key = str(kl).strip()
            if key not in v_lookup:
                continue
            v_hand = v_lookup[key]
            for uc, ul in zip(upcards, up_labels):
                rl_val  = strat[strat_key].get(k, {}).get(ul, "H").strip().upper()
                ver_val = str(verified_df.loc[v_hand, ul]).strip().upper() if ul in verified_df.columns else "H"
                if rl_val != ver_val:
                    total_wrong += 1
    return total_wrong


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--decks",        type=int,   default=6)
    parser.add_argument("--s17",          action="store_true", default=False)
    parser.add_argument("--h17",          dest="s17", action="store_false")  # default
    parser.add_argument("--enhc",         action="store_true", default=False)
    parser.add_argument("--das",          action="store_true", default=True)
    parser.add_argument("--ndas",         dest="das", action="store_false")
    parser.add_argument("--bj-pay",       type=float, default=1.5)
    parser.add_argument("--matrices-dir", dest="matrices_dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", "VerifiedStrategyMatrices"))
    parser.add_argument("--output", default=os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "rl_convergence_plot.png"))
    args = parser.parse_args()

    rules = DealerSettingsObject(
        decks=args.decks, S17=args.s17, ENHC=args.enhc,
        DAS=args.das, BJPay=args.bj_pay,
    )
    folder = _strategy_folder(args.matrices_dir, args.decks, args.s17, args.enhc, args.das)
    # Verified CSVs live one level up — no DAS/NDAS subfolder
    verified_folder = (Path(args.matrices_dir)
                       / ("1D" if args.decks == 1 else ("2D" if args.decks == 2 else "MD"))
                       / ("S17" if args.s17 else "H17")
                       / ("ENHC" if args.enhc else "US"))

    print(f"Settings: {args.decks}D  {'S17' if args.s17 else 'H17'}  "
          f"{'ENHC' if args.enhc else 'US'}  {'DAS' if args.das else 'nDAS'}")
    print(f"Scale   : 1 MC iteration = {MC_TO_RL_SCALE} RL episodes")
    print(f"Testing {len(RL_EPISODE_COUNTS)} episode counts (single worker, no averaging)\n")

    error_counts = []
    iter_times   = []
    total_start  = time.time()

    for mc_iters, rl_eps in zip(MC_ITER_COUNTS, RL_EPISODE_COUNTS):
        iter_start = time.time()
        print(f"── {rl_eps:>12,} episodes  (≡ {mc_iters:>8,} MC iters) ──────────────", flush=True)

        sim = BlackjackSimulator(rules)
        q   = QTable(das=rules.DAS)
        upcard_weights = _upcard_weights(rules.decks)
        hard_dbl, soft_dbl, _, _ = q.get_strategy_arrays()
        rebuild_every = 10_000
        log_every     = max(1, rl_eps // 10)
        from BlackjackRL import _sample_upcard

        for ep in range(1, rl_eps + 1):
            epsilon = 0.1  + (0.01  - 0.1)  * ep / rl_eps
            alpha   = 0.1  + (0.001 - 0.1)  * ep / rl_eps
            upcard  = _sample_upcard(upcard_weights)
            hand    = _sample_hand(rules.decks, upcard)
            _run_episode(sim, q, upcard, hand, epsilon, alpha, hard_dbl, soft_dbl)
            if ep % rebuild_every == 0:
                hard_dbl, soft_dbl, _, _ = q.get_strategy_arrays()
            if ep % log_every == 0:
                pct = 100 * ep // rl_eps
                print(f"  {ep:>12,} / {rl_eps:,}  ({pct:3d}%)  "
                      f"eps={epsilon:.3f}  alpha={alpha:.4f}", flush=True)

        errors  = _count_errors(q, verified_folder, args.das)
        elapsed = time.time() - iter_start
        error_counts.append(errors)
        iter_times.append(elapsed)
        eps_per_sec = rl_eps / elapsed if elapsed > 0 else 0
        print(f"  → {errors} incorrect decisions  ({elapsed:.1f}s  |  {eps_per_sec:,.0f} eps/sec  |  {mc_iters:,} equiv MC iters)\n", flush=True)

    total_elapsed = time.time() - total_start
    print(f"Total time: {total_elapsed:.1f}s  ({total_elapsed/60:.1f} min)\n")

    print("Summary:")
    print(f"  {'MC equiv':<12}  {'Episodes':>14}  {'Errors':>6}  {'Time':>8}")
    print("  " + "-" * 46)
    for mc, ep, er, tm in zip(MC_ITER_COUNTS, RL_EPISODE_COUNTS, error_counts, iter_times):
        print(f"  {mc:<12,}  {ep:>14,}  {er:>6}  {tm:>7.1f}s")
    print(f"  {'TOTAL':<12}  {'':>14}  {'':>6}  {total_elapsed:>7.1f}s")

    # ---------------------------------------------------------------------------
    # Plot
    # ---------------------------------------------------------------------------
    print("\nGenerating plot...")

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d27")

    x = np.array(MC_ITER_COUNTS)

    ax.plot(x, error_counts,
            color="#4FC3F7", linewidth=2.5,
            marker="o", markersize=8,
            markerfacecolor="#4FC3F7", markeredgecolor="#0f1117", markeredgewidth=1.5,
            label="Reinforcement Learning", zorder=3)

    ax.fill_between(x, error_counts, alpha=0.12, color="#4FC3F7")

    for xi, yi in zip(x, error_counts):
        ax.annotate(str(yi),
                    xy=(xi, yi),
                    xytext=(0, 12), textcoords="offset points",
                    ha="center", fontsize=11, color="#4FC3F7")

    ax.set_xscale("log")
    ax.set_xlabel("Equivalent iterations per cell", fontsize=13, color="#cccccc", labelpad=10)
    ax.set_ylabel("Incorrect Decisions", fontsize=13, color="#cccccc", labelpad=10)

    rule_str = (f"{args.decks}D  {'S17' if args.s17 else 'H17'}  "
                f"{'ENHC' if args.enhc else 'US'}  {'DAS' if args.das else 'nDAS'}")
    ax.set_title(f"Reinforcement Learning Convergence\n{rule_str}",
                 fontsize=15, color="#ffffff", pad=18, fontweight="bold")

    # 121000, 1210000, 12100000, 121000000
    tick_labels = ["121K", "1.210M", "12.1M", "121M"]
    completed = MC_ITER_COUNTS[:len(error_counts)]
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

    print(f"Plot saved -> {args.output}")


if __name__ == "__main__":
    main()