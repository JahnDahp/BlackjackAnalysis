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



def ev_from_probabilities(p):
  return p["winProb"] - p["loseProb"] - p["DBJ"]

def stand_ev(p, hand):
  if len(hand) == 2 and hand_total(hand) == 21:
    return (1 - p["DBJ"]) * 1.5
  return ev_from_probabilities(p)

def hit_ev(p):
  return ev_from_probabilities(p)

def double_ev(p):
  return 2.0 * ev_from_probabilities(p)

def split_ev(p, das=False):
  win_dbl=p["double"]["winProb"]; tie_dbl=p["double"]["tieProb"]; lose_dbl=p["double"]["loseProb"]; dbj_dbl=p["double"]["DBJ"]
  win=p["noDouble"]["winProb"]; tie=p["noDouble"]["tieProb"]; lose=p["noDouble"]["loseProb"]; dbj=p["noDouble"]["DBJ"]
  if das:
    win4=win_dbl**2; win3=2*win_dbl*win; win2=2*win_dbl*(tie+tie_dbl)+win**2; win1=2*win_dbl*lose+2*win*(tie+tie_dbl)
    lose1=2*lose_dbl*win+2*lose*(tie+tie_dbl); lose2=2*lose_dbl*(tie+tie_dbl)+lose**2; lose3=2*lose_dbl*lose; lose4=lose_dbl**2
    return 4*win4+3*win3+2*win2+win1-2*dbj-4*dbj_dbl-lose1-2*lose2-3*lose3-4*lose4
  return 2*win**2+2*win*tie-2*dbj-2*lose*tie-2*lose**2



def stand_e2(p, hand):
  if len(hand) == 2 and hand_total(hand) == 21:
    return 2.25 * (1.0 - p["DBJ"])
  return 1.0 - p["tieProb"]

def hit_e2(p):
  return 1.0 - p["tieProb"]

def double_e2(p):
  return 4.0 * (1.0 - p["tieProb"])

def split_e2(p, das=False):
  win=p["noDouble"]["winProb"]; tie=p["noDouble"]["tieProb"]; lose=p["noDouble"]["loseProb"]
  win_dbl=p["double"]["winProb"]; tie_dbl=p["double"]["tieProb"]; lose_dbl=p["double"]["loseProb"]
  if das:
    win4=win_dbl**2; win3=2*win_dbl*win; win2=2*win_dbl*(tie+tie_dbl)+win**2
    tie_var=2*win_dbl*lose_dbl+2*win*lose+(tie+tie_dbl)**2
    lose2=2*lose_dbl*(tie+tie_dbl)+lose**2; lose3=2*lose_dbl*lose; lose4=lose_dbl**2
    return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie_var
  return 1 + 3*(win**2+lose**2) - (2*win*lose + tie**2)

def surr_e2(ui, enhc, decks):
  new_counts = 52 * decks
  d = ((16*decks)/(new_counts-1) if ui==0 else (4*decks)/(new_counts-1) if ui==9 else 0.0) if enhc else 0.0
  return (1-d)*0.25 + d*1.0



def hand_total(hand):
  total = 0; aces = 0
  for c in hand:
    if c == 1: total += 11; aces += 1
    else: total += c
  while total > 21 and aces: total -= 10; aces -= 1
  return total

def is_soft(hand):
  total = 0; aces = 0
  for c in hand:
    if c == 1: total += 11; aces += 1
    else: total += c
  while total > 21 and aces: total -= 10; aces -= 1
  return aces > 0

def hand_key(hand):
  return tuple(sorted(hand))

def surr_ev(ui, enhc, decks):
  if not enhc:
    return -0.5
  new_counts = 52 * decks
  if ui == 0: return -0.5 - 0.5 * (16 * decks) / (new_counts - 1)
  if ui == 9: return -0.5 - 0.5 * (4 * decks) / (new_counts - 1)
  return -0.5

def ce(ev, e2, ra):
  """Certainty equivalent: EV - (lambda/2) * Var, where Var = E[X²] - EV²."""
  return ev - (ra / 2.0) * (e2 - ev ** 2)



