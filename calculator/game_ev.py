# Calculates the overall house edge / player EV for a given blackjack ruleset.
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


# ── EV functions ───────────────────────────────────────────────────────────────

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
    w2 = p["double"]["winProb"]; l2 = p["double"]["loseProb"]; d2 = p["double"]["DBJ"]
    w  = p["noDouble"]["winProb"]; l  = p["noDouble"]["loseProb"]; d  = p["noDouble"]["DBJ"]
    if das:
        return 4*w2 - 4*l2 - 4*d2 + 2*w - 2*l - 2*d
    return 2*w - 2*l - 2*d


# ── Hand helpers ───────────────────────────────────────────────────────────────

def hand_total(hand):
    total = 0; aces = 0
    for c in hand:
        if c == 1: total += 11; aces += 1
        else: total += c
    while total > 21 and aces:
        total -= 10; aces -= 1
    return total

def is_soft(hand):
    total = 0; aces = 0
    for c in hand:
        if c == 1: total += 11; aces += 1
        else: total += c
    while total > 21 and aces:
        total -= 10; aces -= 1
    return aces > 0

def hand_key(hand):
    return tuple(sorted(hand))


# ── Strategy matrix construction ──────────────────────────────────────────────

def build_ev_table(stand_dataset, hit_dataset, double_dataset, is_soft_table):
    weighted_ev_table = {}

    for upcard_index in range(10):
        stand_map = {}; hit_map = {}; double_map = {}

        for row in stand_dataset["soft" if is_soft_table else "hard"][upcard_index]:
            stand_map[hand_key(row[0])] = (row[1], row[2])
        for row in hit_dataset["soft" if is_soft_table else "hard"][upcard_index]:
            hit_map[hand_key(row[0])] = (row[1], row[2])
        for row in double_dataset["soft" if is_soft_table else "hard"][upcard_index]:
            double_map[hand_key(row[0])] = (row[1], row[2])

        for hk in set(stand_map) | set(hit_map) | set(double_map):
            hand = list(hk)
            if is_soft_table != is_soft(hand): continue
            if len(hand) != 2: continue

            total = hand_total(hand)
            cell_key = (upcard_index, total)
            if cell_key not in weighted_ev_table:
                weighted_ev_table[cell_key] = {}

            if hk in stand_map:
                prob, results = stand_map[hk]
                cell = weighted_ev_table[cell_key].setdefault("S", [0.0, 0.0])
                cell[0] += stand_ev(results, hand) * prob
                cell[1] += prob

            if hk in hit_map:
                prob, results = hit_map[hk]
                cell = weighted_ev_table[cell_key].setdefault("H", [0.0, 0.0])
                cell[0] += hit_ev(results) * prob
                cell[1] += prob

            if hk in double_map:
                prob, results = double_map[hk]
                h_ev = hit_ev(hit_map[hk][1]) if hk in hit_map else -999.0
                s_ev = stand_ev(stand_map[hk][1], hand) if hk in stand_map else -999.0
                d_key = "Dh" if h_ev > s_ev else "Ds"
                cell = weighted_ev_table[cell_key].setdefault(d_key, [0.0, 0.0])
                cell[0] += double_ev(results) * prob
                cell[1] += prob

    result = {}
    for cell_key, decisions in weighted_ev_table.items():
        result[cell_key] = {
            dec: (ev / prob) for dec, (ev, prob) in decisions.items() if prob > 0
        }
    return result


def surr_ev(ui, enhc, decks):
    """Effective surrender EV.  For ENHC late surrender the player can still
    lose the full bet to dealer BJ, so EV = -0.5 - 0.5*P(BJ|upcard)."""
    if not enhc:
        return -0.5
    nc = 52 * decks
    if ui == 0:  return -0.5 - 0.5 * (16 * decks) / (nc - 1)   # ace upcard
    if ui == 9:  return -0.5 - 0.5 * (4  * decks) / (nc - 1)   # ten upcard
    return -0.5


def best_non_split_code(evs, surrender=False, s_ev=-0.5):
    if not evs:
        return "S"
    best = max(evs, key=lambda k: evs[k])
    if surrender and evs[best] < s_ev:
        return "R" + best
    return best


def get_ev_for_code(code, evs):
    if code.startswith("R"):
        return evs.get(code[1:], -999.0)
    return evs.get(code, -999.0)


