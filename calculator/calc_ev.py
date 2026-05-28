import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blackjack_calc import Calculator, DealerSettingsObject

settings = DealerSettingsObject(decks=6, S17=True, ENHC=False, DAS=True)
instance = Calculator.create(settings)

UPCARD_LABELS = ["2","3","4","5","6","7","8","9","10","A"]
UPCARD_ORDER  = [2,3,4,5,6,7,8,9,10,1]
COL = 9
DEC = 5


def hand_total(hand):
  total = 0; aces = 0
  for card in hand:
    if card == 1: total += 11; aces += 1
    else: total += card
  while total > 21 and aces: total -= 10; aces -= 1
  return total

def raw_ev(probs):
  return probs["winProb"] - probs["loseProb"] - probs["DBJ"]


# Weighted average EV across hand compositions that reach total_target for a given upcard list
def weighted_ev(upcard_entries, total_target, multiplier=1.0, two_card_only=True):
  total_ev = 0.0; total_prob = 0.0
  for row in upcard_entries:
    if hand_total(row[0]) != total_target: continue
    if two_card_only and len(row[0]) != 2: continue
    total_ev += raw_ev(row[2]) * row[1]
    total_prob += row[1]
  if total_prob == 0: return None
  return multiplier * total_ev / total_prob


def print_table(title, row_labels, get_ev_fn):
  print(f"\n{title}")
  print(f"{'':>6}  " + "  ".join(f"{u:>{COL}}" for u in UPCARD_LABELS))
  for label in row_labels:
    evs = []
    for up_card in UPCARD_ORDER:
      ev = get_ev_fn(label, up_card)
      evs.append(f"{ev:>{COL}.{DEC}f}" if ev is not None else f"{'—':>{COL}}")
    print(f"{label:>6}  " + "  ".join(evs))



# Stand / Hit / Double tables
for decision, label_prefix, multiplier, total_range in [
  ("stand",  "Stand",  1.0, range(21, 3, -1)),
  ("hit",    "Hit",    1.0, range(21, 3, -1)),
  ("double", "Double", 2.0, range(21, 3, -1)),
]:
  data = {"stand": instance.stand_data, "hit": instance.hit_data, "double": instance.double_data}[decision]
  for soft, soft_label, t_range in [(False, "Hard", total_range), (True, "Soft", range(21, 12, -1))]:
    key = "soft" if soft else "hard"
    dataset = instance.get_data_set(data["probs"])

    soft_labels = {t: f"A,{t-11}" for t in range(13, 22)}
    soft_labels[21] = "A,10"
    row_labels = [soft_labels[t] for t in t_range] if soft else [str(t) for t in t_range]

    def get_ev(label, up_card, _dataset=dataset, _key=key, _t_range=list(t_range), _soft_labels=soft_labels, _soft=soft, _multiplier=multiplier):
      total = _t_range[row_labels.index(label)] if _soft else int(label)
      if _soft:
        total = next(t for t in range(13, 22) if _soft_labels[t] == label)
      return weighted_ev(_dataset[_key][up_card - 1], total, _multiplier)

    print_table(f"{label_prefix} EVs — {soft_label} Hands", row_labels, get_ev)



# Split EV tables
split_full = instance.get_data_set(instance.split_data["probs"])
PAIR_LABELS = ["A","2","3","4","5","6","7","8","9","10"]
pair_vals   = [1,2,3,4,5,6,7,8,9,10]

for das_label, das_flag in [("DAS", True), ("nDAS", False)]:
  split_dataset = split_full[das_label]
  tmp_instance = Calculator.create(DealerSettingsObject(decks=settings.decks, S17=settings.S17, ENHC=settings.ENHC, DAS=das_flag))

  def get_split_ev(label, up_card, _ds=split_dataset, _inst=tmp_instance):
    pair_val = pair_vals[PAIR_LABELS.index(label)]
    idx = _inst.get_hand_index([pair_val, pair_val], _ds[up_card - 1])
    if idx == -1: return None
    return _inst.calc_split_ev(_ds[up_card - 1][idx][1])

  print_table(f"Split EVs — {das_label}", PAIR_LABELS, get_split_ev)