def best_non_split_character(ev_var, surrender=False, s_ev=-0.5, s_e2=0.25, ra=0.0):
  """Pick the best action by CE. ev_var: {action: (ev, e2)}."""
  if not ev_var: return "S"
  best_key = None
  best_ce = float('-inf')
  for k, (ev, e2) in ev_var.items():
    c = ce(ev, e2, ra)
    if c > best_ce: best_ce = c; best_key = k
  surr_ce = ce(s_ev, s_e2, ra)
  if surrender and surr_ce > best_ce:
    return "R" + best_key
  return best_key



def build_ev_var_table(stand_dataset, hit_dataset, double_dataset, is_soft_table):
  def hand_key(hand_cards): return tuple(sorted(hand_cards))

  acc = {}
  key = "soft" if is_soft_table else "hard"

  for upcard_index in range(10):
    stand_map = {}; hit_map = {}; double_map = {}
    for row in stand_dataset[key][upcard_index]: stand_map[hand_key(row[0])] = (row[1], row[2])
    for row in hit_dataset[key][upcard_index]: hit_map[hand_key(row[0])] = (row[1], row[2])
    for row in double_dataset[key][upcard_index]: double_map[hand_key(row[0])] = (row[1], row[2])

    for hand in set(stand_map) | set(hit_map) | set(double_map):
      if is_soft_table != is_soft(hand): continue
      if len(hand) != 2: continue
      total = hand_total(hand)
      cell_key = (upcard_index, total)
      if cell_key not in acc: acc[cell_key] = {}

      if hand in stand_map:
        prob, r = stand_map[hand]
        ev_val = stand_ev(r, hand)
        e2_val = stand_e2(r, hand)
        cell = acc[cell_key].setdefault("S", [0.0, 0.0, 0.0])
        cell[0] += ev_val * prob; cell[1] += e2_val * prob; cell[2] += prob

      if hand in hit_map:
        prob, r = hit_map[hand]
        ev_val = hit_ev(r)
        e2_val = hit_e2(r)
        cell = acc[cell_key].setdefault("H", [0.0, 0.0, 0.0])
        cell[0] += ev_val * prob; cell[1] += e2_val * prob; cell[2] += prob

      if hand in double_map:
        prob, r = double_map[hand]
        ev_val = double_ev(r)
        e2_val = double_e2(r)
        h_ev = hit_ev(hit_map[hand][1]) if hand in hit_map else -999.0
        s_ev_v = stand_ev(stand_map[hand][1], hand) if hand in stand_map else -999.0
        d_key = "Dh" if h_ev > s_ev_v else "Ds"
        cell = acc[cell_key].setdefault(d_key, [0.0, 0.0, 0.0])
        cell[0] += ev_val * prob; cell[1] += e2_val * prob; cell[2] += prob

  result = {}
  for cell_key, decisions in acc.items():
    result[cell_key] = {}
    for dec, (sum_ev, sum_e2, sum_prob) in decisions.items():
      if sum_prob > 0:
        result[cell_key][dec] = (sum_ev / sum_prob, sum_e2 / sum_prob)
  return result



