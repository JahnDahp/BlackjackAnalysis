from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class DealerSettingsObject:
    decks: int = 6
    S17: bool = True          # Dealer stands on soft 17
    ENHC: bool = False        # European No Hole Card
    DAS: bool = True          # Double After Split
    drawAces: bool = False    # Can draw to split aces
    BJPay: float = 1.5        # Blackjack payout multiplier

@dataclass
class Card:
    rank: int

class Calculator:
    def __init__(self, dealer_settings: DealerSettingsObject) -> None:
        self.dealer_settings: DealerSettingsObject = dealer_settings
        self.dealer_data: Any = None
        self.stand_data: Any = None
        self.hit_data: Any = None
        self.double_data: Any = None
        self.split_data: Any = None

    @classmethod
    def create(cls, dealer_settings: DealerSettingsObject, data_dir: str) -> "Calculator":
        instance = cls(dealer_settings)

        def read(filename: str) -> Any:
            with open(os.path.join(data_dir, filename), "r", encoding="utf-8") as f:
                return json.load(f)

        instance.dealer_data = read("dealer.json")
        instance.stand_data = read("stand.json")
        instance.hit_data = read("hit.json")
        instance.double_data = read("double.json")
        instance.split_data = read("split.json")
        return instance

    def run_sims(self) -> None:
        pass

    def get_data_set(self, data: Any) -> Any:
        decks = self.dealer_settings.decks
        s17 = self.dealer_settings.S17
        enhc = self.dealer_settings.ENHC

        deck_map = {1: "oneDeck", 2: "twoDeck", 4: "fourDeck", 6: "sixDeck", 8: "eightDeck"}
        deck_key = deck_map.get(decks)

        rule_key = "S17" if s17 else "H17"
        peek_key = "enhc" if enhc else "us"

        return data[deck_key][rule_key][peek_key]

    def run_dealer_sim(self, normalize: bool = False) -> list:
        up_card_outcomes = []

        for i in range(1, 11):
            shoe = self.gen_shoe()
            card_index = next((idx for idx, c in enumerate(shoe) if c.rank == i), -1)
            if card_index == -1:
                raise ValueError(f"No {i} card found in shoe!")

            new_shoe = shoe[:card_index] + shoe[card_index + 1:]
            upcard = Card(rank=i)
            outcomes: list[list[Card]] = []
            count = sum(1 for c in shoe if c.rank == i)
            hand_probs = [count / len(shoe)]
            probabilities: list[list[float]] = []

            self.dealer_outcome_generator(
                [upcard], outcomes, hand_probs, probabilities, new_shoe, False
            )
            up_card_outcomes.append(
                self.get_dealer_outcome_counts(
                    outcomes,
                    self.get_total_probabilities(probabilities),
                    normalize,
                )
            )

        return up_card_outcomes

    def run_dealer_sim_given_cards(
        self,
        cards: list[Card],
        dealer_upcard: int,
        exclude_cards: Optional[list[Card]] = None,
        split: bool = False,
    ) -> list[float]:
        shoe = self.gen_shoe()
        is_blackjack = (
            self.total(cards) == 21
            and len(cards) == 2
            and exclude_cards is None
            and not split
        )
        prob = 1.0

        if exclude_cards:
            self.remove_cards_from_shoe(shoe, exclude_cards)
        self.remove_cards_from_shoe(shoe, cards, prob)
        self.remove_cards_from_shoe(shoe, [Card(rank=dealer_upcard)], prob)

        outcomes: list[list[Card]] = []
        probabilities: list[list[float]] = []
        self.dealer_outcome_generator(
            [Card(rank=dealer_upcard)],
            outcomes,
            [prob],
            probabilities,
            shoe,
            is_blackjack,
        )
        result = self.get_dealer_outcome_counts(
            outcomes,
            self.get_total_probabilities(probabilities),
        )
        return result

    def run_hand_sim(
        self, total_target: int, up_card: int, soft_hands: bool
    ) -> dict:
        all_hands: list[dict] = []
        base_shoe = self.gen_shoe()
        next_card_probs = [0.0] * 10
        seen_combos: set[str] = set()

        for player_rank in range(1, 11):
            player_count = sum(1 for c in base_shoe if c.rank == player_rank)
            if player_count == 0:
                continue

            shoe_after_player = list(base_shoe)
            player_index = next(i for i, c in enumerate(shoe_after_player) if c.rank == player_rank)
            player_card = shoe_after_player.pop(player_index)
            prob_player = player_count / len(base_shoe)

            up_card_count = sum(1 for c in shoe_after_player if c.rank == up_card)
            if up_card_count == 0:
                continue
            dealer_index = next(i for i, c in enumerate(shoe_after_player) if c.rank == up_card)
            shoe_after_player.pop(dealer_index)
            prob_up_card = up_card_count / (len(base_shoe) - 1)

            def recurse(
                hand: list[Card],
                shoe: list[Card],
                hand_probs: list[float],
                min_rank: int,
            ) -> None:
                nonlocal next_card_probs

                t = self.total(hand)
                is_soft = self.is_soft(hand)
                if not soft_hands and is_soft and total_target > 11:
                    t -= 10
                if t > total_target:
                    return
                if t == total_target and len(hand) > 1:
                    if (soft_hands and is_soft) or (not soft_hands):
                        total_prob = 1.0
                        for p in hand_probs:
                            total_prob *= p

                        key = ",".join(str(c.rank) for c in sorted(hand, key=lambda c: c.rank))

                        if key not in seen_combos:
                            seen_combos.add(key)
                            all_hands.append({"hand": hand, "totalProb": total_prob})

                            weight = total_prob
                            remaining_shoe = list(shoe)
                            for next_rank in range(1, 11):
                                cnt = sum(1 for c in remaining_shoe if c.rank == next_rank)
                                if cnt == 0:
                                    continue
                                p = cnt / len(remaining_shoe)
                                next_card_probs[next_rank - 1] += p * weight
                    return

                for rank in range(1, 11):
                    if rank < min_rank:
                        continue
                    cnt = sum(1 for c in shoe if c.rank == rank)
                    if cnt == 0:
                        continue

                    p = cnt / len(shoe)
                    new_shoe = list(shoe)
                    remove_index = next(i for i, c in enumerate(new_shoe) if c.rank == rank)
                    new_shoe.pop(remove_index)

                    new_card = Card(rank=rank)
                    new_current = hand + [new_card]
                    new_probs = hand_probs + [p]

                    recurse(new_current, new_shoe, new_probs, rank)

            recurse(
                [player_card],
                shoe_after_player,
                [prob_player * prob_up_card],
                1,
            )

        total = sum(next_card_probs)
        if total > 0:
            next_card_probs = [p / total for p in next_card_probs]

        return {"allHands": all_hands, "nextCardProbs": next_card_probs}

    def get_dealer_data(self) -> Any:
        return self.get_data_set(self.dealer_data["outcomes"])

    def get_cumulative_probs(self, decision: str) -> dict:
        if decision == "stand":
            data = self.stand_data
        elif decision == "hit":
            data = self.hit_data
        elif decision == "double":
            data = self.double_data
        else:
            data = None

        hard = []
        for up_card in range(1, 11):
            upcard_results = []
            for total_target in range(4, 22):
                candidate_hands = self.run_hand_sim(total_target, up_card, False)["allHands"]
                evs = []
                probs = []
                for hand in candidate_hands:
                    if decision == "double" and len(hand["hand"]) > 2:
                        continue
                    hand_total = self.total(hand["hand"])
                    if hand_total == total_target:
                        ev_data = self.get_data(hand["hand"], up_card, data)
                        if decision == "stand":
                            evs.append(self.calc_stand_ev(hand["hand"], ev_data))
                        elif decision == "hit":
                            evs.append(self.calc_hit_ev(ev_data))
                        elif decision == "double":
                            evs.append(self.calc_double_ev(ev_data))
                        else:
                            evs.append(self.calc_split_ev(ev_data))
                        probs.append(hand["totalProb"])
                probs = self.normalize(probs)
                total_ev = sum(evs[i] * probs[i] for i in range(len(evs)))
                upcard_results.append(total_ev)
            hard.append(upcard_results)

        soft = []
        for up_card in range(1, 11):
            upcard_results = []
            for total_target in range(12, 22):
                candidate_hands = self.run_hand_sim(total_target, up_card, True)["allHands"]
                evs = []
                probs = []
                for hand in candidate_hands:
                    if decision == "double" and len(hand["hand"]) > 2:
                        continue
                    hand_total = self.total(hand["hand"])
                    if hand_total == total_target:
                        ev_data = self.get_data(hand["hand"], up_card, data)
                        if decision == "stand":
                            evs.append(self.calc_stand_ev(hand["hand"], ev_data))
                        elif decision == "hit":
                            evs.append(self.calc_hit_ev(ev_data))
                        elif decision == "double":
                            evs.append(self.calc_double_ev(ev_data))
                        else:
                            evs.append(self.calc_split_ev(ev_data))
                        probs.append(hand["totalProb"])
                probs = self.normalize(probs)
                total_ev = sum(evs[i] * probs[i] for i in range(len(evs)))
                upcard_results.append(total_ev)
            soft.append(upcard_results)

        return {"hard": hard, "soft": soft}

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
                    split_result = data_set[up_card - 1][hand_index][1]
                    ev = self.calc_split_ev(split_result)
                upcard_results.append(ev)
            splits.append(upcard_results)

        return splits

    def is_blackjack(
        self, cards: list[Card], exclude_cards: Optional[list[Card]]
    ) -> bool:
        t = self.total(cards)
        return len(cards) == 2 and t == 21 and exclude_cards is None

    def calc_stand(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
        split: bool = False,
    ) -> dict:
        card_total = self.total(cards)
        win_prob = 0.0
        tie_prob = 0.0
        lose_prob = 0.0
        dbj = 0.0

        if card_total > 21:
            return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": 1.0, "DBJ": dbj}

        dealer_probs = self.run_dealer_sim_given_cards(cards, up_card, exclude_cards, split)

        dbj = dealer_probs[6] if self.dealer_settings.ENHC else 0.0

        if self.is_blackjack(cards, exclude_cards):
            win_prob = 1.0 - dbj
            return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

        outcome = 0
        win_prob += dealer_probs[outcome] if outcome < len(dealer_probs) else 0
        outcome += 1
        while card_total > outcome + 16 and outcome < 6:
            win_prob += dealer_probs[outcome] if outcome < len(dealer_probs) else 0
            outcome += 1
        if card_total == outcome + 16 and outcome < 6:
            tie_prob = dealer_probs[outcome] if outcome < len(dealer_probs) else 0
            outcome += 1
        while card_total < outcome + 16 and outcome < 6:
            lose_prob += dealer_probs[outcome] if outcome < len(dealer_probs) else 0
            outcome += 1

        total = win_prob + tie_prob + lose_prob + dbj
        if total:
            win_prob /= total
            tie_prob /= total
            lose_prob /= total
            dbj /= total

        return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

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
            return (
                self.dealer_settings.BJPay ** 2
                * stand["DBJ"]
                * (1.0 - stand["DBJ"])
            )
        return 1.0 - stand["tieProb"] - self.calc_stand_ev(hand, stand, exclude_cards) ** 2

    def get_stand_probs(self) -> None:
        pass

    def calc_hit(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        if self.total(cards) > 21:
            return {"winProb": 0.0, "tieProb": 0.0, "loseProb": 1.0, "DBJ": 0.0}

        win_prob = 0.0
        tie_prob = 0.0
        lose_prob = 0.0
        dbj = 0.0

        shoe = self.gen_shoe()
        if exclude_cards:
            self.remove_cards_from_shoe(shoe, exclude_cards)
        self.remove_cards_from_shoe(shoe, cards)
        self.remove_cards_from_shoe(shoe, [Card(rank=up_card)])

        next_card_probs = self.get_next_card_prob(shoe, up_card)

        for next_rank in range(1, 11):
            if sum(1 for c in shoe if c.rank == next_rank) == 0:
                continue
            hand = cards + [Card(rank=next_rank)]

            if self.total(hand) > 21:
                lose_prob += next_card_probs[next_rank - 1]
                continue

            if exclude_cards:
                stand = self.calc_stand(hand, up_card, exclude_cards)
            else:
                stand = self.get_data(hand, up_card, self.stand_data)

            stand_ev = self.calc_stand_ev(hand, stand, exclude_cards)
            hit = self.calc_hit(hand, up_card, exclude_cards)
            hit_ev = self.calc_hit_ev(hit)
            max_ev = max(hit_ev, stand_ev)

            if max_ev == stand_ev:
                win_prob += stand["winProb"] * next_card_probs[next_rank - 1]
                tie_prob += stand["tieProb"] * next_card_probs[next_rank - 1]
                lose_prob += stand["loseProb"] * next_card_probs[next_rank - 1]
                dbj += stand["DBJ"] * next_card_probs[next_rank - 1]
            else:
                win_prob += hit["winProb"] * next_card_probs[next_rank - 1]
                tie_prob += hit["tieProb"] * next_card_probs[next_rank - 1]
                lose_prob += hit["loseProb"] * next_card_probs[next_rank - 1]
                dbj += hit["DBJ"] * next_card_probs[next_rank - 1]

        total = win_prob + tie_prob + lose_prob + dbj
        if total:
            win_prob /= total
            tie_prob /= total
            lose_prob /= total
            dbj /= total

        return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

    def calc_hit_ev(self, hit: dict) -> float:
        return hit["winProb"] - hit["loseProb"] - hit["DBJ"]

    def calc_hit_variance(self, hit: dict) -> float:
        return 1.0 - hit["tieProb"] - self.calc_hit_ev(hit) ** 2

    def calc_double(
        self,
        cards: list[Card],
        up_card: int,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        win_prob = 0.0
        tie_prob = 0.0
        lose_prob = 0.0
        dbj = 0.0

        shoe = self.gen_shoe()
        if exclude_cards:
            self.remove_cards_from_shoe(shoe, exclude_cards)
        self.remove_cards_from_shoe(shoe, cards)
        self.remove_cards_from_shoe(shoe, [Card(rank=up_card)])

        next_card_probs = self.get_next_card_prob(shoe, up_card)

        for next_rank in range(1, 11):
            if sum(1 for c in shoe if c.rank == next_rank) == 0:
                continue
            hand = cards + [Card(rank=next_rank)]

            if self.total(hand) > 21:
                lose_prob += next_card_probs[next_rank - 1]
                continue

            stand = self.calc_stand(hand, up_card, exclude_cards)
            win_prob += stand["winProb"] * next_card_probs[next_rank - 1]
            tie_prob += stand["tieProb"] * next_card_probs[next_rank - 1]
            lose_prob += stand["loseProb"] * next_card_probs[next_rank - 1]
            dbj += stand["DBJ"] * next_card_probs[next_rank - 1]

        total = win_prob + tie_prob + lose_prob + dbj
        if total:
            win_prob /= total
            tie_prob /= total
            lose_prob /= total
            dbj /= total

        return {"winProb": win_prob, "tieProb": tie_prob, "loseProb": lose_prob, "DBJ": dbj}

    def calc_double_ev(self, double: dict) -> float:
        return 2.0 * (double["winProb"] - double["loseProb"] - double["DBJ"])

    def calc_double_variance(self, double: dict) -> float:
        return 4.0 * (1.0 - double["tieProb"]) - self.calc_double_ev(double) ** 2

    def calc_split(
        self,
        cards: list[Card],
        up_card: int,
        remove_pair_card: bool = False,
        exclude_cards: Optional[list[Card]] = None,
    ) -> dict:
        empty = {"winProb": 0.0, "tieProb": 0.0, "loseProb": 0.0, "DBJ": 0.0}
        hand_probs = {
            "noDouble": dict(empty),
            "double": dict(empty),
        }

        if len(cards) != 2:
            return hand_probs
        if cards[0].rank != cards[1].rank:
            return hand_probs

        shoe = self.gen_shoe()
        all_exclude = list(cards) + (list(exclude_cards) if exclude_cards else [])
        self.remove_cards_from_shoe(shoe, all_exclude)
        self.remove_cards_from_shoe(shoe, [Card(rank=up_card)])

        next_card_probs = []
        for rank in range(1, 11):
            cnt = sum(1 for c in shoe if c.rank == rank)
            next_card_probs.append(cnt / len(shoe))

        for next_rank in range(1, 11):
            if next_card_probs[next_rank - 1] == 0.0:
                continue
            hand = [cards[0], Card(rank=next_rank)]

            # Build the exclude list for sub-calculations
            sub_exclude: list[Card] = []
            if exclude_cards:
                sub_exclude.extend(exclude_cards)
            if remove_pair_card:
                sub_exclude.append(cards[0])
            sub_exclude_arg = sub_exclude if sub_exclude else None

            stand = self.calc_stand(hand, up_card, sub_exclude_arg)

            if cards[0].rank == 1 and not self.dealer_settings.drawAces:
                # Forced stand after one card on split aces
                hand_probs["noDouble"]["winProb"] += stand["winProb"] * next_card_probs[next_rank - 1]
                hand_probs["noDouble"]["tieProb"] += stand["tieProb"] * next_card_probs[next_rank - 1]
                hand_probs["noDouble"]["loseProb"] += stand["loseProb"] * next_card_probs[next_rank - 1]
                hand_probs["noDouble"]["DBJ"] += stand["DBJ"] * next_card_probs[next_rank - 1]
            else:
                hit = self.calc_hit(hand, up_card, sub_exclude_arg)
                double = self.calc_double(hand, up_card, sub_exclude_arg)

                hit_ev = self.calc_hit_ev(hit)
                double_ev = self.calc_double_ev(double)
                stand_ev = self.calc_stand_ev(hand, stand, sub_exclude_arg)

                if self.can_double(hand) and self.dealer_settings.DAS:
                    max_ev = max(stand_ev, hit_ev, double_ev)
                else:
                    max_ev = max(stand_ev, hit_ev)

                if max_ev == stand_ev:
                    hand_probs["noDouble"]["winProb"] += stand["winProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["tieProb"] += stand["tieProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["loseProb"] += stand["loseProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["DBJ"] += stand["DBJ"] * next_card_probs[next_rank - 1]
                elif max_ev == hit_ev:
                    hand_probs["noDouble"]["winProb"] += hit["winProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["tieProb"] += hit["tieProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["loseProb"] += hit["loseProb"] * next_card_probs[next_rank - 1]
                    hand_probs["noDouble"]["DBJ"] += hit["DBJ"] * next_card_probs[next_rank - 1]
                elif max_ev == double_ev:
                    hand_probs["double"]["winProb"] += double["winProb"] * next_card_probs[next_rank - 1]
                    hand_probs["double"]["tieProb"] += double["tieProb"] * next_card_probs[next_rank - 1]
                    hand_probs["double"]["loseProb"] += double["loseProb"] * next_card_probs[next_rank - 1]
                    hand_probs["double"]["DBJ"] += double["DBJ"] * next_card_probs[next_rank - 1]

        total = (
            hand_probs["double"]["winProb"]
            + hand_probs["double"]["tieProb"]
            + hand_probs["double"]["loseProb"]
            + hand_probs["double"]["DBJ"]
            + hand_probs["noDouble"]["winProb"]
            + hand_probs["noDouble"]["tieProb"]
            + hand_probs["noDouble"]["loseProb"]
            + hand_probs["noDouble"]["DBJ"]
        )

        if total:
            for key in ("double", "noDouble"):
                hand_probs[key]["winProb"] /= total
                hand_probs[key]["tieProb"] /= total
                hand_probs[key]["loseProb"] /= total
                hand_probs[key]["DBJ"] /= total

        return {"noDouble": hand_probs["noDouble"], "double": hand_probs["double"]}

    def calc_split_ev(self, split: dict) -> float:
        w2 = split["double"]["winProb"]
        t2 = split["double"]["tieProb"]
        l2 = split["double"]["loseProb"]
        w = split["noDouble"]["winProb"]
        t = split["noDouble"]["tieProb"]
        l = split["noDouble"]["loseProb"]
        d = split["noDouble"]["DBJ"]

        if self.dealer_settings.DAS:
            win4 = w2 ** 2
            win3 = 2 * w2 * w
            win2 = 2 * w2 * (t + t2) + w ** 2
            win1 = 2 * w2 * l + 2 * w * (t + t2)
            lose1 = 2 * l2 * w + 2 * l * (t + t2)
            lose2 = 2 * l2 * (t + t2) + l ** 2
            lose3 = 2 * l2 * l
            lose4 = l2 ** 2
            return (
                4 * win4
                + 3 * win3
                + 2 * win2
                + win1
                - d
                - lose1
                - 2 * lose2
                - 3 * lose3
                - 4 * lose4
            )

        win2 = w ** 2
        win1 = 2 * w * t
        lose1 = 2 * l * t
        lose2 = l ** 2
        return 2 * win2 + win1 - d - lose1 - 2 * lose2

    def calc_split_variance(self, split: dict) -> float:
        w2 = split["double"]["winProb"]
        t2 = split["double"]["tieProb"]
        l2 = split["double"]["loseProb"]
        w = split["noDouble"]["winProb"]
        t = split["noDouble"]["tieProb"]
        l = split["noDouble"]["loseProb"]
        ev = self.calc_split_ev(split)

        if self.dealer_settings.DAS:
            win4 = w2 ** 2
            win3 = 2 * w2 * w
            win2 = 2 * w2 * (t + t2) + w ** 2
            tie = 2 * w2 * l2 + 2 * w * l + (t + t2) ** 2
            lose2 = 2 * l2 * (t + t2) + l ** 2
            lose3 = 2 * l2 * l
            lose4 = l2 ** 2
            return (
                1
                + 15 * (win4 + lose4)
                + 8 * (win3 + lose3)
                + 3 * (win2 + lose2)
                - tie
                - ev ** 2
            )

        win2 = w ** 2
        tie = 2 * w * l + t ** 2
        lose2 = l ** 2
        return 1 + 3 * (win2 + lose2) - tie - ev ** 2

    def get_next_card_prob(self, shoe: list[Card], up_card: int) -> list[float]:
        next_card_probs = []

        for next_rank in range(1, 11):
            if (up_card != 10 and up_card != 1) or self.dealer_settings.ENHC:
                cnt = sum(1 for c in shoe if c.rank == next_rank)
                next_card_probs.append(cnt / len(shoe))
            elif up_card == 10:
                cnt = sum(1 for c in shoe if c.rank == next_rank)
                ace_count = sum(1 for c in shoe if c.rank == 1)
                cards_remaining = len(shoe)
                if next_rank == 1:
                    next_card_probs.append(ace_count / (cards_remaining - 1))
                else:
                    next_card_probs.append(
                        (cnt * (1.0 - 1.0 / (cards_remaining - ace_count)))
                        / (cards_remaining - 1)
                    )
            elif up_card == 1:
                cnt = sum(1 for c in shoe if c.rank == next_rank)
                ten_count = sum(1 for c in shoe if c.rank == 10)
                cards_remaining = len(shoe)
                if next_rank == 10:
                    next_card_probs.append(ten_count / (cards_remaining - 1))
                else:
                    next_card_probs.append(
                        (cnt * (1.0 - 1.0 / (cards_remaining - ten_count)))
                        / (cards_remaining - 1)
                    )

        return next_card_probs

    def can_double(self, cards: list[Card]) -> bool:
        return len(cards) == 2

    def gen_shoe(self) -> list[Card]:
        shoe: list[Card] = []
        for _ in range(self.dealer_settings.decks):
            for _suit in range(1, 5):
                for rank in range(1, 14):
                    card_rank = 10 if rank >= 11 else rank
                    shoe.append(Card(rank=card_rank))
        return shoe

    def remove_cards_from_shoe(
        self,
        shoe: list[Card],
        cards: list[Card],
        prob: Optional[float] = None,
    ) -> Optional[float]:
        for card in cards:
            cnt = sum(1 for c in shoe if c.rank == card.rank)
            if cnt == 0:
                raise ValueError(f"No {card.rank} card found in shoe!")
            if prob is not None:
                prob *= cnt / len(shoe)
            index = next(i for i, c in enumerate(shoe) if c.rank == card.rank)
            shoe.pop(index)
        return prob

    def is_soft(self, cards: list[Card]) -> bool:
        total = 0
        num_aces = 0

        for card in cards:
            if card.rank == 1:
                total += 11
                num_aces += 1
            else:
                total += card.rank

        while total > 21 and num_aces > 0:
            total -= 10
            num_aces -= 1

        return num_aces > 0

    def total(self, cards: list[Card]) -> int:
        t = 0
        num_aces = 0

        for card in cards:
            if card.rank == 1:
                t += 11
                num_aces += 1
            else:
                t += card.rank

        while t > 21 and num_aces > 0:
            t -= 10
            num_aces -= 1

        return t

    def dealer_outcome_generator(
        self,
        dealer_hand: list[Card],
        outcomes: list[list[Card]],
        hand_probs: list[float],
        probabilities: list[list[float]],
        shoe: list[Card],
        player_bj: bool,
    ) -> None:
        if player_bj and len(dealer_hand) >= 2:
            outcomes.append(dealer_hand)
            probabilities.append(hand_probs)
            return

        current_total = self.total(dealer_hand)
        is_soft_17 = current_total == 17 and self.is_soft(dealer_hand)

        if current_total > 17 or (
            current_total == 17 and (not is_soft_17 or self.dealer_settings.S17)
        ):
            outcomes.append(dealer_hand)
            probabilities.append(hand_probs)
            return

        for i in range(1, 11):
            card_index = next((idx for idx, c in enumerate(shoe) if c.rank == i), -1)
            if card_index == -1:
                continue
            count_in_shoe = sum(1 for c in shoe if c.rank == i)
            total_cards = len(shoe)
            new_probabilities = hand_probs + [count_in_shoe / total_cards]

            new_shoe = shoe[:card_index] + shoe[card_index + 1:]
            new_cards = dealer_hand + [Card(rank=i)]

            self.dealer_outcome_generator(
                new_cards,
                outcomes,
                new_probabilities,
                probabilities,
                new_shoe,
                player_bj,
            )

    def get_dealer_totals(self, outcomes: list[list[Card]]) -> list[int]:
        return [self.total(hand) for hand in outcomes]

    def get_total_probabilities(self, probabilities: list[list[float]]) -> list[float]:
        total_probs = [1.0] * len(probabilities)
        for hand_index, prob_list in enumerate(probabilities):
            for p in prob_list:
                total_probs[hand_index] *= p
        return total_probs

    def get_dealer_outcome_counts(
        self,
        outcomes: list[list[Card]],
        probabilities: list[float],
        normalize: bool = False,
    ) -> list[float]:
        totals = self.get_dealer_totals(outcomes)
        counts = [0.0] * 7
        for i, t in enumerate(totals):
            if 17 <= t <= 20:
                counts[t - 16] += probabilities[i]
            elif t == 21:
                if len(outcomes[i]) == 2:
                    counts[6] += probabilities[i]
                else:
                    counts[5] += probabilities[i]
            else:
                counts[0] += probabilities[i]

        if not self.dealer_settings.ENHC:
            counts[6] = 0.0

        return self.normalize(counts) if normalize else counts

    def normalize(self, arr: list[float]) -> list[float]:
        total = sum(arr)
        if total == 0:
            return arr
        for i in range(len(arr)):
            arr[i] /= total
        return arr

    def hands_equal(
        self, a: list[Card], b: list[Card]
    ) -> bool:
        if len(a) != len(b):
            return False
        ranks_a = sorted(c.rank for c in a)
        ranks_b = sorted(c.rank for c in b)
        return ranks_a == ranks_b

    def get_hand_index(self, hand: list[Card], data: list) -> int:
        hand_sorted = sorted(hand, key=lambda c: c.rank)
        for idx, entry in enumerate(data):
            if self.hands_equal(hand_sorted, entry[0]):
                return idx
        return -1

    def get_data(self, cards: list[Card], up_card: int, data: Any) -> Any:
        data_set = self.get_data_set(data["probs"])
        soft_hand = self.is_soft(cards)

        if soft_hand:
            hand_index = self.get_hand_index(cards, data_set["soft"][up_card - 1])
            if hand_index == -1:
                raise ValueError("No hand in data")
            return data_set["soft"][up_card - 1][hand_index][2]
        else:
            hand_index = self.get_hand_index(cards, data_set["hard"][up_card - 1])
            if hand_index == -1:
                raise ValueError("No hand in data")
            return data_set["hard"][up_card - 1][hand_index][2]