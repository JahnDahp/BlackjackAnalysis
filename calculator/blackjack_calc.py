from __future__ import annotations
import json
import os


class DealerSettingsObject:
  def __init__(self, decks=6, S17=True, ENHC=False, DAS=True):
    self.decks=decks; self.S17=S17; self.ENHC=ENHC; self.DAS=DAS



# Tracks card counts and total for efficient shoe manipulation
class ShoeCount:
  __slots__ = ("counts", "total")

  def __init__(self, decks):
    self.counts = [0] * 11
    self.counts[10] = decks * 16
    for rank in range(1, 10):
      self.counts[rank] = decks * 4
    self.total = decks * 52

  @classmethod
  def from_counts(calculator_class, counts):
    instance = calculator_class.__new__(calculator_class)
    instance.counts = list(counts)
    instance.total = sum(counts[rank] for rank in range(1, len(counts)))
    return instance

  def copy(self): return ShoeCount.from_counts(self.counts)

  def remove(self, rank): self.counts[rank] -= 1; self.total -= 1

  def restore(self, rank): self.counts[rank] += 1; self.total += 1

  def count(self, rank): return self.counts[rank]

  def prob(self, rank): return self.counts[rank] / self.total if self.total else 0.0

  def cache_key(self): return tuple(self.counts)



# Fast hand total helpers that operate on rank tuples rather than card objects
def total_ranks(ranks):
  total = 0; aces = 0
  for rank in ranks:
    if rank == 1: total += 11; aces += 1
    else: total += rank
  while total > 21 and aces > 0: total -= 10; aces -= 1
  return total

def is_soft_ranks(ranks):
  total = 0; aces = 0
  for rank in ranks:
    if rank == 1: total += 11; aces += 1
    else: total += rank
  while total > 21 and aces > 0: total -= 10; aces -= 1
  return aces > 0