def split_decision_chart(split_dataset_das, split_dataset_ndas, stand_dataset, hit_dataset,
                          double_dataset, pair_val, upcard_index, surrender=False, ra=0.0):
  def get_split_ev_e2(dataset, das=False):
    for row in dataset[upcard_index]:
      if row[0][0] == pair_val:
        ev = split_ev(row[1], das)
        e2 = split_e2(row[1], das)
        return ev, e2
    return None, None

  das_ev, das_e2 = get_split_ev_e2(split_dataset_das, das=True)
  ndas_ev, ndas_e2 = get_split_ev_e2(split_dataset_ndas, das=False)

  pair_hand = (pair_val, pair_val)
  key_type = "soft" if is_soft(pair_hand) else "hard"
  non_split_ev_var = {}

  for label, dataset in (("S", stand_dataset), ("H", hit_dataset)):
    for row in dataset[key_type][upcard_index]:
      if hand_key(row[0]) == pair_hand:
        if label == "S":
          non_split_ev_var["S"] = (stand_ev(row[2], pair_hand), stand_e2(row[2], pair_hand))
        else:
          non_split_ev_var["H"] = (hit_ev(row[2]), hit_e2(row[2]))
        break
  for row in double_dataset[key_type][upcard_index]:
    if hand_key(row[0]) == pair_hand:
      h_ev = non_split_ev_var["H"][0] if "H" in non_split_ev_var else -999.0
      s_ev_v = non_split_ev_var["S"][0] if "S" in non_split_ev_var else -999.0
      d_key = "Dh" if h_ev > s_ev_v else "Ds"
      non_split_ev_var[d_key] = (double_ev(row[2]), double_e2(row[2]))
      break

  best_ns_code = best_non_split_character(non_split_ev_var, ra=ra)
  best_ns_ev = non_split_ev_var[best_ns_code][0] if best_ns_code in non_split_ev_var else 0.0
  best_ns_e2 = non_split_ev_var[best_ns_code][1] if best_ns_code in non_split_ev_var else 1.0
  best_ns_ce = ce(best_ns_ev, best_ns_e2, ra)

  das_ce = ce(das_ev, das_e2, ra) if das_ev is not None else None
  ndas_ce = ce(ndas_ev, ndas_e2, ra) if ndas_ev is not None else None

  das_better = das_ce is not None and das_ce > best_ns_ce
  ndas_better = ndas_ce is not None and ndas_ce > best_ns_ce

  s_ev_val = -0.5; s_e2_val = 0.25
  surr_ce_val = ce(s_ev_val, s_e2_val, ra)

  if das_better and ndas_better:
    return "RP" if (surrender and surr_ce_val > das_ce) else "P"
  elif das_better:
    return "RP?" if (surrender and surr_ce_val > das_ce) else "P?"
  else:
    if surrender and surr_ce_val > best_ns_ce:
      return "R" + best_ns_code
    return best_ns_code



UPCARD_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
UPCARD_LABELS = ["2","3","4","5","6","7","8","9","10","A"]

