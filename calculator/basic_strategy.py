# Generates a basic strategy chart given a ruleset from the calculator's EV data.
# Run: python basic_strategy.py [--decks N] [--s17 | --h17] [--enhc | --us] [--das | --ndas]

import argparse
import json
import os

# Formatting for the table
RESET = "\033[0m"; BOLD = "\033[1m"; RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"; 
ORANGE = "\033[38;5;208m"; CYAN = "\033[96m"; WHITE = "\033[97m"; DIM = "\033[2m"
DECISION_COLOUR = {"H": RED, "S": GREEN, "Dh": YELLOW, "Ds": ORANGE, "P": CYAN}
def colored(text, code):
  color = DECISION_COLOUR.get(code, WHITE)
  return f"{color}{BOLD}{text}{RESET}"



# Data retrieval code
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data") 
def load_json(filename):
  path = os.path.join(DATA_DIR, filename)
  if not os.path.exists(path):
    print(f"ERROR: {path} not found.")
  with open(path) as file:
    return json.load(file)
  
def deck_key(decks):
  return {1: "oneDeck", 2: "twoDeck", 4: "fourDeck", 6: "sixDeck", 8: "eightDeck"}[decks]

def get_dataset(data, key, decks, s17, enhc):
  return data[key][deck_key(decks)]["S17" if s17 else "H17"]["enhc" if enhc else "us"]



# Same EV functionon_split from the calculator
def ev_from_probabilities(probabilities):
  return probabilities["winProb"] - probabilities["loseProb"] - probabilities["DBJ"]

def stand_ev(probabilities, hand):
  if len(hand) == 2 and hand_total(hand) == 21:
    return (1 - probabilities["DBJ"]) * 1.5
  return ev_from_probabilities(probabilities)

def hit_ev(probabilities):
  return ev_from_probabilities(probabilities)

def double_ev(probabilities):
  return 2.0 * ev_from_probabilities(probabilities)

def split_ev(probabilities, das=False):
  w2=probabilities["double"]["winProb"]; t2=probabilities["double"]["tieProb"]; l2=probabilities["double"]["loseProb"]
  w=probabilities["noDouble"]["winProb"]; t=probabilities["noDouble"]["tieProb"]
  l=probabilities["noDouble"]["loseProb"]; d=probabilities["noDouble"]["DBJ"]
  if das:
    win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2; win1=2*w2*l+2*w*(t+t2)
    lose1=2*l2*w+2*l*(t+t2); lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
    return 4*win4+3*win3+2*win2+win1-d-lose1-2*lose2-3*lose3-4*lose4
  return 2*w**2 + 2*w*t - d - 2*l*t - 2*l**2



# Helper functionon_split
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

def hand_key(hand_cards):
  return tuple(sorted(c for c in hand_cards))

def best_non_split_character(evs):
  if not evs: return "S"
  best_key = None
  best_value = float('-inf')
  for k in evs:
    if evs[k] > best_value: best_value = evs[k]; best_key = k
  return best_key



