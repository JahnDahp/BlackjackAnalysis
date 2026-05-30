# Run with: python game.py [--decks N] [--s17|--h17] [--enhc|--us] [--das|--ndas] [--surrender|--no-surrender] [--ra N] [--bet N]

import argparse
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")



def load_json(filename):
  path = os.path.join(DATA_DIR, filename)
  if not os.path.exists(path):
    raise FileNotFoundError(f"ERROR: {path} not found.")
  with open(path) as f:
    return json.load(f)

def deck_key(decks):
  return {1: "oneDeck", 2: "twoDeck", 4: "fourDeck", 6: "sixDeck", 8: "eightDeck"}[decks]

def get_dataset(data, key, decks, s17, enhc):
  return data[key][deck_key(decks)]["S17" if s17 else "H17"]["enhc" if enhc else "us"]



RESET = "\033[0m"; BOLD = "\033[1m"; RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
ORANGE = "\033[38;5;208m"; CYAN = "\033[96m"; TEAL = "\033[38;5;37m"; WHITE = "\033[97m"; DIM = "\033[2m"; MAGENTA = "\033[38;5;90m"
DECISION_COLOUR = {"H": RED, "S": GREEN, "Dh": YELLOW, "Ds": ORANGE, "P": CYAN, "P?": TEAL}

def colored(text, code):
  color = MAGENTA if code.startswith("R") else DECISION_COLOUR.get(code, WHITE)
  return f"{color}{BOLD}{text}{RESET}"



def ev_from_probabilities(probs):
  return probs["winProb"] - probs["loseProb"] - probs["DBJ"]

def stand_ev(probs, hand):
  if len(hand) == 2 and hand_total(hand) == 21:
    return (1 - probs["DBJ"]) * 1.5
  return ev_from_probabilities(probs)

def hit_ev(probs):
  return ev_from_probabilities(probs)

def double_ev(probs):
  return 2.0 * ev_from_probabilities(probs)

def split_ev(probs, das=False):
  win_dbl=probs["double"]["winProb"]; tie_dbl=probs["double"]["tieProb"]; lose_dbl=probs["double"]["loseProb"]; dbj_dbl=probs["double"]["DBJ"]
  win=probs["noDouble"]["winProb"]; tie=probs["noDouble"]["tieProb"]; lose=probs["noDouble"]["loseProb"]; dbj=probs["noDouble"]["DBJ"]
  if das:
    win4=win_dbl**2; win3=2*win_dbl*win; win2=2*win_dbl*(tie+tie_dbl)+win**2; win1=2*win_dbl*lose+2*win*(tie+tie_dbl)
    lose1=2*lose_dbl*win+2*lose*(tie+tie_dbl); lose2=2*lose_dbl*(tie+tie_dbl)+lose**2; lose3=2*lose_dbl*lose; lose4=lose_dbl**2
    return 4*win4+3*win3+2*win2+win1-2*dbj-4*dbj_dbl-lose1-2*lose2-3*lose3-4*lose4
  return 2*win**2+2*win*tie-2*dbj-2*lose*tie-2*lose**2



def stand_second_moment(probs, hand):
  if len(hand) == 2 and hand_total(hand) == 21:
    return 2.25 * (1.0 - probs["DBJ"])
  return 1.0 - probs["tieProb"]

def hit_second_moment(probs):
  return 1.0 - probs["tieProb"]

def double_second_moment(probs):
  return 4.0 * (1.0 - probs["tieProb"])

def split_second_moment(probs, das=False):
  win=probs["noDouble"]["winProb"]; tie=probs["noDouble"]["tieProb"]; lose=probs["noDouble"]["loseProb"]
  win_dbl=probs["double"]["winProb"]; tie_dbl=probs["double"]["tieProb"]; lose_dbl=probs["double"]["loseProb"]
  if das:
    win4=win_dbl**2; win3=2*win_dbl*win; win2=2*win_dbl*(tie+tie_dbl)+win**2
    tie_var=2*win_dbl*lose_dbl+2*win*lose+(tie+tie_dbl)**2
    lose2=2*lose_dbl*(tie+tie_dbl)+lose**2; lose3=2*lose_dbl*lose; lose4=lose_dbl**2
    return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie_var
  return 1 + 3*(win**2+lose**2) - (2*win*lose + tie**2)