def pad(s, width):
  visible = len(s.replace(RESET,"").replace(BOLD,"").replace(RED,"").replace(GREEN,"")
               .replace(YELLOW,"").replace(ORANGE,"").replace(CYAN,"").replace(TEAL,"")
               .replace(WHITE,"").replace(DIM,"").replace(MAGENTA,""))
  p = max(0, width - visible)
  return " " * (p // 2) + s + " " * (p - p // 2)

def print_table(title, row_labels, rows):
  col_w, row_lw = 6, 6
  sep = DIM + "─" * (row_lw + 1 + (col_w + 1) * len(UPCARD_LABELS)) + RESET
  print(f"\n{BOLD}{WHITE}{title}{RESET}")
  print(sep)
  print(f"{'':>{row_lw}} │" + "│".join(pad(l, col_w) for l in UPCARD_LABELS))
  print(sep)
  for label, row in zip(row_labels, rows):
    print(f"{label:>{row_lw}} │" + "│".join(pad(colored(code, code), col_w) for code in row))
  print(sep)

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



def build_strategy_matrix(stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
                           das=True, surrender=False, enhc=False, decks=6, ra=0.0):
  hard_ev_var = build_ev_var_table(stand_ds, hit_ds, double_ds, False)
  soft_ev_var = build_ev_var_table(stand_ds, hit_ds, double_ds, True)

  hard_matrix = {}
  soft_matrix = {}
  for (ui, total), ev_var in hard_ev_var.items():
    s_ev_v = surr_ev(ui, enhc, decks); s_e2_v = surr_e2(ui, enhc, decks)
    hard_matrix[(ui, total)] = best_non_split_character(ev_var, surrender, s_ev_v, s_e2_v, ra)
  for (ui, total), ev_var in soft_ev_var.items():
    s_ev_v = surr_ev(ui, enhc, decks); s_e2_v = surr_e2(ui, enhc, decks)
    soft_matrix[(ui, total)] = best_non_split_character(ev_var, surrender, s_ev_v, s_e2_v, ra)

  def build_split_lookup(dataset):
    lookup = {}
    for ui, rows in enumerate(dataset):
      for row in rows: lookup[(hand_key(row[0]), ui)] = row[1]
    return lookup

  split_das_lkp = build_split_lookup(split_das_ds)
  split_ndas_lkp = build_split_lookup(split_ndas_ds)

  pair_matrix = {}
  for pair_val in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    hand_key = hand_key([pair_val, pair_val])
    for ui in range(10):
      s_ev_v = surr_ev(ui, enhc, decks); s_e2_v = surr_e2(ui, enhc, decks)
      total = hand_total(list(hand_key))
      ev_var = (soft_ev_var if is_soft(list(hand_key)) else hard_ev_var).get((ui, total), {})
      best_ns = best_non_split_character(ev_var, surrender, s_ev_v, s_e2_v, ra)
      if best_ns.startswith("R"):
        best_ns_ce_val = ce(s_ev_v, s_e2_v, ra)
      else:
        ns_ev, ns_e2 = ev_var.get(best_ns, (s_ev_v, s_e2_v))
        best_ns_ce_val = ce(ns_ev, ns_e2, ra)

      lookup = split_das_lkp if das else split_ndas_lkp
      if (hand_key, ui) in lookup:
        sp_ev = split_ev(lookup[(hand_key, ui)], das=das)
        sp_e2 = split_e2(lookup[(hand_key, ui)], das=das)
        sp_ce = ce(sp_ev, sp_e2, ra)
        if sp_ce > best_ns_ce_val:
          code = "RP" if (surrender and ce(s_ev_v, s_e2_v, ra) > sp_ce) else "P"
        else:
          code = best_ns
      else:
        code = best_ns
      pair_matrix[(ui, pair_val)] = code

  return hard_matrix, soft_matrix, pair_matrix



def ev_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp, split_das_lkp, split_ndas_lkp, das, enhc=False, decks=6):
  hand_key = hand_key(hand)
  if code == "P":
    lookup = split_das_lkp if das else split_ndas_lkp
    if (hand_key, ui) in lookup: return split_ev(lookup[(hand_key, ui)], das=das)
  if code.startswith("R"):
    return surr_ev(ui, enhc, decks)
  if code in ("Dh", "Ds"):
    if (hand_key, ui) in double_lkp: return double_ev(double_lkp[(hand_key, ui)][1])
    action = "H" if code == "Dh" else "S"
  else:
    action = code
  if action == "S" and (hand_key, ui) in stand_lkp: return stand_ev(stand_lkp[(hand_key, ui)][1], hand)
  if action == "H" and (hand_key, ui) in hit_lkp: return hit_ev(hit_lkp[(hand_key, ui)][1])
  return None

def e2_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp, split_das_lkp, split_ndas_lkp, das, enhc, decks):
  hand_key = hand_key(hand)
  if code.startswith("R"):
    return surr_e2(ui, enhc, decks)
  if code == "P":
    lookup = split_das_lkp if das else split_ndas_lkp
    if (hand_key, ui) in lookup: return split_e2(lookup[(hand_key, ui)], das=das)
    return None
  if code in ("Dh", "Ds"):
    if (hand_key, ui) in double_lkp: return double_e2(double_lkp[(hand_key, ui)][1])
    action = "H" if code == "Dh" else "S"
  else:
    action = code
  lookup = stand_lkp if action == "S" else hit_lkp
  if (hand_key, ui) not in lookup: return None
  r = lookup[(hand_key, ui)][1]
  if action == "S": return stand_e2(r, hand)
  return hit_e2(r)