# Generates a hard/soft EV table
def build_ev_table(stand_dataset, hit_dataset, double_dataset, is_soft_table):
  def hand_key(hand_cards):
    return tuple(sorted(c for c in hand_cards))
  
  weighted_ev_table = {}
  key = "soft" if is_soft_table else "hard"
  for upcard_index in range(10):
    stand_map = {}; hit_map = {}; double_map = {}

    # row[0]: hand, row[1]: hand probability, row[2]: the resulting win/tie/loss/DBJ probabilities from the calculator
    for row in stand_dataset[key][upcard_index]: 
      stand_map[hand_key(row[0])] = (row[1], row[2])
    for row in hit_dataset[key][upcard_index]:
      hit_map[hand_key(row[0])] = (row[1], row[2])
    for row in double_dataset[key][upcard_index]:
      double_map[hand_key(row[0])] = (row[1], row[2])

    for hand in set(stand_map) | set(hit_map) | set(double_map):
      if is_soft_table != is_soft(hand): continue
      total = hand_total(hand)
      cell_key = (upcard_index, total)
      if cell_key not in weighted_ev_table:
        weighted_ev_table[cell_key] = {}

      # cell[0]: cumulative weighted EV for a given total v upcard, cell[1]: cumulative probability
      if hand in stand_map:
        hand_probability, results_list = stand_map[hand]
        cell = weighted_ev_table[cell_key].setdefault("S", [0.0, 0.0])
        cell[0] += stand_ev(results_list, hand) * hand_probability
        cell[1] += hand_probability
      if hand in hit_map:
        hand_probability, results_list = hit_map[hand]
        cell = weighted_ev_table[cell_key].setdefault("H", [0.0, 0.0])
        cell[0] += hit_ev(results_list) * hand_probability
        cell[1] += hand_probability

      # Distinguishes between "Double, otherwise stand" and "Double, otherwise hit", 
      # as doubling isn't always available. Think three-card elevenon_split or if nDAS.
      if hand in double_map:
        hand_probability, results_list = double_map[hand]
        h_ev = hit_ev(hit_map[hand][1]) if hand in hit_map else -999.0
        s_ev = stand_ev(stand_map[hand][1], hand) if hand in stand_map else -999.0
        d_key = "Dh" if h_ev > s_ev else "Ds" 
        cell = weighted_ev_table[cell_key].setdefault(d_key, [0.0, 0.0])
        cell[0] += double_ev(results_list) * hand_probability
        cell[1] += hand_probability

  # Converts weighted ev and cumulative probability into decision-based ev
  # For example: "H": [0.031 (weighted ev), 0.04 (probability)] --> "H":  0.775 (actual ev)
  result = {}
  for cell_key, decisionon_split in weighted_ev_table.items():
    result[cell_key] = {}
    for decision, (ev, probabilities) in decisionon_split.items():
      if probabilities > 0:
        result[cell_key][decision] = ev / probabilities
  return result



# Determines whether to split given DAS/nDAS split EVs vs the best non-split EV
def split_decision(split_dataset_das, split_dataset_ndas, stand_dataset, hit_dataset, double_dataset, pair_val, upcard_index, das=True):
  def get_split_ev(dataset, das=False):
    for row in dataset[upcard_index]:
      # row[0]: hand, row[0][0]: first card, row[1]: split EV probabilities
      if row[0][0] == pair_val: return split_ev(row[1], das)
    return None

  das_ev = get_split_ev(split_dataset_das, das=True)
  ndas_ev = get_split_ev(split_dataset_ndas, das=False)
  pair_hand = (pair_val, pair_val)
  key_type = "soft" if is_soft(pair_hand) else "hard"
  non_split_evs = {}

  # row[0]: hand, row[2]: the resulting win/tie/loss/DBJ probabilities from the calculator
  for label, dataset in (("S", stand_dataset), ("H", hit_dataset)):
    for row in dataset[key_type][upcard_index]:
      if hand_key(row[0]) == pair_hand:
        non_split_evs[label] = stand_ev(row[2], pair_hand) if label == "S" else hit_ev(row[2])
        break

  for row in double_dataset[key_type][upcard_index]:
    if hand_key(row[0]) == pair_hand:
      d_key = "Dh" if non_split_evs.get("H", -999.0) > non_split_evs.get("S", -999.0) else "Ds"
      non_split_evs[d_key] = double_ev(row[2])
      break

  best_non_split_ev = max(non_split_evs.values()) if non_split_evs else 0.0
  best_non_split_code = best_non_split_character(non_split_evs)
  if (das_ev is not None and das_ev > best_non_split_ev) or (ndas_ev is not None and ndas_ev > best_non_split_ev): return "P"
  return best_non_split_code



# Table construction
UPCARD_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
UPCARD_LABELS = ["2","3","4","5","6","7","8","9","10","A"]