def surrender_second_moment(upcard_index, enhc, decks):
  new_counts = 52 * decks
  prob_bj_factor = ((16*decks)/(new_counts-1) if upcard_index==0 else (4*decks)/(new_counts-1) if upcard_index==9 else 0.0) if enhc else 0.0
  return (1-prob_bj_factor)*0.25 + prob_bj_factor*1.0



def hand_total(hand):
  total = 0; aces = 0
  for card in hand:
    if card == 1: total += 11; aces += 1
    else: total += card
  while total > 21 and aces: total -= 10; aces -= 1
  return total

def is_soft(hand):
  total = 0; aces = 0
  for card in hand:
    if card == 1: total += 11; aces += 1
    else: total += card
  while total > 21 and aces: total -= 10; aces -= 1
  return aces > 0

def hand_key(hand):
  return tuple(sorted(hand))

def surrender_ev(upcard_index, enhc, decks):
  if not enhc:
    return -0.5
  new_counts = 52 * decks
  if upcard_index == 0: return -0.5 - 0.5 * (16 * decks) / (new_counts - 1)
  if upcard_index == 9: return -0.5 - 0.5 * (4 * decks) / (new_counts - 1)
  return -0.5

def certainty_equiv(ev, second_moment, risk_aversion):
  return ev - (risk_aversion / 2.0) * (second_moment - ev ** 2)



def best_non_split_action(ev_variance, surrender=False, surr_ev=-0.5, surr_second_moment=0.25, risk_aversion=0.0):
  if not ev_variance: return "S"
  best_action = None
  best_certainty_equiv = float('-inf')
  for action, (ev, second_moment) in ev_variance.items():
    ce_value = certainty_equiv(ev, second_moment, risk_aversion)
    if ce_value > best_certainty_equiv: best_certainty_equiv = ce_value; best_action = action
  surrender_ce = certainty_equiv(surr_ev, surr_second_moment, risk_aversion)
  if surrender and surrender_ce > best_certainty_equiv:
    return "R" + best_action
  return best_action



def build_ev_variance_table(stand_dataset, hit_dataset, double_dataset, is_soft_table):
  def hand_key_local(hand_cards): return tuple(sorted(hand_cards))

  accumulator = {}
  key = "soft" if is_soft_table else "hard"

  for upcard_index in range(10):
    stand_map = {}; hit_map = {}; double_map = {}
    for row in stand_dataset[key][upcard_index]: stand_map[hand_key_local(row[0])] = (row[1], row[2])
    for row in hit_dataset[key][upcard_index]: hit_map[hand_key_local(row[0])] = (row[1], row[2])
    for row in double_dataset[key][upcard_index]: double_map[hand_key_local(row[0])] = (row[1], row[2])

    for hand in set(stand_map) | set(hit_map) | set(double_map):
      if is_soft_table != is_soft(hand): continue
      if len(hand) != 2: continue
      total = hand_total(hand)
      cell_key = (upcard_index, total)
      if cell_key not in accumulator: accumulator[cell_key] = {}

      if hand in stand_map:
        prob, row = stand_map[hand]
        ev_value = stand_ev(row, hand)
        second_moment_value = stand_second_moment(row, hand)
        cell = accumulator[cell_key].setdefault("S", [0.0, 0.0, 0.0])
        cell[0] += ev_value * prob; cell[1] += second_moment_value * prob; cell[2] += prob

      if hand in hit_map:
        prob, row = hit_map[hand]
        ev_value = hit_ev(row)
        second_moment_value = hit_second_moment(row)
        cell = accumulator[cell_key].setdefault("H", [0.0, 0.0, 0.0])
        cell[0] += ev_value * prob; cell[1] += second_moment_value * prob; cell[2] += prob

      if hand in double_map:
        prob, row = double_map[hand]
        ev_value = double_ev(row)
        second_moment_value = double_second_moment(row)
        hit_ev_value = hit_ev(hit_map[hand][1]) if hand in hit_map else -999.0
        stand_ev_value = stand_ev(stand_map[hand][1], hand) if hand in stand_map else -999.0
        double_key = "Dh" if hit_ev_value > stand_ev_value else "Ds"
        cell = accumulator[cell_key].setdefault(double_key, [0.0, 0.0, 0.0])
        cell[0] += ev_value * prob; cell[1] += second_moment_value * prob; cell[2] += prob

  result = {}
  for cell_key, decisions in accumulator.items():
    result[cell_key] = {}
    for action, (sum_ev, sum_second_moment, sum_prob) in decisions.items():
      if sum_prob > 0:
        result[cell_key][action] = (sum_ev / sum_prob, sum_second_moment / sum_prob)
  return result



