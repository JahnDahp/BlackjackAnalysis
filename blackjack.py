from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import Optional
import pandas as pd



@dataclass
class DealerSettingsObject:
  decks: int = 6
  S17: bool = True
  ENHC: bool = False
  DAS: bool = True
  drawAces: bool = False
  BJPay: float = 1.5



_STAND = 0
_HIT = 1
_DOUBLE = 2
_SPLIT = 3
_NONE = -1



def code_to_int(code: str, can_double: bool) -> int:
  c = code.strip().upper()
  if c == "H": return _HIT
  if c == "S": return _STAND
  if c in ("D", "DH"): return _DOUBLE if can_double else _HIT
  if c == "DS": return _DOUBLE if can_double else _STAND
  return _NONE



def build_strategy_arrays(
  hard_choices, soft_choices, das: bool, is_split: bool
) -> tuple[list[int], list[int], list[int], list[int]]:
  hard_dbl = [_NONE] * 22
  soft_dbl = [_NONE] * 22
  hard_nodbl = [_NONE] * 22
  soft_nodbl = [_NONE] * 22

  if isinstance(hard_choices, pd.Series):
    for total, val in hard_choices.items():
      if 0 <= total <= 21:
        hard_dbl[total] = code_to_int(str(val), True)
        hard_nodbl[total] = code_to_int(str(val), False)
  elif isinstance(hard_choices, list):
    for i, val in enumerate(hard_choices):
      t = i + 4  # hard totals start at 4 (min hand: 2+2)
      if 0 <= t <= 21:
        v = int(val) if val != _NONE else _NONE
        hard_dbl[t] = hard_nodbl[t] = v

  if isinstance(soft_choices, pd.Series):
    for total, val in soft_choices.items():
      if 0 <= total <= 21:
        soft_dbl[total] = code_to_int(str(val), True)
        soft_nodbl[total] = code_to_int(str(val), False)
  elif isinstance(soft_choices, list):
    for i, val in enumerate(soft_choices):
      t = i + 12  # soft totals start at 12 (min hand: A+A)
      if 0 <= t <= 21:
        v = int(val) if val != _NONE else _NONE
        soft_dbl[t] = soft_nodbl[t] = v

  return hard_dbl, soft_dbl, hard_nodbl, soft_nodbl



def hand_total(cards: list[int]) -> int:
  total = aces = 0
  for rank in cards:
    if rank == 1:
      total += 11; aces += 1
    else:
      total += rank
  while total > 21 and aces > 0:
    total -= 10; aces -= 1
  return total



def hand_is_soft(cards: list[int]) -> bool:
  total = aces = 0
  for rank in cards:
    if rank == 1:
      total += 11; aces += 1
    else:
      total += rank
  while total > 21 and aces > 0:
    total -= 10; aces -= 1
  return aces > 0



class Shoe:
  __slots__ = ("deck_number", "counts", "_total")

  def __init__(self, deck_number: int) -> None:
    self.deck_number = deck_number
    self.counts = [0] * 11
    self.counts[10] = deck_number * 16  # 10/J/Q/K all map to rank 10
    for rank in range(1, 10):
      self.counts[rank] = deck_number * 4
    self._total: int = deck_number * 52

  def pop_rank(self, rank: int) -> None:
    self.counts[rank] -= 1
    self._total -= 1

  def pick_weighted(self) -> int:
    pick = random.randrange(self._total)
    for rank in range(1, 11):
      pick -= self.counts[rank]
      if pick < 0:
        return rank
    return 10

  def top_pop(self, rank: Optional[int] = None) -> int:
    if rank is not None:
      if self.counts[rank] == 0:
        raise ValueError(f"No card of rank {rank} in shoe")
      self.pop_rank(rank)
      return rank
    rank = self.pick_weighted()
    self.pop_rank(rank)
    return rank

  def remove_one_not(self, exclude_rank: int) -> None:
    total_excl = self._total - self.counts[exclude_rank]
    if total_excl == 0:
      raise ValueError(f"No card excluding rank {exclude_rank} in shoe")
    pick = random.randrange(total_excl)
    for rank in range(1, 11):
      if rank == exclude_rank:
        continue
      pick -= self.counts[rank]
      if pick < 0:
        self.pop_rank(rank)
        return

  def size(self) -> int:
    return self._total

  def empty(self) -> bool:
    return self._total == 0



class Hand:
  __slots__ = ("cards", "bet")

  def __init__(self, cards: list[int], bet: float) -> None:
    self.cards: list[int] = list(cards)
    self.bet = bet

  def total(self) -> int: return hand_total(self.cards)

  def is_soft(self) -> bool: return hand_is_soft(self.cards)

  def is_blackjack(self) -> bool: return len(self.cards) == 2 and self.total() == 21

  def hit(self, rank: int) -> None: self.cards.append(rank)

  def is_bust(self) -> bool: return self.total() > 21

  def can_split(self) -> bool:
    return len(self.cards) == 2 and self.cards[0] == self.cards[1]

  def split(self, c1: int, c2: int) -> "Hand":
    split_rank = self.cards.pop()
    self.cards.append(c1)
    return Hand([split_rank, c2], self.bet)



