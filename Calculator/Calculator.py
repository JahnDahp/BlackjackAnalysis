from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class DealerSettingsObject:
    decks: int = 6
    S17: bool = True
    ENHC: bool = False
    DAS: bool = True
    drawAces: bool = False
    BJPay: float = 1.5


@dataclass
class Card:
    rank: int


# ---------------------------------------------------------------------------
# Shoe represented as a count array — O(1) add/remove/count
# ---------------------------------------------------------------------------

class ShoeCount:
    __slots__ = ("counts", "total")

    def __init__(self, decks: int) -> None:
        self.counts = [0] * 11
        self.counts[10] = decks * 16
        for r in range(1, 10):
            self.counts[r] = decks * 4
        self.total = decks * 52

    @classmethod
    def from_counts(cls, counts: list[int]) -> "ShoeCount":
        s = cls.__new__(cls)
        s.counts = list(counts)
        s.total = sum(counts[1:])
        return s

    def copy(self) -> "ShoeCount":
        return ShoeCount.from_counts(self.counts)

    def remove(self, rank: int) -> None:
        self.counts[rank] -= 1
        self.total -= 1

    def restore(self, rank: int) -> None:
        self.counts[rank] += 1
        self.total += 1

    def count(self, rank: int) -> int:
        return self.counts[rank]

    def prob(self, rank: int) -> float:
        return self.counts[rank] / self.total if self.total else 0.0

    def cache_key(self) -> tuple:
        return tuple(self.counts)


# ---------------------------------------------------------------------------
# Fast hand total helpers
# ---------------------------------------------------------------------------

def _total_ranks(ranks: tuple) -> int:
    t = aces = 0
    for r in ranks:
        if r == 1: t += 11; aces += 1
        else: t += r
    while t > 21 and aces > 0: t -= 10; aces -= 1
    return t