class Calculator:
  def __init__(self, dealer_settings):
    self.dealer_settings = dealer_settings
    self.dealer_data=None; self.stand_data=None; self.hit_data=None
    self.double_data=None; self.split_data=None; self.dealer_cache={}

  @classmethod
  def create(calculator_class, dealer_settings):
    instance = calculator_class(dealer_settings)
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Data")
    def read(filename):
      with open(os.path.join(data_dir, filename), "r") as file:
        return json.load(file)
    instance.dealer_data = read("dealer.json")
    instance.stand_data = read("stand.json")
    instance.hit_data = read("hit.json")
    instance.double_data = read("double.json")
    instance.split_data = read("split.json")
    return instance



  # Data retrieval helpers
  def get_data_set(self, data):
    deck_map = {1:"oneDeck",2:"twoDeck",4:"fourDeck",6:"sixDeck",8:"eightDeck"}
    return data[deck_map[self.dealer_settings.decks]]["S17" if self.dealer_settings.S17 else "H17"]["enhc" if self.dealer_settings.ENHC else "us"]

  def get_dealer_data(self):
    return self.get_data_set(self.dealer_data["outcomes"])

  def get_hand_index(self, hand, data):
    hand_sorted = sorted(hand)
    for index in range(len(data)):
      if sorted(data[index][0]) == hand_sorted: return index
    return -1

  def get_data(self, cards, up_card, data):
    dataset = self.get_data_set(data["probs"])
    key = "soft" if self.is_soft(cards) else "hard"
    index = self.get_hand_index(cards, dataset[key][up_card - 1])
    if index == -1: print("No hand in data")
    return dataset[key][up_card - 1][index][2]



  # Hand helpers
  def total(self, cards):
    total = 0; aces = 0
    for card in cards:
      if card == 1: total += 11; aces += 1
      else: total += card
    while total > 21 and aces > 0: total -= 10; aces -= 1
    return total

  def is_soft(self, cards):
    total = 0; aces = 0
    for card in cards:
      if card == 1: total += 11; aces += 1
      else: total += card
    while total > 21 and aces > 0: total -= 10; aces -= 1
    return aces > 0

  def can_double(self, cards): return len(cards) == 2

  def is_blackjack(self, cards, exclude_cards):
    return len(cards) == 2 and self.total(cards) == 21 and exclude_cards is None

  def hands_equal(self, a, b): return sorted(a) == sorted(b)

  def normalize(self, arr):
    total = sum(arr)
    if total == 0: return arr
    return [x / total for x in arr]

  def gen_shoe(self):
    shoe=[]
    for _ in range(self.dealer_settings.decks):
      for _ in range(4):
        for rank in range(1, 14):
          shoe.append(10 if rank >= 11 else rank)
    return shoe

  def remove_cards_from_shoe(self, shoe, cards, prob=None):
    for card in cards:
      count = sum(1 for existing_card in shoe if existing_card == card)
      if count == 0: print(f"No {card} card found in shoe!")
      if prob is not None: prob *= count / len(shoe)
      index = -1
      for i in range(len(shoe)):
        if shoe[i] == card: index = i; break
      shoe.pop(index)
    return prob



  # Dealer simulation
  def get_dealer_outcomes_cached(self, up_card, shoe):
    cache_key = (up_card,) + shoe.cache_key()
    cached = self.dealer_cache.get(cache_key)
    if cached is not None: return cached
    probs=[]
    self.dealer_recurse((up_card,), shoe, 1.0, probs)
    result = self.aggregate_dealer_probs(probs)
    self.dealer_cache[cache_key] = result
    return result

  def dealer_recurse(self, hand, shoe, probability, results, player_bj=False):
    if player_bj and len(hand) >= 2:
      results.append((hand, probability)); return
    hand_total = total_ranks(hand)
    soft17 = (hand_total == 17 and is_soft_ranks(hand))
    if hand_total > 17 or (hand_total == 17 and (not soft17 or self.dealer_settings.S17)):
      results.append((hand, probability)); return
    for rank in range(1, 11):
      count = shoe.count(rank)
      if count == 0: continue
      rank_prob = count / shoe.total
      shoe.remove(rank)
      self.dealer_recurse(hand + (rank,), shoe, probability * rank_prob, results, player_bj)
      shoe.restore(rank)

  def aggregate_dealer_probs(self, results, normalize_flag=False):
    counts = [0.0] * 7
    for hand, probability in results:
      hand_total = total_ranks(hand)
      if 17 <= hand_total <= 20: counts[hand_total - 16] += probability
      elif hand_total == 21: counts[6 if len(hand) == 2 else 5] += probability
      else: counts[0] += probability
    if not self.dealer_settings.ENHC: counts[6] = 0.0
    if normalize_flag: return self.normalize(counts)
    return counts

  def run_dealer_sim(self, normalize=False):
    results = []
    for up_card in range(1, 11):
      shoe = ShoeCount(self.dealer_settings.decks)
      up_card_prob = shoe.prob(up_card)
      shoe.remove(up_card)
      probs=[]
      self.dealer_recurse((up_card,), shoe, up_card_prob, probs)
      counts = self.aggregate_dealer_probs(probs, normalize_flag=normalize)
      results.append(counts)
    return results

  def run_dealer_sim_given_cards(self, cards, dealer_upcard, exclude_cards=None, split=False):
    shoe = ShoeCount(self.dealer_settings.decks)
    is_bj = self.total(cards) == 21 and len(cards) == 2 and exclude_cards is None and not split
    if exclude_cards:
      for card in exclude_cards: shoe.remove(card)
    for card in cards: shoe.remove(card)
    shoe.remove(dealer_upcard)
    if is_bj:
      probs=[]
      self.dealer_recurse((dealer_upcard,), shoe, 1.0, probs, True)
      return self.aggregate_dealer_probs(probs)
    return self.get_dealer_outcomes_cached(dealer_upcard, shoe)



  # Stand EV
  def stand_from_shoe(self, hand_ranks, up_card, shoe):
    hand_total = total_ranks(hand_ranks)
    if hand_total > 21: return (0.0, 0.0, 1.0, 0.0)
    dealer_probs = self.get_dealer_outcomes_cached(up_card, shoe)
    dbj = dealer_probs[6] if self.dealer_settings.ENHC else 0.0

    win = 0.0; tie = 0.0; lose = 0.0; outcome = 0
    win += dealer_probs[outcome]; outcome += 1
    while hand_total > outcome + 16 and outcome < 6:
      win += dealer_probs[outcome]; outcome += 1
    if hand_total == outcome + 16 and outcome < 6:
      tie = dealer_probs[outcome]; outcome += 1
    while hand_total < outcome + 16 and outcome < 6:
      lose += dealer_probs[outcome]; outcome += 1

    total_prob = win + tie + lose + dbj
    if total_prob: win /= total_prob; tie /= total_prob; lose /= total_prob; dbj /= total_prob
    return (win, tie, lose, dbj)

  def calc_stand(self, cards, up_card, exclude_cards=None, split=False):
    hand_total = self.total(cards)
    if hand_total > 21: return {"winProb": 0.0, "tieProb": 0.0, "loseProb": 1.0, "DBJ": 0.0}
    dealer_probs = self.run_dealer_sim_given_cards(cards, up_card, exclude_cards, split)
    dbj = dealer_probs[6] if self.dealer_settings.ENHC else 0.0

    if self.is_blackjack(cards, exclude_cards):
      win_prob = 1.0 - dbj; total_prob = win_prob + dbj
      if total_prob: win_prob /= total_prob; dbj /= total_prob
      return {"winProb": win_prob, "tieProb": 0.0, "loseProb": 0.0, "DBJ": dbj}

    win_prob = 0.0; tie_prob = 0.0; lose_prob = 0.0; outcome = 0
    win_prob += dealer_probs[outcome]; outcome += 1
    while hand_total > outcome + 16 and outcome < 6:
      win_prob += dealer_probs[outcome]; outcome += 1
    if hand_total == outcome + 16 and outcome < 6:
      tie_prob = dealer_probs[outcome]; outcome += 1
    while hand_total < outcome + 16 and outcome < 6:
      lose_prob += dealer_probs[outcome]; outcome += 1

    total_prob = win_prob + tie_prob + lose_prob + dbj
    if total_prob: win_prob /= total_prob; tie_prob /= total_prob; lose_prob /= total_prob; dbj /= total_prob
    return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

  def calc_stand_ev(self, hand, stand, exclude_cards=None, split=False):
    if self.is_blackjack(hand, exclude_cards) and not split:
      return (1.0 - stand["DBJ"]) * 1.5
    return stand["winProb"] - stand["loseProb"] - stand["DBJ"]

  def calc_stand_variance(self, hand, stand, exclude_cards=None):
    if self.is_blackjack(hand, exclude_cards):
      return 1.5 ** 2 * stand["DBJ"] * (1.0 - stand["DBJ"])
    return 1.0 - stand["tieProb"] - self.calc_stand_ev(hand, stand, exclude_cards) ** 2



  # Hit EV
  def get_next_card_probs_fast(self, shoe, up_card):
    # For US peek rules, conditions out dealer blackjack for A and 10 upcards
    probs = []; enhc = self.dealer_settings.ENHC; shoe_total = shoe.total
    if up_card == 10 and not enhc:
      ace_count = shoe.count(1)
      for rank in range(1, 11):
        rank_count = shoe.count(rank)
        if rank == 1: probs.append(ace_count / (shoe_total - 1) if shoe_total > 1 else 0.0)
        else:
          non_ace_count = shoe_total - ace_count
          probs.append(rank_count * (1.0 - (1.0 / non_ace_count if non_ace_count else 0.0)) / (shoe_total - 1) if shoe_total > 1 else 0.0)
    elif up_card == 1 and not enhc:
      ten_count = shoe.count(10)
      for rank in range(1, 11):
        rank_count = shoe.count(rank)
        if rank == 10: probs.append(ten_count / (shoe_total - 1) if shoe_total > 1 else 0.0)
        else:
          non_ten_count = shoe_total - ten_count
          probs.append(rank_count * (1.0 - (1.0 / non_ten_count if non_ten_count else 0.0)) / (shoe_total - 1) if shoe_total > 1 else 0.0)
    else:
      for rank in range(1, 11):
        probs.append(shoe.count(rank) / shoe_total if shoe_total else 0.0)
    return probs

  def get_next_card_prob(self, shoe, up_card):
    shoe_count = ShoeCount(0); shoe_count.counts = [0] * 11; shoe_count.total = len(shoe)
    for card in shoe: shoe_count.counts[card] += 1
    return self.get_next_card_probs_fast(shoe_count, up_card)

  def hit_from_shoe(self, hand_ranks, up_card, shoe):
    win = 0.0; tie = 0.0; lose = 0.0; dbj = 0.0
    next_card_probs = self.get_next_card_probs_fast(shoe, up_card)
    for rank in range(1, 11):
      if shoe.count(rank) == 0: continue
      rank_prob = next_card_probs[rank - 1]
      if rank_prob == 0.0: continue
      new_hand = hand_ranks + (rank,)
      new_total = total_ranks(new_hand)
      if new_total > 21: lose += rank_prob; continue

      shoe.remove(rank)
      stand_result = self.stand_from_shoe(new_hand, up_card, shoe)
      s_win = stand_result[0]; s_tie = stand_result[1]
      s_lose = stand_result[2]; s_dbj = stand_result[3]
      stand_ev = s_win - s_lose - s_dbj
      hit_result = self.hit_from_shoe(new_hand, up_card, shoe)
      hit_ev = hit_result["winProb"] - hit_result["loseProb"] - hit_result["DBJ"]
      shoe.restore(rank)

      if stand_ev >= hit_ev:
        win += s_win * rank_prob; tie += s_tie * rank_prob
        lose += s_lose * rank_prob; dbj += s_dbj * rank_prob
      else:
        win += hit_result["winProb"] * rank_prob; tie += hit_result["tieProb"] * rank_prob
        lose += hit_result["loseProb"] * rank_prob; dbj += hit_result["DBJ"] * rank_prob

    total_prob = win + tie + lose + dbj
    if total_prob: win /= total_prob; tie /= total_prob; lose /= total_prob; dbj /= total_prob
    return {"winProb": win, "tieProb": tie, "loseProb": lose, "DBJ": dbj}

  def calc_hit(self, cards, up_card, exclude_cards=None):
    if self.total(cards) > 21: return {"winProb": 0.0, "tieProb": 0.0, "loseProb": 1.0, "DBJ": 0.0}
    shoe = ShoeCount(self.dealer_settings.decks)
    if exclude_cards:
      for card in exclude_cards: shoe.remove(card)
    for card in cards: shoe.remove(card)
    shoe.remove(up_card)
    return self.hit_from_shoe(tuple(cards), up_card, shoe)

  def calc_hit_ev(self, hit): return hit["winProb"] - hit["loseProb"] - hit["DBJ"]

  def calc_hit_variance(self, hit): return 1.0 - hit["tieProb"] - self.calc_hit_ev(hit) ** 2



  # Double EV
  def double_from_shoe(self, hand_ranks, up_card, shoe):
    next_card_probs = self.get_next_card_probs_fast(shoe, up_card)
    win = 0.0; tie = 0.0; lose = 0.0; dbj = 0.0
    for rank in range(1, 11):
      if shoe.count(rank) == 0: continue
      rank_prob = next_card_probs[rank - 1]
      if rank_prob == 0.0: continue
      new_hand = hand_ranks + (rank,)
      if total_ranks(new_hand) > 21: lose += rank_prob; continue
      shoe.remove(rank)
      stand_result = self.stand_from_shoe(new_hand, up_card, shoe)
      shoe.restore(rank)
      win += stand_result[0] * rank_prob; tie += stand_result[1] * rank_prob
      lose += stand_result[2] * rank_prob; dbj += stand_result[3] * rank_prob

    total_prob = win + tie + lose + dbj
    if total_prob: win /= total_prob; tie /= total_prob; lose /= total_prob; dbj /= total_prob
    return {"winProb": win, "tieProb": tie, "loseProb": lose, "DBJ": dbj}

  def calc_double(self, cards, up_card, exclude_cards=None):
    shoe = ShoeCount(self.dealer_settings.decks)
    if exclude_cards:
      for card in exclude_cards: shoe.remove(card)
    for card in cards: shoe.remove(card)
    shoe.remove(up_card)
    return self.double_from_shoe(tuple(cards), up_card, shoe)

  def calc_double_ev(self, double): return 2.0 * (double["winProb"] - double["loseProb"] - double["DBJ"])

  def calc_double_variance(self, double): return 4.0 * (1.0 - double["tieProb"]) - self.calc_double_ev(double) ** 2



  # Split EV
  def calc_split(self, cards, up_card, exclude_cards=None):
    empty = {"winProb": 0.0, "tieProb": 0.0, "loseProb": 0.0, "DBJ": 0.0}
    hand_probs = {"noDouble": dict(empty), "double": dict(empty)}
    if len(cards) != 2 or cards[0] != cards[1]: return hand_probs

    self.dealer_cache = {}
    shoe = ShoeCount(self.dealer_settings.decks)
    if exclude_cards:
      for card in exclude_cards: shoe.remove(card)
    for card in cards: shoe.remove(card)
    shoe.remove(up_card)
    pair_rank = cards[0]

    shoe_total = shoe.total
    next_card_probs = [shoe.count(rank) / shoe_total if shoe_total else 0.0 for rank in range(1, 11)]
    for rank in range(1, 11):
      if shoe.count(rank) == 0: continue
      rank_prob = next_card_probs[rank - 1]
      if rank_prob == 0.0: continue
      shoe.remove(rank)
      hand_ranks = (pair_rank, rank)

      if pair_rank == 1:
        # Forced stand on split aces
        stand_result = self.stand_from_shoe(hand_ranks, up_card, shoe)
        hand_probs["noDouble"]["winProb"] += stand_result[0] * rank_prob; hand_probs["noDouble"]["tieProb"] += stand_result[1] * rank_prob
        hand_probs["noDouble"]["loseProb"] += stand_result[2] * rank_prob; hand_probs["noDouble"]["DBJ"] += stand_result[3] * rank_prob
      else:
        stand_result = self.stand_from_shoe(hand_ranks, up_card, shoe)
        hit_result = self.hit_from_shoe(hand_ranks, up_card, shoe)
        double_result = self.double_from_shoe(hand_ranks, up_card, shoe)
        stand_ev = stand_result[0] - stand_result[2] - stand_result[3]
        hit_ev = hit_result["winProb"] - hit_result["loseProb"] - hit_result["DBJ"]
        double_ev = self.calc_double_ev(double_result)
        max_ev = max(stand_ev, hit_ev, double_ev) if self.dealer_settings.DAS else max(stand_ev, hit_ev)
        if self.dealer_settings.DAS and max_ev == double_ev:
          hand_probs["double"]["winProb"] += double_result["winProb"] * rank_prob; hand_probs["double"]["tieProb"] += double_result["tieProb"] * rank_prob
          hand_probs["double"]["loseProb"] += double_result["loseProb"] * rank_prob; hand_probs["double"]["DBJ"] += double_result["DBJ"] * rank_prob
        elif max_ev == hit_ev:
          hand_probs["noDouble"]["winProb"] += hit_result["winProb"] * rank_prob; hand_probs["noDouble"]["tieProb"] += hit_result["tieProb"] * rank_prob
          hand_probs["noDouble"]["loseProb"] += hit_result["loseProb"] * rank_prob; hand_probs["noDouble"]["DBJ"] += hit_result["DBJ"] * rank_prob
        else:
          hand_probs["noDouble"]["winProb"] += stand_result[0] * rank_prob; hand_probs["noDouble"]["tieProb"] += stand_result[1] * rank_prob
          hand_probs["noDouble"]["loseProb"] += stand_result[2] * rank_prob; hand_probs["noDouble"]["DBJ"] += stand_result[3] * rank_prob
      shoe.restore(rank)

    total_prob = sum(hand_probs[bucket][key] for bucket in ("double","noDouble") for key in ("winProb","tieProb","loseProb","DBJ"))
    if total_prob:
      for bucket in ("double","noDouble"):
        for key in ("winProb","tieProb","loseProb","DBJ"):
          hand_probs[bucket][key] /= total_prob
    return hand_probs

  def calc_split_ev(self, split):
    w2=split["double"]["winProb"]; t2=split["double"]["tieProb"]; l2=split["double"]["loseProb"]; d2=split["double"]["DBJ"]
    w=split["noDouble"]["winProb"]; t=split["noDouble"]["tieProb"]; l=split["noDouble"]["loseProb"]; d=split["noDouble"]["DBJ"]
    if self.dealer_settings.DAS:
      win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2; win1=2*w2*l+2*w*(t+t2)
      lose1=2*l2*w+2*l*(t+t2); lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
      return 4*win4+3*win3+2*win2+win1-2*d-4*d2-lose1-2*lose2-3*lose3-4*lose4
    return 2*w**2+2*w*t-2*d-2*l*t-2*l**2

  def calc_split_variance(self, split):
    w2=split["double"]["winProb"]; t2=split["double"]["tieProb"]; l2=split["double"]["loseProb"]
    w=split["noDouble"]["winProb"]; t=split["noDouble"]["tieProb"]; l=split["noDouble"]["loseProb"]
    ev = self.calc_split_ev(split)
    if self.dealer_settings.DAS:
      win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2
      tie=2*w2*l2+2*w*l+(t+t2)**2
      lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
      return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie-ev**2
    return 1+3*(w**2+l**2)-(2*w*l+t**2)-ev**2



  # Cumulative EV lookups
  def get_split_probs(self):
    splits = []
    das_key = "DAS" if self.dealer_settings.DAS else "nDAS"
    data_set = self.get_data_set(self.split_data["probs"])[das_key]
    for up_card in range(1, 11):
      upcard_results = []
      for pair_val in range(1, 11):
        ev = -99.0
        hand_index = self.get_hand_index([pair_val, pair_val], data_set[up_card - 1])
        if hand_index != -1:
          ev = self.calc_split_ev(data_set[up_card - 1][hand_index][1])
        upcard_results.append(ev)
      splits.append(upcard_results)
    return splits

  def get_cumulative_probs(self, decision):
    data = {"stand": self.stand_data, "hit": self.hit_data, "double": self.double_data}.get(decision)
    def calc_for_totals(soft, total_range):
      table = []
      for up_card in range(1, 11):
        upcard_results = []
        for total_target in total_range:
          candidate_hands = self.run_hand_sim(total_target, up_card, soft)["allHands"]
          evs = []; probs = []
          for hand in candidate_hands:
            if decision == "double" and len(hand["hand"]) > 2: continue
            if self.total(hand["hand"]) == total_target:
              ev_data = self.get_data(hand["hand"], up_card, data)
              evs.append(self.calc_ev(decision, hand["hand"], ev_data))
              probs.append(hand["totalProb"])
          probs = self.normalize(probs)
          upcard_results.append(sum(evs[i]*probs[i] for i in range(len(evs))))
        table.append(upcard_results)
      return table
    return {"hard": calc_for_totals(False, range(4, 22)), "soft": calc_for_totals(True, range(13, 22))}

  def calc_ev(self, decision, hand, ev_data):
    if decision == "stand": return self.calc_stand_ev(hand, ev_data)
    if decision == "hit": return self.calc_hit_ev(ev_data)
    if decision == "double": return self.calc_double_ev(ev_data)
    return self.calc_split_ev(ev_data)



  # Hand composition simulation
  def run_hand_sim(self, total_target, up_card, soft_hands):
    all_hands=[]; next_card_probs = [0.0] * 10; seen_combos=set()
    base_shoe = ShoeCount(self.dealer_settings.decks)

    for player_rank in range(1, 11):
      player_count = base_shoe.count(player_rank)
      if player_count == 0: continue
      player_prob = player_count / base_shoe.total
      shoe_after_player = base_shoe.copy()
      shoe_after_player.remove(player_rank)
      upcard_count = shoe_after_player.count(up_card)
      if upcard_count == 0: continue
      upcard_prob = upcard_count / shoe_after_player.total
      shoe_after_player.remove(up_card)

      def recurse(hand, shoe, probability, min_rank):
        hand_total = total_ranks(hand)
        hand_is_soft = is_soft_ranks(hand)
        if not soft_hands and hand_is_soft and total_target > 11: hand_total -= 10
        if hand_total > total_target: return
        if hand_total == total_target and len(hand) > 1:
          if (soft_hands and hand_is_soft) or (not soft_hands):
            combo_key = ",".join(str(rank) for rank in sorted(hand))
            if combo_key not in seen_combos:
              seen_combos.add(combo_key)
              all_hands.append({"hand": list(hand), "totalProb": probability})
              shoe_total = shoe.total
              for next_rank in range(1, 11):
                if shoe.count(next_rank) == 0: continue
                next_card_probs[next_rank - 1] += (shoe.count(next_rank) / shoe_total) * probability
          return
        shoe_total = shoe.total
        for rank in range(min_rank, 11):
          if shoe.count(rank) == 0: continue
          rank_prob = shoe.count(rank) / shoe_total
          shoe.remove(rank)
          recurse(hand + (rank,), shoe, probability * rank_prob, rank)
          shoe.restore(rank)

      recurse((player_rank,), shoe_after_player, player_prob * upcard_prob, 1)

    total = sum(next_card_probs)
    if total > 0: next_card_probs = [prob / total for prob in next_card_probs]
    return {"allHands": all_hands, "nextCardProbs": next_card_probs}