from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import Optional
import pandas as pd

# ---------------------------------------------------------------------------
# DealerSettingsObject
# ---------------------------------------------------------------------------

@dataclass
class DealerSettingsObject:
    decks: int = 6
    S17: bool = True
    ENHC: bool = False
    DAS: bool = True
    drawAces: bool = False
    BJPay: float = 1.5


# ---------------------------------------------------------------------------
# Strategy cache  — converts pd.Series to fast int arrays
# ---------------------------------------------------------------------------
# hard_arr[total]  = action int (0-3) for hard totals 0-21 (indices 0-21)
# soft_arr[total]  = action int for soft totals 0-21

_STAND  = 0
_HIT    = 1
_DOUBLE = 2
_SPLIT  = 3
_NONE   = -1


def _code_to_int(code: str, can_double: bool) -> int:
    c = code.strip().upper()
    if c == "H":  return _HIT
    if c == "S":  return _STAND
    if c in ("D", "DH"): return _DOUBLE if can_double else _HIT
    if c == "DS": return _DOUBLE if can_double else _STAND
    return _NONE


def _build_strategy_arrays(
    hard_choices, soft_choices, das: bool, is_split: bool
) -> tuple[list[int], list[int], list[int], list[int]]:
    """
    Returns (hard_dbl, soft_dbl, hard_nodbl, soft_nodbl):
      - *_dbl:   actions when doubling IS allowed (2-card hand, DAS if split)
      - *_nodbl: actions when doubling is NOT allowed (3+ cards, or split without DAS)
    """
    hard_dbl   = [_NONE] * 22
    soft_dbl   = [_NONE] * 22
    hard_nodbl = [_NONE] * 22
    soft_nodbl = [_NONE] * 22

    if isinstance(hard_choices, pd.Series):
        for total, val in hard_choices.items():
            if 0 <= total <= 21:
                hard_dbl[total]   = _code_to_int(str(val), True)
                hard_nodbl[total] = _code_to_int(str(val), False)
    elif isinstance(hard_choices, list):
        for i, val in enumerate(hard_choices):
            t = i + 4
            if 0 <= t <= 21:
                v = int(val) if val != _NONE else _NONE
                hard_dbl[t] = hard_nodbl[t] = v

    if isinstance(soft_choices, pd.Series):
        for total, val in soft_choices.items():
            if 0 <= total <= 21:
                soft_dbl[total]   = _code_to_int(str(val), True)
                soft_nodbl[total] = _code_to_int(str(val), False)
    elif isinstance(soft_choices, list):
        for i, val in enumerate(soft_choices):
            t = i + 12
            if 0 <= t <= 21:
                v = int(val) if val != _NONE else _NONE
                soft_dbl[t] = soft_nodbl[t] = v

    return hard_dbl, soft_dbl, hard_nodbl, soft_nodbl


# ---------------------------------------------------------------------------
# Fast hand total (no objects)
# ---------------------------------------------------------------------------

def _hand_total(cards: list[int]) -> int:
    t = aces = 0
    for r in cards:
        if r == 1:
            t += 11; aces += 1
        else:
            t += r
    while t > 21 and aces > 0:
        t -= 10; aces -= 1
    return t


def _hand_is_soft(cards: list[int]) -> bool:
    t = aces = 0
    for r in cards:
        if r == 1:
            t += 11; aces += 1
        else:
            t += r
    while t > 21 and aces > 0:
        t -= 10; aces -= 1
    return aces > 0


# ---------------------------------------------------------------------------
# Shoe  — numpy-backed for fast bulk random draws
# ---------------------------------------------------------------------------

class Shoe:
    """
    Shoe backed by an integer count array.
    Each draw calls random.randrange directly for correctness.
    """
    __slots__ = ("deck_number", "counts", "_total")

    def __init__(self, deck_number: int) -> None:
        self.deck_number = deck_number
        self.counts = [0] * 11
        self.counts[10] = deck_number * 16
        for r in range(1, 10):
            self.counts[r] = deck_number * 4
        self._total: int = deck_number * 52

    def _pop_rank(self, r: int) -> None:
        self.counts[r] -= 1
        self._total -= 1

    def _pick_weighted(self) -> int:
        pick = random.randrange(self._total)
        for r in range(1, 11):
            pick -= self.counts[r]
            if pick < 0:
                return r
        return 10

    def top_pop(self, rank: Optional[int] = None) -> int:
        if rank is not None:
            if self.counts[rank] == 0:
                raise ValueError(f"No card of rank {rank} in shoe")
            self._pop_rank(rank)
            return rank
        r = self._pick_weighted()
        self._pop_rank(r)
        return r

    def remove_one_not(self, exclude_rank: int) -> None:
        total_excl = self._total - self.counts[exclude_rank]
        if total_excl == 0:
            raise ValueError(f"No card excluding rank {exclude_rank} in shoe")
        pick = random.randrange(total_excl)
        for r in range(1, 11):
            if r == exclude_rank:
                continue
            pick -= self.counts[r]
            if pick < 0:
                self._pop_rank(r)
                return

    def size(self) -> int:
        return self._total

    def empty(self) -> bool:
        return self._total == 0


# ---------------------------------------------------------------------------
# Hand / Dealer  — plain integer lists, no objects
# ---------------------------------------------------------------------------

