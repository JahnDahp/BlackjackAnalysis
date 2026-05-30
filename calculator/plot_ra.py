# Run with: python plot_ra.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas] [--surrender|--no-surrender] [--bet N]

from __future__ import annotations
import argparse
import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game import compute_game_ev, get_dataset, load_json

RA_VALUES = [round(i * 0.01, 2) for i in range(26)]
HANDS_HOUR = 100



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--decks", type=int, default=6, choices=[1, 2, 4, 6, 8])
  s17_group = parser.add_mutually_exclusive_group()
  s17_group.add_argument("--s17", dest="s17", action="store_true", default=True)
  s17_group.add_argument("--h17", dest="s17", action="store_false")
  enhc_group = parser.add_mutually_exclusive_group()
  enhc_group.add_argument("--us", dest="enhc", action="store_false", default=False)
  enhc_group.add_argument("--enhc", dest="enhc", action="store_true")
  das_group = parser.add_mutually_exclusive_group()
  das_group.add_argument("--das", dest="das", action="store_true", default=True)
  das_group.add_argument("--ndas", dest="das", action="store_false")
  surr_group = parser.add_mutually_exclusive_group()
  surr_group.add_argument("--surrender", dest="surrender", action="store_true", default=True)
  surr_group.add_argument("--no-surrender", dest="surrender", action="store_false")
  parser.add_argument("--bet", type=float, default=25.0)
  args = parser.parse_args()

  stand_dataset = get_dataset(load_json("stand.json"), "probs", args.decks, args.s17, args.enhc)
  hit_dataset = get_dataset(load_json("hit.json"), "probs", args.decks, args.s17, args.enhc)
  double_dataset = get_dataset(load_json("double.json"), "probs", args.decks, args.s17, args.enhc)
  split_data = get_dataset(load_json("split.json"), "probs", args.decks, args.s17, args.enhc)
  split_das_dataset = split_data["DAS"]
  split_ndas_dataset = split_data["nDAS"]

  new_counts = 52 * args.decks
  prob_dealer_bj = ((4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) +
    (16*args.decks/new_counts)*(4*args.decks/(new_counts-1))) if not args.enhc else 0.0
  prob_player_bj = ((4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) +
    (16*args.decks/new_counts)*(4*args.decks/(new_counts-1)))
  prob_dealer_bj_given_player_bj = (
    ((4*args.decks-1)/(new_counts-2))*((16*args.decks-1)/(new_counts-3)) +
    ((16*args.decks-1)/(new_counts-2))*((4*args.decks-1)/(new_counts-3)))
  prob_dealer_bj_no_player = prob_dealer_bj - prob_player_bj * prob_dealer_bj_given_player_bj

  rule_str = (f"{args.decks}D {'S17' if args.s17 else 'H17'} "
              f"{'ENHC' if args.enhc else 'US'} {'DAS' if args.das else 'nDAS'} {'LS' if args.surrender else 'nLS'}")
  print(f"Settings: {rule_str}, ${args.bet:.0f} flat bet")
  print(f"Computing EV/hour for {len(RA_VALUES)} risk-aversion values...\n")

  sd_hours = []
  ev_hours = []

  for risk_aversion in RA_VALUES:
    decision_ev, _, sum_second_moment = compute_game_ev(
      stand_dataset, hit_dataset, double_dataset, split_das_dataset, split_ndas_dataset,
      das=args.das, surrender=args.surrender, decks=args.decks, enhc=args.enhc, risk_aversion=risk_aversion,
    )
    dealer_bj_ev = prob_dealer_bj_no_player * -1.0 if not args.enhc else 0.0
    total_ev = decision_ev + dealer_bj_ev
    second_moment_total = sum_second_moment + (prob_dealer_bj_no_player if not args.enhc else 0.0)
    variance = max(0.0, second_moment_total - total_ev ** 2)
    sd_hour = (variance ** 0.5) * args.bet * (HANDS_HOUR ** 0.5)
    ev_hour = total_ev * args.bet * HANDS_HOUR
    sd_hours.append(sd_hour)
    ev_hours.append(ev_hour)
    print(f" RA={risk_aversion:<5} EV/hour = ${ev_hour:+.2f}  SD/hour = ${sd_hour:.2f}  range = [${ev_hour-sd_hour:+.2f}, ${ev_hour+sd_hour:+.2f}]")

  ra_array = np.array(RA_VALUES, dtype=float)
  ev_array = np.array(ev_hours)
  sd_array = np.array(sd_hours)

  output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ra_ev_plot.png")

  figure, axes = plt.subplots()
  axes.plot(ra_array, ev_array + sd_array, label="EV + 1 SD")
  axes.plot(ra_array, ev_array, label="EV/hour")
  axes.plot(ra_array, ev_array - sd_array, label="EV - 1 SD")
  axes.axhline(0, color="black", linewidth=0.8, linestyle=":")
  axes.set_xlabel("RA")
  axes.set_ylabel("$/hour")
  axes.set_title(f"{rule_str}, ${args.bet:.0f} flat, {HANDS_HOUR} hands/hr")
  axes.legend()
  plt.tight_layout()
  plt.savefig(output, dpi=150)
  plt.close()

  print(f"\nPlot saved -> {output}")



if __name__ == "__main__":
  main()