def build_strategy_matrix(stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
                           das=True, surrender=False, enhc=False, decks=6):
    hard_ev_table = build_ev_table(stand_ds, hit_ds, double_ds, False)
    soft_ev_table = build_ev_table(stand_ds, hit_ds, double_ds, True)

    hard_matrix = {
        (ui, total): best_non_split_code(evs, surrender, surr_ev(ui, enhc, decks))
        for (ui, total), evs in hard_ev_table.items()
    }
    soft_matrix = {
        (ui, total): best_non_split_code(evs, surrender, surr_ev(ui, enhc, decks))
        for (ui, total), evs in soft_ev_table.items()
    }

    def build_split_lookup(dataset):
        lkp = {}
        for ui, rows in enumerate(dataset):
            for row in rows:
                lkp[(hand_key(row[0]), ui)] = row[1]
        return lkp

    split_das_lkp  = build_split_lookup(split_das_ds)
    split_ndas_lkp = build_split_lookup(split_ndas_ds)

    pair_matrix = {}
    for pair_val in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        hk = hand_key([pair_val, pair_val])
        for ui in range(10):
            se = surr_ev(ui, enhc, decks)
            total = hand_total(list(hk))
            soft  = is_soft(list(hk))
            ev_table = soft_ev_table if soft else hard_ev_table
            non_split_evs = ev_table.get((ui, total), {})
            best_ns = best_non_split_code(non_split_evs, surrender, se)

            best_ns_ev = se if best_ns.startswith("R") else get_ev_for_code(best_ns, non_split_evs)

            das_ev_val  = split_ev(split_das_lkp[(hk, ui)],  das=True)  if (hk, ui) in split_das_lkp  else None
            ndas_ev_val = split_ev(split_ndas_lkp[(hk, ui)], das=False) if (hk, ui) in split_ndas_lkp else None
            split_ev_val = das_ev_val if das else ndas_ev_val

            if split_ev_val is not None and split_ev_val > best_ns_ev:
                code = "RP" if (surrender and split_ev_val < se) else "P"
            else:
                code = best_ns

            pair_matrix[(ui, pair_val)] = code

    return hard_matrix, soft_matrix, pair_matrix


# ── EV lookup for a given decision code ───────────────────────────────────────

def ev_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp, split_das_lkp, split_ndas_lkp, das,
               enhc=False, decks=6):
    hk = hand_key(hand)

    if code == "P":
        lkp = split_das_lkp if das else split_ndas_lkp
        if (hk, ui) in lkp:
            return split_ev(lkp[(hk, ui)], das=das)

    if code.startswith("R"):
        return surr_ev(ui, enhc, decks)

    if code in ("Dh", "Ds"):
        if (hk, ui) in double_lkp:
            return double_ev(double_lkp[(hk, ui)][1])
        action = "H" if code == "Dh" else "S"
    else:
        action = code  # "S" or "H"

    if action == "S" and (hk, ui) in stand_lkp:
        return stand_ev(stand_lkp[(hk, ui)][1], hand)
    if action == "H" and (hk, ui) in hit_lkp:
        return hit_ev(hit_lkp[(hk, ui)][1])

    return None


def _e2(code, hand, ui, stand_lkp, hit_lkp, double_lkp,
        split_das_lkp, split_ndas_lkp, das, enhc, decks):
    """E[payout^2] — matches Calculator.py calc_*_variance formulas exactly."""
    hk = hand_key(hand)
    if code.startswith("R"):
        nc = 52 * decks
        d = ((16*decks)/(nc-1) if ui==0 else (4*decks)/(nc-1) if ui==9 else 0.0) if enhc else 0.0
        return (1-d)*0.25 + d*1.0
    if code == "P":
        lkp = split_das_lkp if das else split_ndas_lkp
        if (hk, ui) not in lkp:
            return None
        p = lkp[(hk, ui)]
        w=p["noDouble"]["winProb"]; t=p["noDouble"]["tieProb"]; l=p["noDouble"]["loseProb"]
        w2=p["double"]["winProb"];  t2=p["double"]["tieProb"];  l2=p["double"]["loseProb"]
        if das:
            win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2
            tie_=2*w2*l2+2*w*l+(t+t2)**2
            lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
            return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie_
        return 1 + 3*(w**2+l**2) - (2*w*l + t**2)
    if code in ("Dh", "Ds"):
        if (hk, ui) not in double_lkp:
            return None
        r = double_lkp[(hk, ui)][1]
        return 4.0 * (1.0 - r["tieProb"])
    is_nat = len(hand) == 2 and hand_total(hand) == 21
    lkp = stand_lkp if code == "S" else hit_lkp
    if (hk, ui) not in lkp:
        return None
    r = lkp[(hk, ui)][1]
    if is_nat:
        return 2.25 * (1.0 - r["DBJ"])
    return 1.0 - r["tieProb"]