class Hand:
    __slots__ = ("cards", "bet")

    def __init__(self, cards: list[int], bet: float) -> None:
        self.cards: list[int] = list(cards)
        self.bet = bet

    def total(self) -> int:        return _hand_total(self.cards)
    def is_soft(self) -> bool:     return _hand_is_soft(self.cards)
    def is_blackjack(self) -> bool: return len(self.cards) == 2 and self.total() == 21
    def hit(self, r: int) -> None: self.cards.append(r)
    def is_bust(self) -> bool:     return self.total() > 21

    def can_split(self) -> bool:
        return len(self.cards) == 2 and self.cards[0] == self.cards[1]

    def split(self, c1: int, c2: int) -> "Hand":
        sr = self.cards.pop()
        self.cards.append(c1)
        return Hand([sr, c2], self.bet)


class Dealer:
    __slots__ = ("cards", "S17")

    def __init__(self, up: int, s17: bool) -> None:
        self.cards: list[int] = [up]
        self.S17 = s17

    def total(self) -> int:         return _hand_total(self.cards)
    def is_soft(self) -> bool:      return _hand_is_soft(self.cards)
    def is_blackjack(self) -> bool: return len(self.cards) == 2 and self.total() == 21
    def hit(self, r: int) -> None:  self.cards.append(r)
    def is_bust(self) -> bool:      return self.total() > 21

    def stop(self) -> bool:
        t = self.total()
        if t > 17: return True
        if t < 17: return False
        if self.is_soft(): return self.S17
        return True


# ---------------------------------------------------------------------------
# BlackjackSimulator
# ---------------------------------------------------------------------------

class BlackjackSimulator:
    STAND  = _STAND
    HIT    = _HIT
    DOUBLE = _DOUBLE
    SPLIT  = _SPLIT

    def __init__(self, rules: DealerSettingsObject) -> None:
        self.rules = rules
        self.shoe = Shoe(0)
        self.hands: list[Hand] = []
        self.dealer = Dealer(1, rules.S17)
        # Cached integer strategy arrays (rebuilt per start_sim call if needed)
        self._hard_dbl:   list[int] = [_NONE] * 22
        self._soft_dbl:   list[int] = [_NONE] * 22
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
        self.shoe     = Shoe(self.rules.decks)
        self.gain     = 0.0
        self.current_hand = 0

        # Rebuild strategy cache only when choices change (id-based cache key)
        cache_key = (id(hard_choices), id(soft_choices))
        if cache_key != self._strategy_cache_key:
            (self._hard_dbl, self._soft_dbl,
             self._hard_nodbl, self._soft_nodbl) = _build_strategy_arrays(
                hard_choices, soft_choices, self.rules.DAS, is_split=False
            )
            self._strategy_cache_key = cache_key

        player_ranks = [self.shoe.top_pop(r) for r in hand]
        d1 = self.shoe.top_pop(up_card)
        self.dealer = Dealer(d1, self.rules.S17)

        bet = 2.0 if choice == _DOUBLE else 1.0
        self.hands = [Hand(player_ranks, bet)]

        # US peek
        if not self.rules.ENHC and up_card in (1, 10):
            hole = self.shoe.top_pop()
            self.dealer.hit(hole)
            if self.dealer.is_blackjack():
                self.gain = math.nan
                return self.gain

        self._play(choice, is_first=True)
        return self.gain

    # ── play loop ─────────────────────────────────────────────────────

    def _play(self, choice: int, is_first: bool = False) -> None:
        if is_first:
            self._act(choice, split_depth=0)

        while self.current_hand < len(self.hands):
            hand = self.hands[self.current_hand]
            is_split = len(self.hands) > 1
            choice = self._strategy(hand, is_split)
            if choice == _NONE:
                self.current_hand += 1
            else:
                self._act(choice, split_depth=1 if is_split else 0)

        self._dealer_play()
        self._settle()

    def _strategy(self, hand: Hand, is_split: bool) -> int:
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

    def _act(self, choice: int, split_depth: int) -> None:
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

        # Auto-advance past bust
        if (self.current_hand < len(self.hands)
                and self.hands[self.current_hand].is_bust()):
            self.current_hand += 1

    def _dealer_play(self) -> None:
        is_natural = self.hands[0].is_blackjack() and len(self.hands) == 1

        if len(self.dealer.cards) < 2:
            self.dealer.hit(self.shoe.top_pop())

        if self.rules.ENHC and is_natural:
            return

        if any(not is_natural and not h.is_bust() for h in self.hands):
            while not self.dealer.stop():
                self.dealer.hit(self.shoe.top_pop())

    def _settle(self) -> None:
        is_natural = self.hands[0].is_blackjack() and len(self.hands) == 1
        d_total = self.dealer.total()
        d_bust  = self.dealer.is_bust()

        for hand in self.hands:
            if hand.is_bust():
                self.gain -= hand.bet
            elif d_bust:
                self.gain += hand.bet
            elif hand.total() < d_total:
                self.gain -= hand.bet
            elif hand.total() > d_total:
                self.gain += self.rules.BJPay if is_natural else hand.bet

    # ── backwards-compat aliases ──────────────────────────────────────

    def _play_sim(self, choice: int) -> None:  self._play(choice, is_first=True)
    def play_sim(self, choice: int) -> None:   self._play(choice, is_first=True)
    def _dealer_hit(self) -> None:             self._dealer_play()
    def dealer_hit(self) -> None:              self._dealer_play()
    def _win_loss(self) -> None:               self._settle()
    def win_loss(self) -> None:                self._settle()


# ---------------------------------------------------------------------------
# Compatibility shim
# ---------------------------------------------------------------------------

class Card:
    __slots__ = ("rank",)

    def __init__(self, rank: int) -> None:
        self.rank = rank

    def get_rank(self) -> int:
        if 11 <= self.rank <= 13: return 10
        if self.rank == 1:        return 11
        return self.rank

    def is_ace(self) -> bool:
        return self.rank == 1