def pad(s, width):
  visible = len(s.replace(RESET,"").replace(BOLD,"").replace(RED,"").replace(GREEN,"").replace(YELLOW,"").replace(ORANGE,"").replace(CYAN,"").replace(WHITE,"").replace(DIM,""))
  pad = max(0, width - visible)
  left = pad // 2
  return " " * left + s + " " * (pad - left)

def print_table(title, row_labels, rows):
  col_w, row_lw = 5, 6
  sep = DIM + "─" * (row_lw + 1 + (col_w + 1) * len(UPCARD_LABELS)) + RESET
  print(f"\n{BOLD}{WHITE}{title}{RESET}")
  print(sep)
  print(f"{'':>{row_lw}} │" + "│".join(pad(l, col_w) for l in UPCARD_LABELS))
  print(sep)
  for label, row in zip(row_labels, rows):
    print(f"{label:>{row_lw}} │" + "│".join(pad(colored(code, code), col_w) for code in row))
  print(sep)

def print_legend():
  items = [("H","Hit"),("S","Stand"),("Dh","Double, else Hit"),("Ds","Double, else Stand"),("P","Split")]
  print(f"\n{BOLD}Legend{RESET}")
  for code, desc in items:
    colored_code = colored(code, code)
    visible_len = len(code)
    print(f"  {colored_code}{chr(32) * (8 - visible_len)} {desc}")



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--decks", type=int, default=6, choices=[1,2,4,6,8])
  parser.add_argument("--s17", dest="s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", dest="enhc", action="store_true", default=False)
  parser.add_argument("--us", dest="enhc", action="store_false")
  parser.add_argument("--das", dest="das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")
  args = parser.parse_args()

  stand_dataset = get_dataset(load_json("stand.json"), "probs", args.decks, args.s17, args.enhc)
  hit_dataset = get_dataset(load_json("hit.json"), "probs", args.decks, args.s17, args.enhc)
  double_dataset = get_dataset(load_json("double.json"), "probs", args.decks, args.s17, args.enhc)
  split_dataset_full = get_dataset(load_json("split.json"), "probs", args.decks, args.s17, args.enhc)
  split_dataset_das = split_dataset_full["DAS"]
  split_dataset_ndas = split_dataset_full["nDAS"]

  rule_str = f"{args.decks} deck{'s' if args.decks > 1 else ''}, {'S17' if args.s17 else 'H17'}, {'ENHC' if args.enhc else 'US peek'}, {'DAS' if args.das else 'nDAS'}"
  print(f"\n{BOLD}{WHITE}Basic Strategy — {rule_str}{RESET}")

  hard_ev_table = build_ev_table(stand_dataset, hit_dataset, double_dataset, False)
  soft_ev_table = build_ev_table(stand_dataset, hit_dataset, double_dataset, True)

  print_table("Hard Hands", [str(t) for t in range(21, 3, -1)],
    [[best_non_split_character(hard_ev_table.get((ui, total), {})) for ui in UPCARD_ORDER] for total in range(21, 3, -1)])

  print_table("Soft Hands", [f"A,{t-11}" if t <= 21 else "A,10" for t in range(21, 12, -1)],
    [[best_non_split_character(soft_ev_table.get((ui, total), {})) for ui in UPCARD_ORDER] for total in range(21, 12, -1)])

  pair_order = [1, 10, 9, 8, 7, 6, 5, 4, 3, 2]
  pair_labels = ["A,A","10,10","9,9","8,8","7,7","6,6","5,5","4,4","3,3","2,2"]
  print_table("Pairs (Split)", pair_labels,
    [[split_decision(split_dataset_das, split_dataset_ndas, stand_dataset, hit_dataset, double_dataset, pv, ui, das=args.das) for ui in UPCARD_ORDER] for pv in pair_order])

  print_legend()
  print()

if __name__ == "__main__":
  main()