def split_decision_chart(split_dataset_das, split_dataset_ndas, stand_dataset, hit_dataset,
                          double_dataset, pair_val, upcard_index, surrender=False, risk_aversion=0.0):
  def get_split_ev_and_second_moment(dataset, das=False):
    for row in dataset[upcard_index]:
      if row[0][0] == pair_val:
        return split_ev(row[1], das), split_second_moment(row[1], das)
    return None, None

  das_split_ev, das_split_second_moment = get_split_ev_and_second_moment(split_dataset_das, das=True)
  ndas_split_ev, ndas_split_second_moment = get_split_ev_and_second_moment(split_dataset_ndas, das=False)

  pair_hand = (pair_val, pair_val)
  key_type = "soft" if is_soft(pair_hand) else "hard"
  non_split_ev_variance = {}

  for label, dataset in (("S", stand_dataset), ("H", hit_dataset)):
    for row in dataset[key_type][upcard_index]:
      if hand_key(row[0]) == pair_hand:
        if label == "S":
          non_split_ev_variance["S"] = (stand_ev(row[2], pair_hand), stand_second_moment(row[2], pair_hand))
        else:
          non_split_ev_variance["H"] = (hit_ev(row[2]), hit_second_moment(row[2]))
        break
  for row in double_dataset[key_type][upcard_index]:
    if hand_key(row[0]) == pair_hand:
      hit_ev_value = non_split_ev_variance["H"][0] if "H" in non_split_ev_variance else -999.0
      stand_ev_value = non_split_ev_variance["S"][0] if "S" in non_split_ev_variance else -999.0
      double_key = "Dh" if hit_ev_value > stand_ev_value else "Ds"
      non_split_ev_variance[double_key] = (double_ev(row[2]), double_second_moment(row[2]))
      break

  best_non_split_code = best_non_split_action(non_split_ev_variance, risk_aversion=risk_aversion)
  best_non_split_ev_value = non_split_ev_variance[best_non_split_code][0] if best_non_split_code in non_split_ev_variance else 0.0
  best_non_split_second_moment = non_split_ev_variance[best_non_split_code][1] if best_non_split_code in non_split_ev_variance else 1.0
  best_non_split_ce = certainty_equiv(best_non_split_ev_value, best_non_split_second_moment, risk_aversion)

  das_ce = certainty_equiv(das_split_ev, das_split_second_moment, risk_aversion) if das_split_ev is not None else None
  ndas_ce = certainty_equiv(ndas_split_ev, ndas_split_second_moment, risk_aversion) if ndas_split_ev is not None else None

  das_better = das_ce is not None and das_ce > best_non_split_ce
  ndas_better = ndas_ce is not None and ndas_ce > best_non_split_ce

  surrender_ce = certainty_equiv(-0.5, 0.25, risk_aversion)

  if das_better and ndas_better:
    return "RP" if (surrender and surrender_ce > das_ce) else "P"
  elif das_better:
    return "RP?" if (surrender and surrender_ce > das_ce) else "P?"
  else:
    if surrender and surrender_ce > best_non_split_ce:
      return "R" + best_non_split_code
    return best_non_split_code



