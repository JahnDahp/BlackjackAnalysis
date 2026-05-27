import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blackjack_calc import Calculator, DealerSettingsObject

settings = DealerSettingsObject(decks=6, S17=True, ENHC=False, DAS=False)
instance = Calculator.create(settings)

PAIR_LABELS = ["A","2","3","4","5","6","7","8","9","10"]
UPCARD_LABELS = ["2","3","4","5","6","7","8","9","10","A"]
UPCARD_ORDER = [2,3,4,5,6,7,8,9,10,1]

print(f"\nSplit EVs — 6D S17 US DAS")
print(f"{'':>4} " + "  ".join(f"{u:>9}" for u in UPCARD_LABELS))

das_key = "DAS" if settings.DAS else "nDAS"
data_set = instance.get_data_set(instance.split_data["probs"])[das_key]

for pair_val in range(1, 11):
    evs = []
    for up_card in UPCARD_ORDER:
        hand_index = instance.get_hand_index([pair_val, pair_val], data_set[up_card - 1])
        if hand_index != -1:
            ev = instance.calc_split_ev(data_set[up_card - 1][hand_index][1])
            evs.append(f"{ev:>9.5f}")
        else:
            evs.append(f"{'N/A':>6}")
    print(f"{PAIR_LABELS[pair_val-1]:>4} " + "  ".join(evs))