def _is_soft_ranks(ranks: tuple) -> bool:
    t = aces = 0
    for r in ranks:
        if r == 1: t += 11; aces += 1
        else: t += r
    while t > 21 and aces > 0: t -= 10; aces -= 1
    return aces > 0


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class Calculator:
    def __init__(self, dealer_settings: DealerSettingsObject) -> None:
        self.dealer_settings = dealer_settings
        self.dealer_data: Any = None
        self.stand_data: Any = None
        self.hit_data: Any = None
        self.double_data: Any = None
        self.split_data: Any = None
        self._dealer_cache: dict = {}

    @classmethod
    def create(cls, dealer_settings: DealerSettingsObject, data_dir: str) -> "Calculator":
        inst = cls(dealer_settings)
        def read(f):
            with open(os.path.join(data_dir, f), "r", encoding="utf-8") as fh:
                return json.load(fh)
        inst.dealer_data  = read("dealer.json")
        inst.stand_data   = read("stand.json")
        inst.hit_data     = read("hit.json")
        inst.double_data  = read("double.json")
        inst.split_data   = read("split.json")
        return inst

    def run_sims(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Data set helpers
    # ------------------------------------------------------------------

    def get_data_set(self, data: Any) -> Any:
        deck_map = {1:"oneDeck",2:"twoDeck",4:"fourDeck",6:"sixDeck",8:"eightDeck"}
        return data[deck_map[self.dealer_settings.decks]][
            "S17" if self.dealer_settings.S17 else "H17"][
            "enhc" if self.dealer_settings.ENHC else "us"]

    def get_dealer_data(self) -> Any:
        return self.get_data_set(self.dealer_data["outcomes"])

    # ------------------------------------------------------------------
    # Shoe helpers (Card-list API kept for compatibility)
    # ------------------------------------------------------------------

    def gen_shoe(self) -> list[Card]:
        shoe: list[Card] = []
        for _ in range(self.dealer_settings.decks):
            for _ in range(4):
                for rank in range(1, 14):
                    shoe.append(Card(rank=10 if rank >= 11 else rank))
        return shoe

    def remove_cards_from_shoe(
        self, shoe: list[Card], cards: list[Card], prob: Optional[float] = None
    ) -> Optional[float]:
        for card in cards:
            cnt = sum(1 for c in shoe if c.rank == card.rank)
            if cnt == 0:
                raise ValueError(f"No {card.rank} card found in shoe!")
            if prob is not None:
                prob *= cnt / len(shoe)
            idx = next(i for i, c in enumerate(shoe) if c.rank == card.rank)
            shoe.pop(idx)
        return prob

    # ------------------------------------------------------------------
    # Card / hand helpers
    # ------------------------------------------------------------------

    def total(self, cards: list[Card]) -> int:
        t = aces = 0
        for c in cards:
            if c.rank == 1: t += 11; aces += 1
            else: t += c.rank
        while t > 21 and aces > 0: t -= 10; aces -= 1
        return t

    def is_soft(self, cards: list[Card]) -> bool:
        t = aces = 0
        for c in cards:
            if c.rank == 1: t += 11; aces += 1
            else: t += c.rank
        while t > 21 and aces > 0: t -= 10; aces -= 1
        return aces > 0

    def can_double(self, cards: list[Card]) -> bool:
        return len(cards) == 2

    def is_blackjack(self, cards: list[Card], exclude_cards: Optional[list[Card]]) -> bool:
        return len(cards) == 2 and self.total(cards) == 21 and exclude_cards is None

    def hands_equal(self, a: list[Card], b: list[Card]) -> bool:
        if len(a) != len(b): return False
        return sorted(c.rank for c in a) == sorted(c.rank for c in b)

    def get_hand_index(self, hand: list[Card], data: list) -> int:
        hand_sorted = sorted(hand, key=lambda c: c.rank)
        for idx, entry in enumerate(data):
            if self.hands_equal(hand_sorted, entry[0]):
                return idx
        return -1

    def get_data(self, cards: list[Card], up_card: int, data: Any) -> Any:
        ds = self.get_data_set(data["probs"])
        soft = self.is_soft(cards)
        key = "soft" if soft else "hard"
        idx = self.get_hand_index(cards, ds[key][up_card - 1])
        if idx == -1:
            raise ValueError("No hand in data")
        return ds[key][up_card - 1][idx][2]

    def normalize(self, arr: list[float]) -> list[float]:
        t = sum(arr)
        if t == 0: return arr
        return [x / t for x in arr]

    # ------------------------------------------------------------------
    # Dealer cache
    # ------------------------------------------------------------------

    def _get_dealer_outcomes_cached(self, up_card: int, shoe: ShoeCount) -> list[float]:
        """Dealer outcome distribution, cached by (upcard, shoe_counts)."""
        key = (up_card,) + shoe.cache_key()
        cached = self._dealer_cache.get(key)
        if cached is not None:
            return cached
        probs: list[float] = []
        self._dealer_recurse((up_card,), shoe, 1.0, probs)
        result = self._aggregate_dealer_probs(probs)
        self._dealer_cache[key] = result
        return result

    # ------------------------------------------------------------------
    # Dealer simulation
    # ------------------------------------------------------------------

    def run_dealer_sim(self, normalize: bool = False) -> list:
        results = []
        for up_card in range(1, 11):
            shoe = ShoeCount(self.dealer_settings.decks)
            p_up = shoe.prob(up_card)
            shoe.remove(up_card)
            probs: list[float] = []
            self._dealer_recurse((up_card,), shoe, p_up, probs)
            counts = self._aggregate_dealer_probs(probs, normalize_flag=normalize)
            results.append(counts)
        return results

    def run_dealer_sim_given_cards(
        self,
        cards: list[Card],
        dealer_upcard: int,
        exclude_cards: Optional[list[Card]] = None,
        split: bool = False,
    ) -> list[float]:
        shoe = ShoeCount(self.dealer_settings.decks)
        is_bj = (
            self.total(cards) == 21
            and len(cards) == 2
            and exclude_cards is None
            and not split
        )
        if exclude_cards:
            for c in exclude_cards: shoe.remove(c.rank)
        for c in cards: shoe.remove(c.rank)
        shoe.remove(dealer_upcard)

        if is_bj:
            probs: list[float] = []
            self._dealer_recurse((dealer_upcard,), shoe, 1.0, probs, True)
            return self._aggregate_dealer_probs(probs)

        return self._get_dealer_outcomes_cached(dealer_upcard, shoe)

    def _dealer_recurse(
        self,
        hand: tuple,
        shoe: ShoeCount,
        prob: float,
        results: list,
        player_bj: bool = False,
    ) -> None:
        if player_bj and len(hand) >= 2:
            results.append((hand, prob)); return

        t = _total_ranks(hand)
        soft17 = (t == 17 and _is_soft_ranks(hand))

        if t > 17 or (t == 17 and (not soft17 or self.dealer_settings.S17)):
            results.append((hand, prob)); return

        for r in range(1, 11):
            cnt = shoe.count(r)
            if cnt == 0: continue
            p = cnt / shoe.total
            shoe.remove(r)
            self._dealer_recurse(hand + (r,), shoe, prob * p, results, player_bj)
            shoe.restore(r)

    def _aggregate_dealer_probs(self, results: list, normalize_flag: bool = False) -> list[float]:
        counts = [0.0] * 7
        for hand, prob in results:
            t = _total_ranks(hand)
            if 17 <= t <= 20: counts[t - 16] += prob
            elif t == 21: counts[6 if len(hand) == 2 else 5] += prob
            else: counts[0] += prob
        if not self.dealer_settings.ENHC: counts[6] = 0.0
        if normalize_flag: return self.normalize(counts)
        return counts

    # ------------------------------------------------------------------
    # Stand — uses dealer cache directly when shoe is already built
    # ------------------------------------------------------------------

    def calc_stand(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
        split: bool = False,
    ) -> dict:
        card_total = self.total(cards)
        if card_total > 21:
            return {"winProb": 0.0, "tieProb": 0.0, "loseProb": 1.0, "DBJ": 0.0}

        dealer_probs = self.run_dealer_sim_given_cards(cards, up_card, exclude_cards, split)
        dbj = dealer_probs[6] if self.dealer_settings.ENHC else 0.0

        if self.is_blackjack(cards, exclude_cards):
            win_prob = 1.0 - dbj
            tot = win_prob + dbj
            if tot: win_prob /= tot; dbj /= tot
            return {"winProb": win_prob, "tieProb": 0.0, "loseProb": 0.0, "DBJ": dbj}

        win_prob = tie_prob = lose_prob = 0.0
        outcome = 0
        win_prob += dealer_probs[outcome]; outcome += 1
        while card_total > outcome + 16 and outcome < 6:
            win_prob += dealer_probs[outcome]; outcome += 1
        if card_total == outcome + 16 and outcome < 6:
            tie_prob = dealer_probs[outcome]; outcome += 1
        while card_total < outcome + 16 and outcome < 6:
            lose_prob += dealer_probs[outcome]; outcome += 1

        tot = win_prob + tie_prob + lose_prob + dbj
        if tot: win_prob /= tot; tie_prob /= tot; lose_prob /= tot; dbj /= tot
        return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

    def _stand_from_shoe(
        self,
        hand_ranks: tuple,
        up_card: int,
        shoe: ShoeCount,
    ) -> tuple:
        """
        Fast stand result (win, tie, lose, dbj) using the pre-built shoe and
        dealer cache. No Card objects, no shoe reconstruction.
        """
        card_total = _total_ranks(hand_ranks)
        if card_total > 21:
            return (0.0, 0.0, 1.0, 0.0)

        dealer_probs = self._get_dealer_outcomes_cached(up_card, shoe)
        dbj = dealer_probs[6] if self.dealer_settings.ENHC else 0.0

        win = tie = lose = 0.0
        outcome = 0
        win += dealer_probs[outcome]; outcome += 1
        while card_total > outcome + 16 and outcome < 6:
            win += dealer_probs[outcome]; outcome += 1
        if card_total == outcome + 16 and outcome < 6:
            tie = dealer_probs[outcome]; outcome += 1
        while card_total < outcome + 16 and outcome < 6:
            lose += dealer_probs[outcome]; outcome += 1

        tot = win + tie + lose + dbj
        if tot: win /= tot; tie /= tot; lose /= tot; dbj /= tot
        return (win, tie, lose, dbj)

    def calc_stand_ev(
        self,
        hand: list[Card],
        stand: dict,
        exclude_cards: Optional[list[Card]] = None,
        split: bool = False,
    ) -> float:
        if self.is_blackjack(hand, exclude_cards) and not split:
            return (1.0 - stand["DBJ"]) * self.dealer_settings.BJPay
        return stand["winProb"] - stand["loseProb"] - stand["DBJ"]

    def calc_stand_variance(
        self,
        hand: list[Card],
        stand: dict,
        exclude_cards: Optional[list[Card]] = None,
    ) -> float:
        if self.is_blackjack(hand, exclude_cards):
            return self.dealer_settings.BJPay ** 2 * stand["DBJ"] * (1.0 - stand["DBJ"])
        return 1.0 - stand["tieProb"] - self.calc_stand_ev(hand, stand, exclude_cards) ** 2

    def get_stand_probs(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Hit — fast path threads the shoe through, uses dealer cache
    # ------------------------------------------------------------------

    def _get_next_card_probs_fast(self, shoe: ShoeCount, up_card: int) -> list[float]:
        probs = []
        ENHC = self.dealer_settings.ENHC
        T = shoe.total
        if up_card == 10 and not ENHC:
            ace_cnt = shoe.count(1)
            for r in range(1, 11):
                cnt = shoe.count(r)
                if r == 1:
                    probs.append(ace_cnt / (T - 1) if T > 1 else 0.0)
                else:
                    non_ace = T - ace_cnt
                    probs.append(
                        cnt * (1.0 - (1.0 / non_ace if non_ace else 0.0)) / (T - 1)
                        if T > 1 else 0.0
                    )
        elif up_card == 1 and not ENHC:
            ten_cnt = shoe.count(10)
            for r in range(1, 11):
                cnt = shoe.count(r)
                if r == 10:
                    probs.append(ten_cnt / (T - 1) if T > 1 else 0.0)
                else:
                    non_ten = T - ten_cnt
                    probs.append(
                        cnt * (1.0 - (1.0 / non_ten if non_ten else 0.0)) / (T - 1)
                        if T > 1 else 0.0
                    )
        else:
            for r in range(1, 11):
                probs.append(shoe.count(r) / T if T else 0.0)
        return probs

    def get_next_card_prob(self, shoe: list[Card], up_card: int) -> list[float]:
        sc = ShoeCount(0)
        sc.counts = [0] * 11
        sc.total = len(shoe)
        for c in shoe: sc.counts[c.rank] += 1
        return self._get_next_card_probs_fast(sc, up_card)

    def calc_hit(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        if self.total(cards) > 21:
            return {"winProb": 0.0, "tieProb": 0.0, "loseProb": 1.0, "DBJ": 0.0}

        shoe = ShoeCount(self.dealer_settings.decks)
        if exclude_cards:
            for c in exclude_cards: shoe.remove(c.rank)
        for c in cards: shoe.remove(c.rank)
        shoe.remove(up_card)

        return self._hit_from_shoe(tuple(c.rank for c in cards), up_card, shoe)

    def _hit_from_shoe(
        self,
        hand_ranks: tuple,
        up_card: int,
        shoe: ShoeCount,
    ) -> dict:
        """Hit EV using pre-built shoe and dealer cache throughout."""
        win = tie = lose = dbj = 0.0
        next_probs = self._get_next_card_probs_fast(shoe, up_card)

        for r in range(1, 11):
            if shoe.count(r) == 0: continue
            p = next_probs[r - 1]
            if p == 0.0: continue

            new_hand = hand_ranks + (r,)
            t = _total_ranks(new_hand)

            if t > 21:
                lose += p
                continue

            shoe.remove(r)

            st = self._stand_from_shoe(new_hand, up_card, shoe)
            st_ev = st[0] - st[2] - st[3]

            ht = self._hit_from_shoe(new_hand, up_card, shoe)
            ht_ev = ht["winProb"] - ht["loseProb"] - ht["DBJ"]

            shoe.restore(r)

            if st_ev >= ht_ev:
                win += st[0] * p; tie += st[1] * p
                lose += st[2] * p; dbj += st[3] * p
            else:
                win += ht["winProb"] * p; tie += ht["tieProb"] * p
                lose += ht["loseProb"] * p; dbj += ht["DBJ"] * p

        tot = win + tie + lose + dbj
        if tot: win /= tot; tie /= tot; lose /= tot; dbj /= tot
        return {"winProb": win, "tieProb": tie, "loseProb": lose, "DBJ": dbj}

    def calc_hit_ev(self, hit: dict) -> float:
        return hit["winProb"] - hit["loseProb"] - hit["DBJ"]

    def calc_hit_variance(self, hit: dict) -> float:
        return 1.0 - hit["tieProb"] - self.calc_hit_ev(hit) ** 2

    # ------------------------------------------------------------------
    # Double — threads shoe through, uses dealer cache
    # ------------------------------------------------------------------

    def calc_double(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        shoe = ShoeCount(self.dealer_settings.decks)
        if exclude_cards:
            for c in exclude_cards: shoe.remove(c.rank)
        for c in cards: shoe.remove(c.rank)
        shoe.remove(up_card)

        return self._double_from_shoe(tuple(c.rank for c in cards), up_card, shoe)

    def _double_from_shoe(
        self,
        hand_ranks: tuple,
        up_card: int,
        shoe: ShoeCount,
    ) -> dict:
        """Double EV using pre-built shoe and dealer cache."""
        next_probs = self._get_next_card_probs_fast(shoe, up_card)
        win = tie = lose = dbj = 0.0

        for r in range(1, 11):
            if shoe.count(r) == 0: continue
            p = next_probs[r - 1]
            if p == 0.0: continue
            new_hand = hand_ranks + (r,)
            if _total_ranks(new_hand) > 21:
                lose += p; continue
            shoe.remove(r)
            st = self._stand_from_shoe(new_hand, up_card, shoe)
            shoe.restore(r)
            win += st[0] * p; tie += st[1] * p
            lose += st[2] * p; dbj += st[3] * p

        tot = win + tie + lose + dbj
        if tot: win /= tot; tie /= tot; lose /= tot; dbj /= tot
        return {"winProb": win, "tieProb": tie, "loseProb": lose, "DBJ": dbj}

    def calc_double_ev(self, double: dict) -> float:
        return 2.0 * (double["winProb"] - double["loseProb"] - double["DBJ"])

    def calc_double_variance(self, double: dict) -> float:
        return 4.0 * (1.0 - double["tieProb"]) - self.calc_double_ev(double) ** 2

    # ------------------------------------------------------------------
    # Split — single shoe threaded through all sub-calculations
    # ------------------------------------------------------------------

    def calc_split(
        self,
        cards: list[Card],
        up_card: int,
        remove_pair_card: bool = False,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        empty = {"winProb": 0.0, "tieProb": 0.0, "loseProb": 0.0, "DBJ": 0.0}
        hand_probs = {"noDouble": dict(empty), "double": dict(empty)}

        if len(cards) != 2 or cards[0].rank != cards[1].rank:
            return hand_probs

        # Fresh dealer cache for this split calculation
        self._dealer_cache = {}

        # Build shoe once: remove both pair cards + upcard + any excludes
        shoe = ShoeCount(self.dealer_settings.decks)
        if exclude_cards:
            for c in exclude_cards: shoe.remove(c.rank)
        for c in cards: shoe.remove(c.rank)
        shoe.remove(up_card)

        # If remove_pair_card, remove one more copy of the pair rank
        pair_rank = cards[0].rank
        if remove_pair_card:
            shoe.remove(pair_rank)

        T = shoe.total
        next_probs = [shoe.count(r) / T if T else 0.0 for r in range(1, 11)]

        for r in range(1, 11):
            if shoe.count(r) == 0: continue
            p = next_probs[r - 1]
            if p == 0.0: continue

            # Draw one card to the split hand — remove from shoe
            shoe.remove(r)

            hand_ranks = (pair_rank, r)
            t = _total_ranks(hand_ranks)

            if pair_rank == 1 and not self.dealer_settings.drawAces:
                # Forced stand on split aces
                st = self._stand_from_shoe(hand_ranks, up_card, shoe)
                hand_probs["noDouble"]["winProb"]  += st[0] * p
                hand_probs["noDouble"]["tieProb"]  += st[1] * p
                hand_probs["noDouble"]["loseProb"] += st[2] * p
                hand_probs["noDouble"]["DBJ"]      += st[3] * p
            else:
                st  = self._stand_from_shoe(hand_ranks, up_card, shoe)
                ht  = self._hit_from_shoe(hand_ranks, up_card, shoe)
                dbl = self._double_from_shoe(hand_ranks, up_card, shoe)

                st_ev  = st[0] - st[2] - st[3]
                ht_ev  = ht["winProb"] - ht["loseProb"] - ht["DBJ"]
                dbl_ev = self.calc_double_ev(dbl)

                # DAS: 2-card split hand can always double (it's 2 cards)
                if self.dealer_settings.DAS:
                    max_ev = max(st_ev, ht_ev, dbl_ev)
                else:
                    max_ev = max(st_ev, ht_ev)

                if self.dealer_settings.DAS and max_ev == dbl_ev:
                    bucket = "double"
                    hand_probs[bucket]["winProb"]  += dbl["winProb"] * p
                    hand_probs[bucket]["tieProb"]  += dbl["tieProb"] * p
                    hand_probs[bucket]["loseProb"] += dbl["loseProb"] * p
                    hand_probs[bucket]["DBJ"]      += dbl["DBJ"] * p
                elif max_ev == ht_ev:
                    hand_probs["noDouble"]["winProb"]  += ht["winProb"] * p
                    hand_probs["noDouble"]["tieProb"]  += ht["tieProb"] * p
                    hand_probs["noDouble"]["loseProb"] += ht["loseProb"] * p
                    hand_probs["noDouble"]["DBJ"]      += ht["DBJ"] * p
                else:
                    hand_probs["noDouble"]["winProb"]  += st[0] * p
                    hand_probs["noDouble"]["tieProb"]  += st[1] * p
                    hand_probs["noDouble"]["loseProb"] += st[2] * p
                    hand_probs["noDouble"]["DBJ"]      += st[3] * p

            shoe.restore(r)

        tot = sum(
            hand_probs[b][k]
            for b in ("double", "noDouble")
            for k in ("winProb", "tieProb", "loseProb", "DBJ")
        )
        if tot:
            for b in ("double", "noDouble"):
                for k in ("winProb", "tieProb", "loseProb", "DBJ"):
                    hand_probs[b][k] /= tot

        return hand_probs

    def calc_split_ev(self, split: dict) -> float:
        w2=split["double"]["winProb"]; t2=split["double"]["tieProb"]
        l2=split["double"]["loseProb"]
        w=split["noDouble"]["winProb"]; t=split["noDouble"]["tieProb"]
        l=split["noDouble"]["loseProb"]; d=split["noDouble"]["DBJ"]
        if self.dealer_settings.DAS:
            win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2
            win1=2*w2*l+2*w*(t+t2)
            lose1=2*l2*w+2*l*(t+t2); lose2=2*l2*(t+t2)+l**2
            lose3=2*l2*l; lose4=l2**2
            return 4*win4+3*win3+2*win2+win1-d-lose1-2*lose2-3*lose3-4*lose4
        win2=w**2; win1=2*w*t; lose1=2*l*t; lose2=l**2
        return 2*win2+win1-d-lose1-2*lose2

    def calc_split_variance(self, split: dict) -> float:
        w2=split["double"]["winProb"]; t2=split["double"]["tieProb"]
        l2=split["double"]["loseProb"]
        w=split["noDouble"]["winProb"]; t=split["noDouble"]["tieProb"]
        l=split["noDouble"]["loseProb"]
        ev=self.calc_split_ev(split)
        if self.dealer_settings.DAS:
            win4=w2**2; win3=2*w2*w; win2=2*w2*(t+t2)+w**2
            tie=2*w2*l2+2*w*l+(t+t2)**2
            lose2=2*l2*(t+t2)+l**2; lose3=2*l2*l; lose4=l2**2
            return 1+15*(win4+lose4)+8*(win3+lose3)+3*(win2+lose2)-tie-ev**2
        win2=w**2; tie=2*w*l+t**2; lose2=l**2
        return 1+3*(win2+lose2)-tie-ev**2

    # ------------------------------------------------------------------
    # get_split_probs / get_cumulative_probs
    # ------------------------------------------------------------------

    def get_split_probs(self) -> list:
        splits = []
        das_key = "DAS" if self.dealer_settings.DAS else "nDAS"
        data_set = self.get_data_set(self.split_data["probs"])[das_key]
        for up_card in range(1, 11):
            upcard_results = []
            for pair_val in range(1, 11):
                ev = -99.0
                hand_index = self.get_hand_index(
                    [Card(rank=pair_val), Card(rank=pair_val)],
                    data_set[up_card - 1],
                )
                if hand_index != -1:
                    ev = self.calc_split_ev(data_set[up_card - 1][hand_index][1])
                upcard_results.append(ev)
            splits.append(upcard_results)
        return splits

    def get_cumulative_probs(self, decision: str) -> dict:
        data = {"stand": self.stand_data, "hit": self.hit_data,
                "double": self.double_data}.get(decision)
        hard = []
        for up_card in range(1, 11):
            upcard_results = []
            for total_target in range(4, 22):
                candidate_hands = self.run_hand_sim(total_target, up_card, False)["allHands"]
                evs, probs = [], []
                for hand in candidate_hands:
                    if decision == "double" and len(hand["hand"]) > 2: continue
                    if self.total(hand["hand"]) == total_target:
                        ev_data = self.get_data(hand["hand"], up_card, data)
                        evs.append(self._calc_ev(decision, hand["hand"], ev_data))
                        probs.append(hand["totalProb"])
                probs = self.normalize(probs)
                upcard_results.append(sum(evs[i]*probs[i] for i in range(len(evs))))
            hard.append(upcard_results)

        soft = []
        for up_card in range(1, 11):
            upcard_results = []
            for total_target in range(12, 22):
                candidate_hands = self.run_hand_sim(total_target, up_card, True)["allHands"]
                evs, probs = [], []
                for hand in candidate_hands:
                    if decision == "double" and len(hand["hand"]) > 2: continue
                    if self.total(hand["hand"]) == total_target:
                        ev_data = self.get_data(hand["hand"], up_card, data)
                        evs.append(self._calc_ev(decision, hand["hand"], ev_data))
                        probs.append(hand["totalProb"])
                probs = self.normalize(probs)
                upcard_results.append(sum(evs[i]*probs[i] for i in range(len(evs))))
            soft.append(upcard_results)
        return {"hard": hard, "soft": soft}

    def _calc_ev(self, decision: str, hand, ev_data) -> float:
        if decision == "stand":   return self.calc_stand_ev(hand, ev_data)
        if decision == "hit":     return self.calc_hit_ev(ev_data)
        if decision == "double":  return self.calc_double_ev(ev_data)
        return self.calc_split_ev(ev_data)

    # ------------------------------------------------------------------
    # run_hand_sim
    # ------------------------------------------------------------------

    def run_hand_sim(self, total_target: int, up_card: int, soft_hands: bool) -> dict:
        all_hands: list[dict] = []
        next_card_probs = [0.0] * 10
        seen_combos: set[str] = set()
        base_shoe = ShoeCount(self.dealer_settings.decks)

        for player_rank in range(1, 11):
            player_cnt = base_shoe.count(player_rank)
            if player_cnt == 0: continue
            prob_player = player_cnt / base_shoe.total

            shoe_after_player = base_shoe.copy()
            shoe_after_player.remove(player_rank)

            up_cnt = shoe_after_player.count(up_card)
            if up_cnt == 0: continue
            prob_up = up_cnt / shoe_after_player.total
            shoe_after_player.remove(up_card)

            def recurse(hand: tuple, shoe: ShoeCount, prob: float, min_rank: int) -> None:
                t = _total_ranks(hand)
                is_soft = _is_soft_ranks(hand)
                if not soft_hands and is_soft and total_target > 11:
                    t -= 10
                if t > total_target: return
                if t == total_target and len(hand) > 1:
                    if (soft_hands and is_soft) or (not soft_hands):
                        key = ",".join(str(r) for r in sorted(hand))
                        if key not in seen_combos:
                            seen_combos.add(key)
                            cards = [Card(rank=r) for r in hand]
                            all_hands.append({"hand": cards, "totalProb": prob})
                            T = shoe.total
                            for nr in range(1, 11):
                                if shoe.count(nr) == 0: continue
                                next_card_probs[nr - 1] += (shoe.count(nr) / T) * prob
                    return
                T = shoe.total
                for r in range(min_rank, 11):
                    if shoe.count(r) == 0: continue
                    p = shoe.count(r) / T
                    shoe.remove(r)
                    recurse(hand + (r,), shoe, prob * p, r)
                    shoe.restore(r)

            recurse((player_rank,), shoe_after_player, prob_player * prob_up, 1)

        total = sum(next_card_probs)
        if total > 0:
            next_card_probs = [p / total for p in next_card_probs]
        return {"allHands": all_hands, "nextCardProbs": next_card_probs}

    # ------------------------------------------------------------------
    # Legacy API kept for compatibility
    # ------------------------------------------------------------------

    def dealer_outcome_generator(
        self, dealer_hand, outcomes, hand_probs, probabilities, shoe, player_bj
    ) -> None:
        if player_bj and len(dealer_hand) >= 2:
            outcomes.append(dealer_hand); probabilities.append(hand_probs); return
        t = self.total(dealer_hand)
        soft17 = (t == 17 and self.is_soft(dealer_hand))
        if t > 17 or (t == 17 and (not soft17 or self.dealer_settings.S17)):
            outcomes.append(dealer_hand); probabilities.append(hand_probs); return
        for i in range(1, 11):
            card_index = next((idx for idx, c in enumerate(shoe) if c.rank == i), -1)
            if card_index == -1: continue
            cnt = sum(1 for c in shoe if c.rank == i)
            p = cnt / len(shoe)
            new_shoe = shoe[:card_index] + shoe[card_index + 1:]
            self.dealer_outcome_generator(
                dealer_hand + [Card(rank=i)], outcomes,
                hand_probs + [p], probabilities, new_shoe, player_bj
            )

    def get_dealer_totals(self, outcomes):
        return [self.total(h) for h in outcomes]

    def get_total_probabilities(self, probabilities):
        total_probs = [1.0] * len(probabilities)
        for i, plist in enumerate(probabilities):
            for p in plist: total_probs[i] *= p
        return total_probs

    def get_dealer_outcome_counts(self, outcomes, probabilities, normalize=False):
        totals = self.get_dealer_totals(outcomes)
        counts = [0.0] * 7
        for i, t in enumerate(totals):
            if 17 <= t <= 20: counts[t - 16] += probabilities[i]
            elif t == 21: counts[6 if len(outcomes[i]) == 2 else 5] += probabilities[i]
            else: counts[0] += probabilities[i]
        if not self.dealer_settings.ENHC: counts[6] = 0.0
        return self.normalize(counts) if normalize else counts