UPCARD_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
UPCARD_LABELS = ["2","3","4","5","6","7","8","9","10","A"]

def pad(text, width):
  visible = len(text.replace(RESET,"").replace(BOLD,"").replace(RED,"").replace(GREEN,"")
               .replace(YELLOW,"").replace(ORANGE,"").replace(CYAN,"").replace(TEAL,"")
               .replace(WHITE,"").replace(DIM,"").replace(MAGENTA,""))
  padding = max(0, width - visible)
  return " " * (padding // 2) + text + " " * (padding - padding // 2)

def print_table(title, row_labels, rows):
  col_width, row_label_width = 6, 6
  separator = DIM + "─" * (row_label_width + 1 + (col_width + 1) * len(UPCARD_LABELS)) + RESET
  print(f"\n{BOLD}{WHITE}{title}{RESET}")
  print(separator)
  print(f"{'':>{row_label_width}} │" + "│".join(pad(label, col_width) for label in UPCARD_LABELS))
  print(separator)
  for label, row in zip(row_labels, rows):
    print(f"{label:>{row_label_width}} │" + "│".join(pad(colored(code, code), col_width) for code in row))
  print(separator)

def print_legend():
  items = [
    ("H", "Hit"),
    ("S", "Stand"),
    ("Dh", "Double, else Hit"),
    ("Ds", "Double, else Stand"),
    ("P", "Split"),
    ("P?", "Split if DAS only"),
    ("RH", "Surrender, else Hit"),
    ("RS", "Surrender, else Stand"),
  ]
  print(f"\n{BOLD}Legend{RESET}")
  for code, desc in items:
    print(f" {colored(code, code)}{' ' * (8 - len(code))} {desc}")



def build_strategy_matrix(stand_dataset, hit_dataset, double_dataset, split_das_dataset, split_ndas_dataset,
                           das=True, surrender=False, enhc=False, decks=6, risk_aversion=0.0):
  hard_ev_variance = build_ev_variance_table(stand_dataset, hit_dataset, double_dataset, False)
  soft_ev_variance = build_ev_variance_table(stand_dataset, hit_dataset, double_dataset, True)

  hard_matrix = {}
  soft_matrix = {}
  for (upcard_index, total), ev_variance in hard_ev_variance.items():
    surrender_ev_value = surrender_ev(upcard_index, enhc, decks)
    surrender_second_moment_value = surrender_second_moment(upcard_index, enhc, decks)
    hard_matrix[(upcard_index, total)] = best_non_split_action(
      ev_variance, surrender, surrender_ev_value, surrender_second_moment_value, risk_aversion)
  for (upcard_index, total), ev_variance in soft_ev_variance.items():
    surrender_ev_value = surrender_ev(upcard_index, enhc, decks)
    surrender_second_moment_value = surrender_second_moment(upcard_index, enhc, decks)
    soft_matrix[(upcard_index, total)] = best_non_split_action(
      ev_variance, surrender, surrender_ev_value, surrender_second_moment_value, risk_aversion)

  def build_split_lookup(dataset):
    lookup = {}
    for upcard_index, rows in enumerate(dataset):
      for row in rows: lookup[(hand_key(row[0]), upcard_index)] = row[1]
    return lookup

  split_das_lookup = build_split_lookup(split_das_dataset)
  split_ndas_lookup = build_split_lookup(split_ndas_dataset)

  pair_matrix = {}
  for pair_val in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    pair_hand_key = hand_key([pair_val, pair_val])
    for upcard_index in range(10):
      surrender_ev_value = surrender_ev(upcard_index, enhc, decks)
      surrender_second_moment_value = surrender_second_moment(upcard_index, enhc, decks)
      total = hand_total(list(pair_hand_key))
      ev_variance = (soft_ev_variance if is_soft(list(pair_hand_key)) else hard_ev_variance).get((upcard_index, total), {})
      best_non_split = best_non_split_action(ev_variance, surrender, surrender_ev_value, surrender_second_moment_value, risk_aversion)
      if best_non_split.startswith("R"):
        best_non_split_ce = certainty_equiv(surrender_ev_value, surrender_second_moment_value, risk_aversion)
      else:
        non_split_ev, non_split_second_moment = ev_variance.get(best_non_split, (surrender_ev_value, surrender_second_moment_value))
        best_non_split_ce = certainty_equiv(non_split_ev, non_split_second_moment, risk_aversion)

      split_lookup = split_das_lookup if das else split_ndas_lookup
      if (pair_hand_key, upcard_index) in split_lookup:
        split_ev_value = split_ev(split_lookup[(pair_hand_key, upcard_index)], das=das)
        split_second_moment_value = split_second_moment(split_lookup[(pair_hand_key, upcard_index)], das=das)
        split_ce = certainty_equiv(split_ev_value, split_second_moment_value, risk_aversion)
        if split_ce > best_non_split_ce:
          code = "RP" if (surrender and certainty_equiv(surrender_ev_value, surrender_second_moment_value, risk_aversion) > split_ce) else "P"
        else:
          code = best_non_split
      else:
        code = best_non_split
      pair_matrix[(upcard_index, pair_val)] = code

  return hard_matrix, soft_matrix, pair_matrix



def ev_for_code(code, hand, upcard_index, stand_lookup, hit_lookup, double_lookup,
                split_das_lookup, split_ndas_lookup, das, enhc=False, decks=6):
  hand_tuple = hand_key(hand)
  if code == "P":
    lookup = split_das_lookup if das else split_ndas_lookup
    if (hand_tuple, upcard_index) in lookup: return split_ev(lookup[(hand_tuple, upcard_index)], das=das)
  if code.startswith("R"):
    return surrender_ev(upcard_index, enhc, decks)
  if code in ("Dh", "Ds"):
    if (hand_tuple, upcard_index) in double_lookup: return double_ev(double_lookup[(hand_tuple, upcard_index)][1])
    action = "H" if code == "Dh" else "S"
  else:
    action = code
  if action == "S" and (hand_tuple, upcard_index) in stand_lookup: return stand_ev(stand_lookup[(hand_tuple, upcard_index)][1], hand)
  if action == "H" and (hand_tuple, upcard_index) in hit_lookup: return hit_ev(hit_lookup[(hand_tuple, upcard_index)][1])
  return None

def second_moment_for_code(code, hand, upcard_index, stand_lookup, hit_lookup, double_lookup,
                            split_das_lookup, split_ndas_lookup, das, enhc, decks):
  hand_tuple = hand_key(hand)
  if code.startswith("R"):
    return surrender_second_moment(upcard_index, enhc, decks)
  if code == "P":
    lookup = split_das_lookup if das else split_ndas_lookup
    if (hand_tuple, upcard_index) in lookup: return split_second_moment(lookup[(hand_tuple, upcard_index)], das=das)
    return None
  if code in ("Dh", "Ds"):
    if (hand_tuple, upcard_index) in double_lookup: return double_second_moment(double_lookup[(hand_tuple, upcard_index)][1])
    action = "H" if code == "Dh" else "S"
  else:
    action = code
  lookup = stand_lookup if action == "S" else hit_lookup
  if (hand_tuple, upcard_index) not in lookup: return None
  row = lookup[(hand_tuple, upcard_index)][1]
  if action == "S": return stand_second_moment(row, hand)
  return hit_second_moment(row)



def compute_game_ev(stand_dataset, hit_dataset, double_dataset, split_das_dataset, split_ndas_dataset,
                    das=True, surrender=False, decks=6, enhc=False, risk_aversion=0.0):
  hard_matrix, soft_matrix, pair_matrix = build_strategy_matrix(
    stand_dataset, hit_dataset, double_dataset, split_das_dataset, split_ndas_dataset,
    das, surrender, enhc=enhc, decks=decks, risk_aversion=risk_aversion)

  def build_lookup(dataset):
    lookup = {}
    for key_type in ("hard", "soft"):
      for upcard_index, rows in enumerate(dataset[key_type]):
        for row in rows: lookup[(hand_key(row[0]), upcard_index)] = (row[1], row[2])
    return lookup

  def build_split_lookup(dataset):
    lookup = {}
    for upcard_index, rows in enumerate(dataset):
      for row in rows: lookup[(hand_key(row[0]), upcard_index)] = row[1]
    return lookup

  stand_lookup = build_lookup(stand_dataset)
  hit_lookup = build_lookup(hit_dataset)
  double_lookup = build_lookup(double_dataset)
  split_das_lookup = build_split_lookup(split_das_dataset)
  split_ndas_lookup = build_split_lookup(split_ndas_dataset)

  new_counts = 52 * decks
  bj_factors = [1.0] * 10
  if not enhc:
    bj_factors[0] = 1.0 - (16 * decks) / (new_counts - 1)
    bj_factors[9] = 1.0 - (4 * decks) / (new_counts - 1)

  all_entries = {}
  for (hand_tuple, upcard_index), (prob, _) in stand_lookup.items():
    if len(hand_tuple) == 2:
      weight = (1.0 if hand_tuple[0] == hand_tuple[1] else 2.0) * bj_factors[upcard_index]
      all_entries[(hand_tuple, upcard_index)] = prob * weight
  for (hand_tuple, upcard_index), (prob, _) in hit_lookup.items():
    if len(hand_tuple) == 2 and (hand_tuple, upcard_index) not in all_entries:
      weight = (1.0 if hand_tuple[0] == hand_tuple[1] else 2.0) * bj_factors[upcard_index]
      all_entries[(hand_tuple, upcard_index)] = prob * weight

  total_ev = 0.0; sum_second_moment = 0.0; breakdown = {}
  for (hand_tuple, upcard_index), prob in all_entries.items():
    hand = list(hand_tuple); total = hand_total(hand); is_soft_hand = is_soft(hand)
    is_pair = len(hand) == 2 and hand[0] == hand[1]
    if is_pair: code = pair_matrix.get((upcard_index, hand[0]))
    elif is_soft_hand: code = soft_matrix.get((upcard_index, total))
    else: code = hard_matrix.get((upcard_index, total))
    if code is None: continue

    ev = ev_for_code(code, hand, upcard_index, stand_lookup, hit_lookup, double_lookup,
                     split_das_lookup, split_ndas_lookup, das, enhc=enhc, decks=decks)
    if ev is None: continue
    second_moment = second_moment_for_code(code, hand, upcard_index, stand_lookup, hit_lookup, double_lookup,
                                           split_das_lookup, split_ndas_lookup, das, enhc, decks)
    if second_moment is None: second_moment = ev ** 2

    total_ev += prob * ev
    sum_second_moment += prob * second_moment
    breakdown[code] = breakdown.get(code, 0.0) + prob * ev

  return total_ev, breakdown, sum_second_moment



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--decks", type=int, default=6, choices=[1, 2, 4, 6, 8])
  parser.add_argument("--s17", dest="s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", dest="enhc", action="store_true", default=False)
  parser.add_argument("--us", dest="enhc", action="store_false")
  parser.add_argument("--das", dest="das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")
  parser.add_argument("--surrender", dest="surrender", action="store_true", default=True)
  parser.add_argument("--no-surrender", dest="surrender", action="store_false")
  parser.add_argument("--ra", type=float, default=0.0)
  parser.add_argument("--bet", type=float, default=25.0)
  args = parser.parse_args()

  stand_dataset = get_dataset(load_json("stand.json"), "probs", args.decks, args.s17, args.enhc)
  hit_dataset = get_dataset(load_json("hit.json"), "probs", args.decks, args.s17, args.enhc)
  double_dataset = get_dataset(load_json("double.json"), "probs", args.decks, args.s17, args.enhc)
  split_data = get_dataset(load_json("split.json"), "probs", args.decks, args.s17, args.enhc)
  split_das_dataset = split_data["DAS"]
  split_ndas_dataset = split_data["nDAS"]

  surrender_str = "Late Surrender" if args.surrender else "No Surrender"
  risk_aversion_str = f", λ={args.ra}" if args.ra != 0.0 else ""
  rule_str = (f"{args.decks} deck{'s' if args.decks > 1 else ''}, "
              f"{'S17' if args.s17 else 'H17'}, "
              f"{'ENHC' if args.enhc else 'US peek'}, "
              f"{'DAS' if args.das else 'nDAS'}, "
              f"{surrender_str}{risk_aversion_str}")

  print(f"\n{BOLD}{WHITE}Basic Strategy — {rule_str}{RESET}")

  hard_ev_variance = build_ev_variance_table(stand_dataset, hit_dataset, double_dataset, False)
  soft_ev_variance = build_ev_variance_table(stand_dataset, hit_dataset, double_dataset, True)

  print_table("Hard Hands", [str(t) for t in range(21, 3, -1)],
    [[best_non_split_action(hard_ev_variance.get((upcard_index, total), {}), args.surrender, risk_aversion=args.ra)
      for upcard_index in UPCARD_ORDER] for total in range(21, 3, -1)])

  print_table("Soft Hands", [f"A,{t-11}" if t <= 21 else "A,10" for t in range(21, 12, -1)],
    [[best_non_split_action(soft_ev_variance.get((upcard_index, total), {}), args.surrender, risk_aversion=args.ra)
      for upcard_index in UPCARD_ORDER] for total in range(21, 12, -1)])

  pair_order = [1, 10, 9, 8, 7, 6, 5, 4, 3, 2]
  pair_labels = ["A,A","10,10","9,9","8,8","7,7","6,6","5,5","4,4","3,3","2,2"]
  print_table("Pairs (Split)", pair_labels,
    [[split_decision_chart(split_das_dataset, split_ndas_dataset, stand_dataset, hit_dataset, double_dataset,
                           pair_val, upcard_index, args.surrender, risk_aversion=args.ra)
      for upcard_index in UPCARD_ORDER] for pair_val in pair_order])

  print_legend()

  decision_ev, breakdown, sum_second_moment = compute_game_ev(
    stand_dataset, hit_dataset, double_dataset, split_das_dataset, split_ndas_dataset,
    das=args.das, surrender=args.surrender, decks=args.decks, enhc=args.enhc, risk_aversion=args.ra)

  new_counts = 52 * args.decks
  prob_dealer_bj = ((4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) +
    (16*args.decks/new_counts)*(4*args.decks/(new_counts-1))) if not args.enhc else 0.0
  prob_player_bj = ((4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) +
    (16*args.decks/new_counts)*(4*args.decks/(new_counts-1)))
  prob_dealer_bj_given_player_bj = (
    ((4*args.decks-1)/(new_counts-2))*((16*args.decks-1)/(new_counts-3)) +
    ((16*args.decks-1)/(new_counts-2))*((4*args.decks-1)/(new_counts-3)))
  prob_dealer_bj_no_player = prob_dealer_bj - prob_player_bj * prob_dealer_bj_given_player_bj
  dealer_bj_only_ev = prob_dealer_bj_no_player * -1.0 if not args.enhc else 0.0
  total_ev = decision_ev + dealer_bj_only_ev

  bet = args.bet; hands_hour = 100
  ev_hour = total_ev * bet * hands_hour
  second_moment_total = sum_second_moment + (prob_dealer_bj_no_player if not args.enhc else 0.0)
  variance = second_moment_total - total_ev ** 2
  sd_hour = (variance ** 0.5) * bet * (hands_hour ** 0.5)

  print(f"\n{BOLD}{WHITE}Game EV — {rule_str}{RESET}")
  print(f" Player EV : {total_ev*100:+.4f}%")
  print(f" EV/hour   : ${ev_hour:+.2f} (${bet:.0f} flat, {hands_hour} hands/hr)")
  print(f" SD/hour   : ${sd_hour:.2f}")
  print(f" 1 SD range: ${ev_hour - sd_hour:.2f} to ${ev_hour + sd_hour:.2f}")
  print(f" 2 SD range: ${ev_hour - 2*sd_hour:.2f} to ${ev_hour + 2*sd_hour:.2f}")
  print()



if __name__ == "__main__":
  main()