class Dealer:
  __slots__ = ("cards", "S17")

  def __init__(self, up: int, s17: bool) -> None:
    self.cards: list[int] = [up]
    self.S17 = s17

  def total(self) -> int: return hand_total(self.cards)

  def is_soft(self) -> bool: return hand_is_soft(self.cards)

  def is_blackjack(self) -> bool: return len(self.cards) == 2 and self.total() == 21

  def hit(self, rank: int) -> None: self.cards.append(rank)

  def is_bust(self) -> bool: return self.total() > 21

  def stop(self) -> bool:
    total = self.total()
    if total > 17: return True
    if total < 17: return False
    if self.is_soft(): return self.S17
    return True



class BlackjackSimulator:
  STAND = _STAND
  HIT = _HIT
  DOUBLE = _DOUBLE
  SPLIT = _SPLIT

  def __init__(self, rules: DealerSettingsObject) -> None:
    self.rules = rules
    self.shoe = Shoe(0)
    self.hands: list[Hand] = []
    self.dealer = Dealer(1, rules.S17)
    self._hard_dbl: list[int] = [_NONE] * 22
    self._soft_dbl: list[int] = [_NONE] * 22
    self._hard_nodbl: list[int] = [_NONE] * 22
    self._soft_nodbl: list[int] = [_NONE] * 22
    self._strategy_cache_key: tuple = (-1, -1)
    self.current_hand = 0
    self.gain = 0.0

  def start_sim(
    self,
    hand: list[int],
    up_card: int,
    choice: int,
    hard_choices,
    soft_choices,
  ) -> float:
    self.shoe = Shoe(self.rules.decks)
    self.gain = 0.0
    self.current_hand = 0

    cache_key = (id(hard_choices), id(soft_choices))
    if cache_key != self._strategy_cache_key:
      (self._hard_dbl, self._soft_dbl,
       self._hard_nodbl, self._soft_nodbl) = build_strategy_arrays(
        hard_choices, soft_choices, self.rules.DAS, is_split=False
      )
      self._strategy_cache_key = cache_key

    player_ranks = [self.shoe.top_pop(r) for r in hand]
    d1 = self.shoe.top_pop(up_card)
    self.dealer = Dealer(d1, self.rules.S17)

    bet = 2.0 if choice == _DOUBLE else 1.0
    self.hands = [Hand(player_ranks, bet)]

    if not self.rules.ENHC and up_card in (1, 10):
      hole = self.shoe.top_pop()
      self.dealer.hit(hole)
      if self.dealer.is_blackjack():
        self.gain = math.nan
        return self.gain

    self.play(choice, is_first=True)
    return self.gain



  def play(self, choice: int, is_first: bool = False) -> None:
    if is_first:
      self.act(choice, split_depth=0)

    while self.current_hand < len(self.hands):
      hand = self.hands[self.current_hand]
      is_split = len(self.hands) > 1
      choice = self.strategy(hand, is_split)
      if choice == _NONE:
        self.current_hand += 1
      else:
        self.act(choice, split_depth=1 if is_split else 0)

    self.dealer_play()
    self.settle()

  def strategy(self, hand: Hand, is_split: bool) -> int:
    if len(hand.cards) < 2:
      return _HIT
    t = hand.total()
    soft = hand.is_soft()
    can_dbl = len(hand.cards) == 2 and (not is_split or self.rules.DAS)
    if can_dbl:
      arr = self._soft_dbl if soft else self._hard_dbl
    else:
      arr = self._soft_nodbl if soft else self._hard_nodbl
    return arr[t] if 0 <= t <= 21 else _NONE

  def act(self, choice: int, split_depth: int) -> None:
    hand = self.hands[self.current_hand]

    if choice in (_HIT, _DOUBLE):
      hand.hit(self.shoe.top_pop())

    if choice == _DOUBLE:
      hand.bet *= 2.0

    if choice in (_STAND, _DOUBLE):
      self.current_hand += 1
      return

    if choice == _SPLIT:
      c1 = self.shoe.top_pop()
      c2 = self.shoe.top_pop()
      new_hand = hand.split(c1, c2)
      self.hands.append(new_hand)
      if hand.cards[0] == 1 and not self.rules.drawAces:
        self.current_hand = len(self.hands)
        return

    if (self.current_hand < len(self.hands)
        and self.hands[self.current_hand].is_bust()):
      self.current_hand += 1

  def dealer_play(self) -> None:
    is_natural = self.hands[0].is_blackjack() and len(self.hands) == 1

    if len(self.dealer.cards) < 2:
      self.dealer.hit(self.shoe.top_pop())

    if self.rules.ENHC and is_natural:
      return

    if any(not is_natural and not h.is_bust() for h in self.hands):
      while not self.dealer.stop():
        self.dealer.hit(self.shoe.top_pop())

  def settle(self) -> None:
    is_natural = self.hands[0].is_blackjack() and len(self.hands) == 1
    dealer_total = self.dealer.total()
    dealer_bust = self.dealer.is_bust()

    for hand in self.hands:
      if hand.is_bust():
        self.gain -= hand.bet
      elif dealer_bust:
        self.gain += hand.bet
      elif hand.total() < dealer_total:
        self.gain -= hand.bet
      elif hand.total() > dealer_total:
        self.gain += self.rules.BJPay if is_natural else hand.bet