def compute_game_ev(stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
                    das=True, surrender=False, decks=6, enhc=False, ra=0.0):
  hard_matrix, soft_matrix, pair_matrix = build_strategy_matrix(
    stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
    das, surrender, enhc=enhc, decks=decks, ra=ra)

  def build_lookup(dataset):
    lookup = {}
    for key_type in ("hard", "soft"):
      for ui, rows in enumerate(dataset[key_type]):
        for row in rows: lookup[(hand_key(row[0]), ui)] = (row[1], row[2])
    return lookup

  def build_split_lookup(dataset):
    lookup = {}
    for ui, rows in enumerate(dataset):
      for row in rows: lookup[(hand_key(row[0]), ui)] = row[1]
    return lookup

  stand_lkp = build_lookup(stand_ds)
  hit_lkp = build_lookup(hit_ds)
  double_lkp = build_lookup(double_ds)
  split_das_lkp = build_split_lookup(split_das_ds)
  split_ndas_lkp = build_split_lookup(split_ndas_ds)

  new_counts = 52 * decks
  bj_factors = [1.0] * 10
  if not enhc:
    bj_factors[0] = 1.0 - (16 * decks) / (new_counts - 1)
    bj_factors[9] = 1.0 - (4 * decks) / (new_counts - 1)

  all_entries = {}
  for (hand_key, ui), (prob, _) in stand_lkp.items():
    if len(hand_key) == 2:
      w = (1.0 if hand_key[0] == hand_key[1] else 2.0) * bj_factors[ui]
      all_entries[(hand_key, ui)] = prob * w
  for (hand_key, ui), (prob, _) in hit_lkp.items():
    if len(hand_key) == 2 and (hand_key, ui) not in all_entries:
      w = (1.0 if hand_key[0] == hand_key[1] else 2.0) * bj_factors[ui]
      all_entries[(hand_key, ui)] = prob * w

  total_ev = 0.0; sum_e2 = 0.0; breakdown = {}
  for (hand_key, ui), prob in all_entries.items():
    hand = list(hand_key); total = hand_total(hand); soft = is_soft(hand)
    is_pair = len(hand) == 2 and hand[0] == hand[1]
    if is_pair: code = pair_matrix.get((ui, hand[0]))
    elif soft: code = soft_matrix.get((ui, total))
    else: code = hard_matrix.get((ui, total))
    if code is None: continue

    ev = ev_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp, split_das_lkp, split_ndas_lkp, das, enhc=enhc, decks=decks)
    if ev is None: continue
    e2 = e2_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp, split_das_lkp, split_ndas_lkp, das, enhc, decks)
    if e2 is None: e2 = ev ** 2

    total_ev += prob * ev
    sum_e2 += prob * e2
    breakdown[code] = breakdown.get(code, 0.0) + prob * ev

  return total_ev, breakdown, sum_e2