# ── Main EV calculation ────────────────────────────────────────────────────────

def compute_game_ev(stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
                    das=True, surrender=False, decks=6, enhc=False):
    hard_matrix, soft_matrix, pair_matrix = build_strategy_matrix(
        stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds, das, surrender,
        enhc=enhc, decks=decks
    )

    def build_lookup(dataset):
        lkp = {}
        for key_type in ("hard", "soft"):
            for ui, rows in enumerate(dataset[key_type]):
                for row in rows:
                    lkp[(hand_key(row[0]), ui)] = (row[1], row[2])
        return lkp

    def build_split_lookup(dataset):
        lkp = {}
        for ui, rows in enumerate(dataset):
            for row in rows:
                lkp[(hand_key(row[0]), ui)] = row[1]
        return lkp

    stand_lkp      = build_lookup(stand_ds)
    hit_lkp        = build_lookup(hit_ds)
    double_lkp     = build_lookup(double_ds)
    split_das_lkp  = build_split_lookup(split_das_ds)
    split_ndas_lkp = build_split_lookup(split_ndas_ds)

    # The JSON stores ONE ordering of each non-pair hand, so non-pair probs are
    # exactly half the correct unordered probability. Multiply by 2 to fix.
    # After doubling, all probs sum to 1.0 (unconditional 3-card deal space).
    #
    # For US rules, the EVs are conditioned on no dealer BJ (DBJ=0), but the
    # probabilities are unconditional and include phantom dealer-BJ deals for
    # ace and ten upcards. Multiply those upcard columns by P(no BJ | upcard)
    # to get the correct active-game probability. ENHC needs no correction
    # because the EVs already carry the dealer-BJ loss via DBJ terms.
    nc = 52 * decks
    if not enhc:
        bj_factors = [1.0] * 10
        bj_factors[0] = 1.0 - (16 * decks) / (nc - 1)   # ace upcard
        bj_factors[9] = 1.0 - (4  * decks) / (nc - 1)   # ten upcard
    else:
        bj_factors = [1.0] * 10

    all_entries = {}
    for (hk, ui), (prob, _) in stand_lkp.items():
        if len(hk) == 2:
            w = (1.0 if hk[0] == hk[1] else 2.0) * bj_factors[ui]
            all_entries[(hk, ui)] = prob * w
    for (hk, ui), (prob, _) in hit_lkp.items():
        if len(hk) == 2 and (hk, ui) not in all_entries:
            w = (1.0 if hk[0] == hk[1] else 2.0) * bj_factors[ui]
            all_entries[(hk, ui)] = prob * w

    total_ev  = 0.0
    sum_e2    = 0.0
    breakdown = {}

    for (hk, ui), prob in all_entries.items():
        hand  = list(hk)
        total = hand_total(hand)
        soft  = is_soft(hand)

        is_pair = len(hand) == 2 and hand[0] == hand[1]
        if is_pair:
            code = pair_matrix.get((ui, hand[0]))
        elif soft:
            code = soft_matrix.get((ui, total))
        else:
            code = hard_matrix.get((ui, total))

        if code is None:
            continue

        ev = ev_for_code(code, hand, ui, stand_lkp, hit_lkp, double_lkp,
                         split_das_lkp, split_ndas_lkp, das, enhc=enhc, decks=decks)
        if ev is None:
            continue

        e2 = _e2(code, hand, ui, stand_lkp, hit_lkp, double_lkp,
                 split_das_lkp, split_ndas_lkp, das, enhc, decks)
        if e2 is None:
            e2 = ev ** 2

        weighted = prob * ev
        total_ev += weighted
        sum_e2   += prob * e2
        breakdown[code] = breakdown.get(code, 0.0) + weighted

    return total_ev, breakdown, sum_e2


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compute overall blackjack player EV under basic strategy.")
    parser.add_argument("--decks",          type=int,   default=6, choices=[1,2,4,6,8])
    parser.add_argument("--s17",            dest="s17",      action="store_true",  default=True)
    parser.add_argument("--h17",            dest="s17",      action="store_false")
    parser.add_argument("--enhc",           dest="enhc",     action="store_true",  default=False)
    parser.add_argument("--us",             dest="enhc",     action="store_false")
    parser.add_argument("--das",            dest="das",      action="store_true",  default=True)
    parser.add_argument("--ndas",           dest="das",      action="store_false")
    parser.add_argument("--surrender",      dest="surrender",action="store_true",  default=True)
    parser.add_argument("--no-surrender",   dest="surrender",action="store_false")
    parser.add_argument("--dealer-bj-prob", type=float, default=None,
                        help="Override dealer BJ probability. Defaults to exact calculation from deck count.")
    args = parser.parse_args()

    stand_ds      = get_dataset(load_json("stand.json"),  "probs", args.decks, args.s17, args.enhc)
    hit_ds        = get_dataset(load_json("hit.json"),    "probs", args.decks, args.s17, args.enhc)
    double_ds     = get_dataset(load_json("double.json"), "probs", args.decks, args.s17, args.enhc)
    split_full    = get_dataset(load_json("split.json"),  "probs", args.decks, args.s17, args.enhc)
    split_das_ds  = split_full["DAS"]
    split_ndas_ds = split_full["nDAS"]

    decision_ev, breakdown, sum_e2 = compute_game_ev(
        stand_ds, hit_ds, double_ds, split_das_ds, split_ndas_ds,
        das=args.das, surrender=args.surrender, decks=args.decks, enhc=args.enhc
    )

    n  = args.decks
    nc = 52 * n

    if args.dealer_bj_prob is not None:
        p_dealer_bj = args.dealer_bj_prob if not args.enhc else 0.0
    else:
        p_dealer_bj = (4*n/nc)*(16*n/(nc-1)) + (16*n/nc)*(4*n/(nc-1)) if not args.enhc else 0.0

    p_player_bj = (4*n/nc)*(16*n/(nc-1)) + (16*n/nc)*(4*n/(nc-1))
    p_dealer_bj_given_player_bj = (
        ((4*n-1)/(nc-2))*((16*n-1)/(nc-3)) +
        ((16*n-1)/(nc-2))*((4*n-1)/(nc-3))
    )
    p_both_bj             = p_player_bj * p_dealer_bj_given_player_bj
    p_dealer_bj_no_player = p_dealer_bj - p_both_bj

    # For US: add dealer-BJ-only loss (-1 per hand) for hands absent from dataset.
    # For ENHC: all BJ losses are already in the EVs; no separate adjustment needed.
    dealer_bj_only_ev = p_dealer_bj_no_player * -1.0 if not args.enhc else 0.0
    total_ev          = decision_ev + dealer_bj_only_ev

    surrender_str = "Late Surrender" if args.surrender else "No Surrender"
    rule_str = (
        f"{args.decks} deck{'s' if args.decks > 1 else ''}, "
        f"{'S17' if args.s17 else 'H17'}, "
        f"{'ENHC' if args.enhc else 'US peek'}, "
        f"{'DAS' if args.das else 'nDAS'}, "
        f"{surrender_str}"
    )

    bet        = 10.0
    hands_hour = 100
    ev_hour    = total_ev * bet * hands_hour

    # E[payout^2]: for US add the dealer-BJ-only hands (payout=-1, absent from dataset)
    e2_total   = sum_e2 + (p_dealer_bj_no_player if not args.enhc else 0.0)
    variance   = e2_total - total_ev ** 2
    sd_hour    = (variance ** 0.5) * bet * (hands_hour ** 0.5)

    print(f"\nRules      : {rule_str}")
    print(f"Player EV  : {total_ev*100:+.4f}%")
    print(f"EV/hour    : ${ev_hour:+.2f}  (${bet:.0f} flat, {hands_hour} hands/hr)")
    print(f"1 SD (68.3%): ${ev_hour - sd_hour:.2f} to ${ev_hour + sd_hour:.2f}")
    print(f"2 SD (95.5%): ${ev_hour - 2*sd_hour:.2f} to ${ev_hour + 2*sd_hour:.2f}")
    print()


if __name__ == "__main__":
    main()