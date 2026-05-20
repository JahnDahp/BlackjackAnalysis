"""
plot_convergence.py

Runs the Q-learning agent at checkpoints and plots number of incorrect
decisions vs. episodes, with a horizontal dashed line for Monte Carlo's result.

Usage:
    python plot_convergence.py [--decks 1] [--s17] [--das] [--mc-errors 2]
                               [--total-episodes 100000000] [--checkpoints 20]
                               [--workers 8] [--matrices-dir ../VerifiedStrategyMatrices]

The script trains the RL agent in stages (checkpoints), evaluates accuracy at
each stage against the verified strategy CSVs, then plots the convergence curve.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

from BlackjackSimulator import BlackjackSimulator, DealerSettingsObject, _STAND, _HIT, _DOUBLE, _SPLIT, _NONE
from BlackjackRL import (
    QTable, _train_worker, _average_qtables, _strategy_folder,
    _load_strategy_csv, _N_ACTIONS, ACTION_NAMES,
)


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------

def _count_errors(q: QTable, folder: Path, das: bool) -> int:
    """Count decisions that differ from verified CSVs."""
    strat = q.to_strategy_dicts()
    upcards   = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
    up_labels = ["2","3","4","5","6","7","8","9","10","A"]

    pair_ranks  = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    pair_labels = ["10","9","8","7","6","5","4","3","2","A"]

    pairs_label = "DAS" if das else "NDAS"
    table_map = {
        "Hard":              (list(range(21,3,-1)),  [str(t) for t in range(21,3,-1)],  "hard",  None),
        "Soft":              (list(range(21,12,-1)), [str(t) for t in range(21,12,-1)], "soft",  None),
        f"Pairs_{pairs_label}": (pair_ranks, pair_labels, "pairs", das),
    }

    total_wrong = 0
    for csv_name, (keys, key_labels, strat_key, das_flag) in table_map.items():
        verified_df = _load_strategy_csv(folder, csv_name.replace(f"_DAS","").replace(f"_NDAS","") if "Pairs" in csv_name else csv_name, das=das_flag)
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

def main():
    import multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Plot RL convergence curve vs Monte Carlo baseline.")
    parser.add_argument("--decks",           type=int,   default=1)
    parser.add_argument("--s17",             action="store_true", default=True)
    parser.add_argument("--h17",             dest="s17", action="store_false")
    parser.add_argument("--enhc",            action="store_true", default=False)
    parser.add_argument("--das",             action="store_true", default=True)
    parser.add_argument("--ndas",            dest="das", action="store_false")
    parser.add_argument("--bj-pay",          type=float, default=1.5)

    parser.add_argument("--total-episodes",  type=int,   default=100_000_000)
    parser.add_argument("--checkpoints",     type=int,   default=20,
                        help="Number of evaluation checkpoints")
    parser.add_argument("--workers",         type=int,   default=None)
    parser.add_argument("--matrices-dir",    dest="matrices_dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", "VerifiedStrategyMatrices"))
    parser.add_argument("--output",          default=os.path.join(
                            os.path.dirname(os.path.abspath(__file__)), "convergence_plot.png"))
    args = parser.parse_args()

    rules = DealerSettingsObject(
        decks=args.decks, S17=args.s17, ENHC=args.enhc,
        DAS=args.das, BJPay=args.bj_pay,
    )

    folder = _strategy_folder(args.matrices_dir, args.decks, args.s17, args.enhc, args.das)

    import multiprocessing as mp
    cpu = mp.cpu_count() or 1
    n_workers = min(args.workers if args.workers else max(1, cpu - 4), 20)
    print(f"Detected {cpu} CPUs, using {n_workers} workers.")
    print(f"Total episodes: {args.total_episodes:,} across {args.checkpoints} checkpoints.\n")

    episodes_per_checkpoint = args.total_episodes // args.checkpoints
    epsilon_start, epsilon_end = 1.0, 0.01
    alpha_start,   alpha_end   = 0.1, 0.001

    episode_counts = []
    error_counts   = []

    # Accumulate a single Q-table across checkpoints by training cumulatively
    # (train checkpoint-by-checkpoint, evaluating after each)
    cumulative_episodes = 0
    q_accumulated = QTable(das=args.das)

    for ck in range(1, args.checkpoints + 1):
        ck_episodes = episodes_per_checkpoint
        ep_start    = cumulative_episodes
        ep_end      = cumulative_episodes + ck_episodes
        total       = args.total_episodes

        # epsilon and alpha for this window
        eps_s = epsilon_start + (epsilon_end - epsilon_start) * ep_start / total
        eps_e = epsilon_start + (epsilon_end - epsilon_start) * ep_end   / total
        alp_s = alpha_start   + (alpha_end   - alpha_start)   * ep_start / total
        alp_e = alpha_start   + (alpha_end   - alpha_start)   * ep_end   / total

        eps_per_worker = ck_episodes // n_workers
        worker_args = [
            (rules, eps_per_worker, eps_s, eps_e, alp_s, alp_e, i)
            for i in range(n_workers)
        ]

        with mp.Pool(processes=n_workers) as pool:
            results = pool.map(_train_worker, worker_args)

        # Merge this checkpoint's results into accumulated Q-table
        ck_q = _average_qtables(results, args.das)

        # Blend: running average weighted by episode count
        w_old = cumulative_episodes / (ep_end if ep_end > 0 else 1)
        w_new = ck_episodes         / (ep_end if ep_end > 0 else 1)
        for row_i in range(18):
            for col_i in range(10):
                for a in range(_N_ACTIONS):
                    q_accumulated.hard[row_i][col_i][a] = (
                        q_accumulated.hard[row_i][col_i][a] * w_old +
                        ck_q.hard[row_i][col_i][a] * w_new
                    )
        for row_i in range(9):
            for col_i in range(10):
                for a in range(_N_ACTIONS):
                    q_accumulated.soft[row_i][col_i][a] = (
                        q_accumulated.soft[row_i][col_i][a] * w_old +
                        ck_q.soft[row_i][col_i][a] * w_new
                    )
        for row_i in range(10):
            for col_i in range(10):
                for a in range(_N_ACTIONS):
                    q_accumulated.pairs[row_i][col_i][a] = (
                        q_accumulated.pairs[row_i][col_i][a] * w_old +
                        ck_q.pairs[row_i][col_i][a] * w_new
                    )
        q_accumulated._dirty = True

        cumulative_episodes = ep_end
        errors = _count_errors(q_accumulated, folder, args.das)
        episode_counts.append(cumulative_episodes)
        error_counts.append(errors)

        print(f"  Checkpoint {ck:>2}/{args.checkpoints}  "
              f"episodes={cumulative_episodes:>12,}  errors={errors}", flush=True)

    # ---------------------------------------------------------------------------
    # Plot
    # ---------------------------------------------------------------------------
    print("\nGenerating plot...")

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d27")

    x = np.array(episode_counts) / 1_000_000  # millions

    # RL convergence line
    ax.plot(x, error_counts,
            color="#4FC3F7", linewidth=2.5, marker="o", markersize=5,
            markerfacecolor="#4FC3F7", markeredgecolor="#0f1117", markeredgewidth=1,
            label="Q-Learning (RL) — incorrect decisions", zorder=3)

    # Fill under RL line
    ax.fill_between(x, error_counts, alpha=0.12, color="#4FC3F7")

    final_err = error_counts[-1]
    ax.annotate(f"RL final: {final_err} errors",
                xy=(x[-1], final_err),
                xytext=(-10, -18), textcoords="offset points",
                color="#4FC3F7", fontsize=11, ha="right",
                arrowprops=dict(arrowstyle="-", color="#4FC3F7", lw=1))

    # Styling
    ax.set_xlabel("Training Episodes (millions)", fontsize=13, color="#cccccc", labelpad=10)
    ax.set_ylabel("Incorrect Decisions", fontsize=13, color="#cccccc", labelpad=10)
    ax.set_title("Q-Learning Convergence vs. Monte Carlo Baseline\nBlackjack Basic Strategy (1D S17 US DAS)",
                 fontsize=15, color="#ffffff", pad=18, fontweight="bold")

    ax.tick_params(colors="#888888", labelsize=11)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333344")

    ax.grid(True, color="#252535", linewidth=0.8, alpha=0.8)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    legend = ax.legend(fontsize=12, framealpha=0.25, facecolor="#1a1d27",
                       edgecolor="#444455", labelcolor="#dddddd",
                       loc="upper right")

    # Episode count on top x-axis
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xlabel("", color="#888888")
    ax2.tick_params(colors="#555566", labelsize=9)
    ax2.set_facecolor("#1a1d27")

    plt.tight_layout()
    plt.savefig(args.output, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()

    print(f"\nPlot saved -> {args.output}")


if __name__ == "__main__":
    main()