def main():
  parser = argparse.ArgumentParser(description="Basic strategy charts + game EV for a blackjack ruleset.")
  parser.add_argument("--decks", type=int, default=6, choices=[1,2,4,6,8])
  parser.add_argument("--s17", dest="s17", action="store_true", default=True)
  parser.add_argument("--h17", dest="s17", action="store_false")
  parser.add_argument("--enhc", dest="enhc", action="store_true", default=False)
  parser.add_argument("--us", dest="enhc", action="store_false")
  parser.add_argument("--das", dest="das", action="store_true", default=True)
  parser.add_argument("--ndas", dest="das", action="store_false")
  parser.add_argument("--surrender", dest="surrender",action="store_true", default=True)
  parser.add_argument("--no-surrender", dest="surrender",action="store_false")
  parser.add_argument("--ra", type=float, default=0.0,
                      help="Risk aversion coefficient λ (CE = EV - (λ/2)·Var). Default 0 = risk neutral.")
  parser.add_argument("--bet", type=float, default=25.0,
                      help="Flat bet size in dollars. Default $25.")
  args = parser.parse_args()

  stand_ds = get_dataset(load_json("stand.json"), "probs", args.decks, args.s17, args.enhc)
  hit_ds = get_dataset(load_json("hit.json"), "probs", args.decks, args.s17, args.enhc)
  double_ds = get_dataset(load_json("double.json"), "probs", args.decks, args.s17, args.enhc)
  split_full = get_dataset(load_json("split.json"), "probs", args.decks, args.s17, args.enhc)
  split_das_ds = split_full["DAS"]
  split_ndas_ds = split_full["nDAS"]

  surrender_str = "Late Surrender" if args.surrender else "No Surrender"
  ra_str = f", λ={args.ra}" if args.ra != 0.0 else ""
  rule_str = (f"{args.decks} deck{'s' if args.decks > 1 else ''}, "
              f"{'S17' if args.s17 else 'H17'}, "
              f"{'ENHC' if args.enhc else 'US peek'}, "
              f"{'DAS' if args.das else 'nDAS'}, "
              f"{surrender_str}{ra_str}")

  print(f"\n{BOLD}{WHITE}Basic Strategy — {rule_str}{RESET}")

  hard_ev_var = build_ev_var_table(stand_ds, hit_ds, double_ds, False)
  soft_ev_var = build_ev_var_table(stand_ds, hit_ds, double_ds, True)

  print_table("Hard Hands", [str(t) for t in range(21, 3, -1)],
    [[best_non_split_character(hard_ev_var.get((ui, total), {}), args.surrender, ra=args.ra)
      for ui in UPCARD_ORDER] for total in range(21, 3, -1)])

  print_table("Soft Hands", [f"A,{t-11}" if t <= 21 else "A,10" for t in range(21, 12, -1)],
    [[best_non_split_character(soft_ev_var.get((ui, total), {}), args.surrender, ra=args.ra)
      for ui in UPCARD_ORDER] for total in range(21, 12, -1)])

  pair_order = [1, 10, 9, 8, 7, 6, 5, 4, 3, 2]
  pair_labels = ["A,A","10,10","9,9","8,8","7,7","6,6","5,5","4,4","3,3","2,2"]
  print_table("Pairs (Split)", pair_labels,
    [[split_decision_chart(split_das_ds, split_ndas_ds, stand_ds, hit_ds, double_ds,
                           pv, ui, args.surrender, ra=args.ra)
      for ui in UPCARD_ORDER] for pv in pair_order])

  print_legend()

  decision_ev, breakdown, sum_e2 = compute_game_ev(
    stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
    das=args.das, surrender=args.surrender, decks=args.decks, enhc=args.enhc, ra=args.ra)

  new_counts = 52 * args.decks
  p_dealer_bj = (4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) + (16*args.decks/new_counts)*(4*args.decks/(new_counts-1)) if not args.enhc else 0.0
  p_player_bj = (4*args.decks/new_counts)*(16*args.decks/(new_counts-1)) + (16*args.decks/new_counts)*(4*args.decks/(new_counts-1))
  p_dealer_bj_given_player_bj = (((4*args.decks-1)/(new_counts-2))*((16*args.decks-1)/(new_counts-3)) +
                                  ((16*args.decks-1)/(new_counts-2))*((4*args.decks-1)/(new_counts-3)))
  p_both_bj = p_player_bj * p_dealer_bj_given_player_bj
  p_dealer_bj_no_player = p_dealer_bj - p_both_bj
  dealer_bj_only_ev = p_dealer_bj_no_player * -1.0 if not args.enhc else 0.0
  total_ev = decision_ev + dealer_bj_only_ev

  bet = args.bet; hands_hour = 100
  ev_hour = total_ev * bet * hands_hour
  e2_total = sum_e2 + (p_dealer_bj_no_player if not args.enhc else 0.0)
  variance = e2_total - total_ev ** 2
  sd_hour = (variance ** 0.5) * bet * (hands_hour ** 0.5)

  print(f"\n{BOLD}{WHITE}Game EV — {rule_str}{RESET}")
  print(f" Player EV : {total_ev*100:+.4f}%")
  print(f" EV/hour : ${ev_hour:+.2f} (${bet:.0f} flat, {hands_hour} hands/hr)")
  print(f" SD/hour : ${sd_hour:.2f}")
  print(f" 1 SD (68.3%): ${ev_hour - sd_hour:.2f} to ${ev_hour + sd_hour:.2f}")
  print(f" 2 SD (95.5%): ${ev_hour - 2*sd_hour:.2f} to ${ev_hour + 2*sd_hour:.2f}")
  print()



if __name__ == "__main__":
  main()

