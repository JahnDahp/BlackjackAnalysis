import { DealerSettingsObject } from "../SettingsObjects.js";
import * as fs from "fs";
import * as path from "path";

async function loadData() {
  const dealerData = await fetch("../data/dealer.json").then((res) =>
    res.json(),
  );
  const standData = await fetch("../data/stand.json").then((res) => res.json());
  const hitData = await fetch("../data/hit.json").then((res) => res.json());
  const doubleData = await fetch("../data/double.json").then((res) =>
    res.json(),
  );
  const splitData = await fetch("../data/split.json").then((res) => res.json());

  return { dealerData, standData, hitData, doubleData, splitData };
}

interface Card {
  rank: number;
}

export class Calculator {
  dealerSettings: DealerSettingsObject;
  dealerData: any = null;
  standData: any = null;
  hitData: any = null;
  doubleData: any = null;
  splitData: any = null;

  protected constructor(dealerSettings: DealerSettingsObject) {
    this.dealerSettings = dealerSettings;
  }

  static create(dealerSettings: any, dataDir: string): Calculator {
    const instance = new Calculator(dealerSettings);
    const read = (file: string) =>
      JSON.parse(fs.readFileSync(path.join(dataDir, file), "utf-8"));
    instance.dealerData = read("dealer.json");
    instance.standData = read("stand.json");
    instance.hitData = read("hit.json");
    instance.doubleData = read("double.json");
    instance.splitData = read("split.json");
    return instance;
  }

  runSims() {}

  getDataSet(data: any) {
    let returnData: any;
    switch (this.dealerSettings.decks) {
      case 1:
        this.dealerSettings.S17
          ? this.dealerSettings.ENHC
            ? (returnData = data.oneDeck.S17.enhc)
            : (returnData = data.oneDeck.S17.us)
          : this.dealerSettings.ENHC
            ? (returnData = data.oneDeck.H17.enhc)
            : (returnData = data.oneDeck.H17.us);
      case 2:
        this.dealerSettings.S17
          ? this.dealerSettings.ENHC
            ? (returnData = data.twoDeck.S17.enhc)
            : (returnData = data.twoDeck.S17.us)
          : this.dealerSettings.ENHC
            ? (returnData = data.twoDeck.H17.enhc)
            : (returnData = data.twoDeck.H17.us);
      case 4:
        this.dealerSettings.S17
          ? this.dealerSettings.ENHC
            ? (returnData = data.fourDeck.S17.enhc)
            : (returnData = data.fourDeck.S17.us)
          : this.dealerSettings.ENHC
            ? (returnData = data.fourDeck.H17.enhc)
            : (returnData = data.fourDeck.H17.us);
      case 6:
        this.dealerSettings.S17
          ? this.dealerSettings.ENHC
            ? (returnData = data.sixDeck.S17.enhc)
            : (returnData = data.sixDeck.S17.us)
          : this.dealerSettings.ENHC
            ? (returnData = data.sixDeck.H17.enhc)
            : (returnData = data.sixDeck.H17.us);
      case 8:
        this.dealerSettings.S17
          ? this.dealerSettings.ENHC
            ? (returnData = data.eightDeck.S17.enhc)
            : (returnData = data.eightDeck.S17.us)
          : this.dealerSettings.ENHC
            ? (returnData = data.eightDeck.H17.enhc)
            : (returnData = data.eightDeck.H17.us);
    }
    return returnData;
  }

  runDealerSim(normalize?: boolean) {
    let upCardOutcomes = [];

    for (let i = 1; i <= 10; i++) {
      let shoe = this.genShoe();
      const cardIndex = shoe.findIndex((card) => card.rank === i);
      if (cardIndex === -1) {
        throw new Error(`No ${i} card found in shoe!`);
      }

      const newShoe = [
        ...shoe.slice(0, cardIndex),
        ...shoe.slice(cardIndex + 1),
      ];

      const upcard: Card = { rank: i };
      const outcomes: Card[][] = [];
      const count = shoe.filter((card) => card.rank === i).length;
      const handProbs = [count / shoe.length];
      const probabilities: number[][] = [];

      this.dealerOutcomeGenerator(
        [upcard],
        outcomes,
        handProbs,
        probabilities,
        newShoe,
        false,
      );
      upCardOutcomes.push(
        this.getDealerOutcomeCounts(
          outcomes,
          this.getTotalProbabilities(probabilities),
          normalize,
        ),
      );
    }
    return upCardOutcomes;
  }

  /**
   * Simulates dealer outcomes given a specific set of player cards and dealer upcard.
   * Removes those exact cards from a fresh shoe, then runs the dealer outcome generator
   * on the remaining shoe. Optionally accepts additional cards to exclude (e.g. split
   * partner cards). Returns the dealer outcome probability distribution and whether
   * the player hand is a blackjack.
   */
  runDealerSimGivenCards(
    cards: Card[],
    dealerUpcard: number,
    excludeCards?: Card[],
    split?: boolean,
  ) {
    let shoe = this.genShoe();
    const isBlackjack =
      this.total(cards) === 21 && cards.length === 2 && !excludeCards && !split;
    let prob = 1;

    if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
    this.removeCardsFromShoe(shoe, cards, prob);
    this.removeCardsFromShoe(shoe, [{ rank: dealerUpcard }], prob);

    const outcomes: Card[][] = [];
    const probabilities: number[][] = [];
    this.dealerOutcomeGenerator(
      [{ rank: dealerUpcard }],
      outcomes,
      [prob],
      probabilities,
      shoe,
      isBlackjack,
    );
    const result = this.getDealerOutcomeCounts(
      outcomes,
      this.getTotalProbabilities(probabilities),
    );
    return result;
  }

  /**
   * Enumerates all unique player hand compositions that reach a given total
   * against a specific dealer upcard, for either hard or soft hands.
   * Uses recursive enumeration over a fresh shoe (with the first player card
   * and dealer upcard removed), building hands card by card in sorted order
   * to avoid duplicate compositions. Returns all unique hands with their
   * joint probabilities, plus the probability distribution of the next card
   * drawn after reaching the target total (used for hit EV calculations).
   */
  runHandSim(totalTarget: number, upCard: number, softHands: boolean) {
    const allHands: any[] = [];
    const baseShoe = this.genShoe();
    let nextCardProbs = Array(10).fill(0);
    const seenCombos = new Set<string>();

    for (let playerRank = 1; playerRank <= 10; playerRank++) {
      const playerCount = baseShoe.filter((c) => c.rank === playerRank).length;
      if (playerCount === 0) continue;

      const shoeAfterPlayer = [...baseShoe];
      const playerIndex = shoeAfterPlayer.findIndex(
        (c) => c.rank === playerRank,
      );
      const playerCard = shoeAfterPlayer.splice(playerIndex, 1)[0];
      const probPlayer = playerCount / baseShoe.length;

      const upCardCount = shoeAfterPlayer.filter(
        (c) => c.rank === upCard,
      ).length;
      if (upCardCount === 0) continue;
      const dealerIndex = shoeAfterPlayer.findIndex((c) => c.rank === upCard);
      shoeAfterPlayer.splice(dealerIndex, 1);
      const probUpCard = upCardCount / (baseShoe.length - 1);

      const recurse = (
        hand: Card[],
        shoe: Card[],
        handProbs: number[],
        minRank: number,
      ) => {
        let total = this.total(hand);
        const isSoft = this.isSoft(hand);
        if (!softHands && isSoft && totalTarget > 11) total -= 10;
        if (total > totalTarget) return;
        if (total === totalTarget && hand.length > 1) {
          if ((softHands && isSoft) || !softHands) {
            const totalProb = handProbs.reduce((a, b) => a * b, 1);

            const key = hand
              .map((c) => c.rank)
              .sort((a, b) => a - b)
              .join(",");

            if (!seenCombos.has(key)) {
              seenCombos.add(key);
              allHands.push({ hand, totalProb });

              const weight = totalProb;
              const remainingShoe = [...shoe];
              for (let nextRank = 1; nextRank <= 10; nextRank++) {
                const count = remainingShoe.filter(
                  (c) => c.rank === nextRank,
                ).length;
                if (count === 0) continue;
                const prob = count / remainingShoe.length;
                nextCardProbs[nextRank - 1] += prob * weight;
              }
            }
          }
          return;
        }

        for (let rank = 1; rank <= 10; rank++) {
          if (rank < minRank) continue;

          const count = shoe.filter((c) => c.rank === rank).length;
          if (count === 0) continue;

          const prob = count / shoe.length;
          const newShoe = [...shoe];
          const removeIndex = newShoe.findIndex((c) => c.rank === rank);
          newShoe.splice(removeIndex, 1);

          const newCard: Card = { rank: rank };
          const newCurrent = [...hand, newCard];
          const newProbs = [...handProbs, prob];

          recurse(newCurrent, newShoe, newProbs, rank);
        }
      };
      recurse([playerCard], shoeAfterPlayer, [probPlayer * probUpCard], 1);
    }

    const total = nextCardProbs.reduce((a, b) => a + b, 0);
    if (total > 0) {
      nextCardProbs = nextCardProbs.map((p) => p / total);
    }

    return { allHands, nextCardProbs };
  }

  /**
   * Returns the dealer outcome probability table for the current game configuration
   * by looking up the preloaded dealer data using getDataSet.
   */
  getDealerData() {
    return this.getDataSet((this.dealerData as any).outcomes);
  }

  /**
   * Computes probability-weighted average EVs for a given decision (stand, hit, double)
   * across all hand totals and dealer upcards, using precomputed per-hand EV data.
   * For each total/upcard combination, enumerates all hand compositions via runHandSim,
   * looks up each hand's EV from the precomputed data, and returns the weighted average.
   * Returns separate hard (4-21) and soft (12-21) EV tables.
   */
  getCumulativeProbs(decision: string) {
    let data =
      decision === "stand"
        ? this.standData
        : decision === "hit"
          ? this.hitData
          : decision === "double"
            ? this.doubleData
            : null;
    const hard = [];
    for (let upCard = 1; upCard <= 10; upCard++) {
      const upcardResults = [];
      for (let totalTarget = 4; totalTarget <= 21; totalTarget++) {
        const candidateHands = this.runHandSim(
          totalTarget,
          upCard,
          false,
        ).allHands;
        let EVs = [];
        let probs = [];
        for (let hand of candidateHands) {
          if (decision === "double" && hand.hand.length > 2) continue;
          const handTotal = this.total(hand.hand);
          if (handTotal === totalTarget) {
            if (decision === "stand") {
              EVs.push(
                this.calcStandEV(
                  hand.hand,
                  this.getData(hand.hand, upCard, data),
                ),
              );
            } else if (decision === "hit") {
              EVs.push(this.calcHitEV(this.getData(hand.hand, upCard, data)));
            } else if (decision === "double") {
              EVs.push(
                this.calcDoubleEV(this.getData(hand.hand, upCard, data)),
              );
            } else {
              EVs.push(this.calcSplitEV(this.getData(hand.hand, upCard, data)));
            }
            probs.push(hand.totalProb);
          }
        }
        probs = this.normalize(probs);
        let totalEV = 0;
        for (let i = 0; i < EVs.length; i++) {
          totalEV += EVs[i] * probs[i];
        }
        upcardResults.push(totalEV);
      }
      hard.push(upcardResults);
    }

    const soft = [];
    for (let upCard = 1; upCard <= 10; upCard++) {
      const upcardResults = [];
      for (let totalTarget = 12; totalTarget <= 21; totalTarget++) {
        const candidateHands = this.runHandSim(
          totalTarget,
          upCard,
          true,
        ).allHands;
        let EVs = [];
        let probs = [];
        for (let hand of candidateHands) {
          if (decision === "double" && hand.hand.length > 2) continue;
          const handTotal = this.total(hand.hand);
          if (handTotal === totalTarget) {
            if (decision === "stand") {
              EVs.push(
                this.calcStandEV(
                  hand.hand,
                  this.getData(hand.hand, upCard, data),
                ),
              );
            } else if (decision === "hit") {
              EVs.push(this.calcHitEV(this.getData(hand.hand, upCard, data)));
            } else if (decision === "double") {
              EVs.push(
                this.calcDoubleEV(this.getData(hand.hand, upCard, data)),
              );
            } else {
              EVs.push(this.calcSplitEV(this.getData(hand.hand, upCard, data)));
            }
            probs.push(hand.totalProb);
          }
        }
        probs = this.normalize(probs);
        let totalEV = 0;
        for (let i = 0; i < EVs.length; i++) {
          totalEV += EVs[i] * probs[i];
        }
        upcardResults.push(totalEV);
      }
      soft.push(upcardResults);
    }
    return { hard, soft };
  }

  /**
   * Returns a 10x10 table of split EVs for every pair (A-A through 10-10)
   * vs every dealer upcard (A through 10), looked up from precomputed split data.
   * Returns -99 for any combination not found in the data.
   */
  getSplitProbs() {
    const splits = [];
    const dasKey = this.dealerSettings.DAS ? "DAS" : "nDAS";
    const dataSet = this.getDataSet((this.splitData as any).probs)[dasKey];

    for (let upCard = 1; upCard <= 10; upCard++) {
      const upcardResults = [];
      for (let pairVal = 1; pairVal <= 10; pairVal++) {
        let EV = -99;
        const handIndex = this.getHandIndex(
          [{ rank: pairVal }, { rank: pairVal }],
          dataSet[upCard - 1],
        );
        if (handIndex !== -1) {
          const splitResult = dataSet[upCard - 1][handIndex][1];
          EV = this.calcSplitEV(splitResult);
        }
        upcardResults.push(EV);
      }
      splits.push(upcardResults);
    }
    return splits;
  }

  /**
   * Returns true if the given hand is a blackjack (2-card 21) and no excludeCards
   * are present. The excludeCards check handles split scenarios where a hand
   * that totals 21 in 2 cards should not be counted as a natural blackjack.
   */
  isBlackjack(cards: Card[], excludeCards: Card[] | undefined) {
    const total = this.total(cards);
    return cards.length === 2 && total === 21 && !excludeCards;
  }

  /**
   * Calculates the win, tie, and loss probabilities for standing on a given hand
   * vs a dealer upcard. Handles blackjack as a special case (only ties dealer BJ,
   * beats everything else). For non-blackjack hands, compares the player total
   * against each possible dealer outcome (bust, 17-21, BJ) to assign win/tie/loss
   * probabilities. Accepts optional excludeCards for split scenarios.
   */
  calcStand(
    cards: Card[],
    upCard: number,
    excludeCards?: Card[],
    split?: boolean,
  ): { winProb: number; tieProb: number; loseProb: number; DBJ: number } {
    const cardTotal = this.total(cards);
    let winProb = 0;
    let tieProb = 0;
    let loseProb = 0;
    let DBJ = 0;
    let outcome = 0;

    if (cardTotal > 21) {
      loseProb = 1;
      return { winProb, tieProb, loseProb, DBJ };
    }

    const dealerProbs = this.runDealerSimGivenCards(
      cards,
      upCard,
      excludeCards,
      split,
    );

    DBJ = this.dealerSettings.ENHC ? dealerProbs[6] : 0;

    if (this.isBlackjack(cards, excludeCards)) {
      winProb = 1 - DBJ;
      return { winProb, tieProb, loseProb, DBJ };
    }

    winProb += dealerProbs[outcome++] ?? 0;
    while (cardTotal > outcome + 16 && outcome < 6) {
      winProb += dealerProbs[outcome++] ?? 0;
    }
    if (cardTotal === outcome + 16 && outcome < 6) {
      tieProb = dealerProbs[outcome++] ?? 0;
    }
    while (cardTotal < outcome + 16 && outcome < 6) {
      loseProb += dealerProbs[outcome++] ?? 0;
    }

    const total = winProb + tieProb + loseProb + DBJ;
    winProb = winProb / total;
    tieProb = tieProb / total;
    loseProb = loseProb / total;
    DBJ = DBJ / total;

    return { winProb, tieProb, loseProb, DBJ };
  }

  /**
   * Converts stand win/tie/loss probabilities into an expected value (EV).
   * Under ENHC rules, the player loses their full bet to dealer blackjack,
   * so DBJ is subtracted directly. Under US rules (peek), dealer BJ ends the
   * hand immediately so remaining probabilities are renormalized to exclude it.
   * Blackjack pays at the configured BJPay rate (typically 1.5x).
   */
  calcStandEV(
    hand: Card[],
    stand: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    },
    excludeCards?: Card[],
    split?: boolean,
  ) {
    if (this.isBlackjack(hand, excludeCards) && !split) {
      return (1 - stand.DBJ) * this.dealerSettings.BJPay;
    }
    return stand.winProb - stand.loseProb - stand.DBJ;
  }

  /**
   * Computes the variance of the stand EV using win/tie/loss probabilities.
   * Variance is calculated as 1 minus the tie probability minus the squared EV,
   * adjusted for ENHC vs US peek rules. Used for risk/variance analysis.
   */
  calcStandVariance(
    hand: Card[],
    stand: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    },
    excludeCards?: Card[],
  ) {
    if (this.isBlackjack(hand, excludeCards)) {
      return this.dealerSettings.BJPay ** 2 * stand.DBJ * (1 - stand.DBJ);
    }
    return 1 - stand.tieProb - this.calcStandEV(hand, stand, excludeCards) ** 2;
  }

  getStandProbs() {}

  /**
   * Recursively calculates win/tie/loss probabilities for hitting a hand.
   * For each possible next card, computes the resulting hand and determines
   * whether the optimal continuation is to stand or hit again (by comparing
   * their EVs). Accumulates the weighted probabilities of each outcome across
   * all possible next cards. Accepts optional excludeCards for split scenarios.
   */
  calcHit(
    cards: Card[],
    upCard: number,
    excludeCards?: Card[],
  ): {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  } {
    if (this.total(cards) > 21) {
      return { winProb: 0, tieProb: 0, loseProb: 1, DBJ: 0 };
    }

    let winProb = 0;
    let tieProb = 0;
    let loseProb = 0;
    let DBJ = 0;

    let shoe = this.genShoe();
    if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
    this.removeCardsFromShoe(shoe, cards);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

    let nextCardProbs = this.getNextCardProb(shoe, upCard);
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      // console.log(JSON.stringify(cards), nextRank, "vs", upCard);
      if (shoe.filter((c) => c.rank === nextRank).length === 0) continue;
      const hand = [...cards, { rank: nextRank }];

      if (this.total(hand) > 21) {
        loseProb += nextCardProbs[nextRank - 1];
        continue;
      }

      let stand = excludeCards
        ? this.calcStand(hand, upCard, excludeCards)
        : this.getData(hand, upCard, this.standData);
      const standEV = this.calcStandEV(hand, stand, excludeCards);
      const hit = this.calcHit(hand, upCard, excludeCards);
      const hitEV = this.calcHitEV(hit);
      const maxEV = Math.max(hitEV, standEV);
      if (maxEV === standEV) {
        winProb += stand.winProb * nextCardProbs[nextRank - 1];
        tieProb += stand.tieProb * nextCardProbs[nextRank - 1];
        loseProb += stand.loseProb * nextCardProbs[nextRank - 1];
        DBJ += stand.DBJ * nextCardProbs[nextRank - 1];
      } else if (maxEV === hitEV) {
        winProb += hit.winProb * nextCardProbs[nextRank - 1];
        tieProb += hit.tieProb * nextCardProbs[nextRank - 1];
        loseProb += hit.loseProb * nextCardProbs[nextRank - 1];
        DBJ += hit.DBJ * nextCardProbs[nextRank - 1];
      }
    }

    const total = winProb + tieProb + loseProb + DBJ;
    winProb = winProb / total;
    tieProb = tieProb / total;
    loseProb = loseProb / total;
    DBJ = DBJ / total;

    return { winProb, tieProb, loseProb, DBJ };
  }

  /**
   * Converts hit win/tie/loss probabilities into an EV.
   * Under ENHC rules, subtracts DBJ directly. Under US peek rules,
   * renormalizes probabilities to exclude dealer blackjack scenarios.
   */
  calcHitEV(hit: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return hit.winProb - hit.loseProb - hit.DBJ;
  }

  /**
   * Computes the variance of the hit EV. Similar to calcStandVariance but
   * applied to hit outcome probabilities.
   */
  calcHitVariance(hit: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return 1 - hit.tieProb - this.calcHitEV(hit) ** 2;
  }

  /**
   * Calculates win/tie/loss probabilities for doubling down on a hand.
   * Similar to calcHit, but the player receives exactly one more card and
   * must stand — there is no recursive hitting. For each possible next card,
   * looks up the stand probabilities for the resulting hand and accumulates
   * them weighted by the probability of drawing that card.
   */
  calcDouble(
    cards: Card[],
    upCard: number,
    excludeCards?: Card[],
  ): {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  } {
    let winProb = 0;
    let tieProb = 0;
    let loseProb = 0;
    let DBJ = 0;

    let shoe = this.genShoe();
    if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
    this.removeCardsFromShoe(shoe, cards);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

    let nextCardProbs = this.getNextCardProb(shoe, upCard);
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if (shoe.filter((c) => c.rank === nextRank).length === 0) continue;
      const hand = [...cards, { rank: nextRank }];

      if (this.total(hand) > 21) {
        loseProb += nextCardProbs[nextRank - 1];
        continue;
      }

      let stand;
      stand = this.calcStand(hand, upCard, excludeCards);
      winProb += stand.winProb * nextCardProbs[nextRank - 1];
      tieProb += stand.tieProb * nextCardProbs[nextRank - 1];
      loseProb += stand.loseProb * nextCardProbs[nextRank - 1];
      DBJ += stand.DBJ * nextCardProbs[nextRank - 1];
    }

    const total = winProb + tieProb + loseProb + DBJ;
    winProb = winProb / total;
    tieProb = tieProb / total;
    loseProb = loseProb / total;
    DBJ = DBJ / total;

    return { winProb, tieProb, loseProb, DBJ };
  }

  /**
   * Converts double win/tie/loss probabilities into an EV.
   * The bet is doubled, so the EV is multiplied by 2 compared to a normal stand.
   * Handles ENHC vs US peek rules the same way as calcStandEV.
   */
  calcDoubleEV(double: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return 2 * (double.winProb - double.loseProb - double.DBJ);
  }

  /**
   * Computes the variance of the double EV. Since the bet is doubled,
   * variance is scaled by 4 compared to a single-bet hand.
   */
  calcDoubleVariance(double: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return 4 * (1 - double.tieProb) - this.calcDoubleEV(double) ** 2;
  }

  /**
   * Calculates the EV of splitting a pair against a dealer upcard.
   * For each possible card drawn to the first split hand, computes the optimal
   * play (stand, hit, or double if DAS is allowed) and accumulates the resulting
   * win/tie/loss probabilities. Special handling for split aces when drawAces
   * is disabled (forced stand after one card). The second split hand is treated
   * symmetrically. Returns the total split EV multiplied by 2 (for both hands).
   * Returns NaN if the hand is not a valid pair.
   */
  calcSplit(
    cards: Card[],
    upCard: number,
    removePairCard?: boolean,
    excludeCards?: Card[],
  ): {
    noDouble: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    };
    double: { winProb: number; tieProb: number; loseProb: number; DBJ: number };
  } {
    let handProbs = {
      noDouble: { winProb: 0, tieProb: 0, loseProb: 0, DBJ: 0 },
      double: { winProb: 0, tieProb: 0, loseProb: 0, DBJ: 0 },
    };

    if (cards.length != 2) return handProbs;
    if (cards[0].rank != cards[1].rank) return handProbs;

    let shoe = this.genShoe();
    this.removeCardsFromShoe(shoe, [...cards, ...(excludeCards ?? [])]);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);
    let nextCardProbs = [];
    for (let rank = 1; rank <= 10; rank++) {
      const count = shoe.filter((c) => c.rank === rank).length;
      nextCardProbs.push(count / shoe.length);
    }

    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if (nextCardProbs[nextRank - 1] === 0) continue;
      const hand = [cards[0], { rank: nextRank }];

      const stand = this.calcStand(
        hand,
        upCard,
        excludeCards
          ? [...excludeCards, ...(removePairCard ? [cards[0]] : [])]
          : [...(removePairCard ? [cards[0]] : [])],
      );

      if (cards[0].rank === 1 && !this.dealerSettings.drawAces) {
        handProbs.noDouble.winProb +=
          stand.winProb * nextCardProbs[nextRank - 1];
        handProbs.noDouble.tieProb +=
          stand.tieProb * nextCardProbs[nextRank - 1];
        handProbs.noDouble.loseProb +=
          stand.loseProb * nextCardProbs[nextRank - 1];
        handProbs.noDouble.DBJ += stand.DBJ * nextCardProbs[nextRank - 1];
      } else {
        const hit = this.calcHit(
          hand,
          upCard,
          excludeCards
            ? [...excludeCards, ...(removePairCard ? [cards[0]] : [])]
            : [...(removePairCard ? [cards[0]] : [])],
        );
        const double = this.calcDouble(
          hand,
          upCard,
          excludeCards
            ? [...excludeCards, ...(removePairCard ? [cards[0]] : [])]
            : [...(removePairCard ? [cards[0]] : [])],
        );

        const hitEV = this.calcHitEV(hit);
        const doubleEV = this.calcDoubleEV(double);
        const standEV = this.calcStandEV(
          hand,
          stand,
          excludeCards
            ? [...excludeCards, ...(removePairCard ? [cards[0]] : [])]
            : [...(removePairCard ? [cards[0]] : [])],
        );

        let maxEV = 0;
        if (this.canDouble(hand) && this.dealerSettings.DAS)
          maxEV = Math.max(standEV, hitEV, doubleEV);
        else maxEV = Math.max(standEV, hitEV);

        if (maxEV === standEV) {
          handProbs.noDouble.winProb +=
            stand.winProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.tieProb +=
            stand.tieProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.loseProb +=
            stand.loseProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.DBJ += stand.DBJ * nextCardProbs[nextRank - 1];
        } else if (maxEV === hitEV) {
          handProbs.noDouble.winProb +=
            hit.winProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.tieProb +=
            hit.tieProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.loseProb +=
            hit.loseProb * nextCardProbs[nextRank - 1];
          handProbs.noDouble.DBJ += hit.DBJ * nextCardProbs[nextRank - 1];
        } else if (maxEV === doubleEV) {
          handProbs.double.winProb +=
            double.winProb * nextCardProbs[nextRank - 1];
          handProbs.double.tieProb +=
            double.tieProb * nextCardProbs[nextRank - 1];
          handProbs.double.loseProb +=
            double.loseProb * nextCardProbs[nextRank - 1];
          handProbs.double.DBJ += double.DBJ * nextCardProbs[nextRank - 1];
        }
      }
    }
    const total =
      handProbs.double.winProb +
      handProbs.double.tieProb +
      handProbs.double.loseProb +
      handProbs.double.DBJ +
      handProbs.noDouble.winProb +
      handProbs.noDouble.tieProb +
      handProbs.noDouble.loseProb +
      handProbs.noDouble.DBJ;

    handProbs.double.winProb /= total;
    handProbs.double.tieProb /= total;
    handProbs.double.loseProb /= total;
    handProbs.double.DBJ /= total;
    handProbs.noDouble.winProb /= total;
    handProbs.noDouble.tieProb /= total;
    handProbs.noDouble.loseProb /= total;
    handProbs.noDouble.DBJ /= total;

    return {
      noDouble: handProbs.noDouble,
      double: handProbs.double,
    };
  }

  calcSplitEV(split: {
    noDouble: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    };
    double: { winProb: number; tieProb: number; loseProb: number; DBJ: number };
  }) {
    const w2 = split.double.winProb;
    const t2 = split.double.tieProb;
    const l2 = split.double.loseProb;
    const w = split.noDouble.winProb;
    const t = split.noDouble.tieProb;
    const l = split.noDouble.loseProb;
    const d = split.noDouble.DBJ;

    if (this.dealerSettings.DAS) {
      const win4 = w2 ** 2;
      const win3 = 2 * w2 * w;
      const win2 = 2 * w2 * (t + t2) + w ** 2;
      const win1 = 2 * w2 * l + 2 * w * (t + t2);
      const lose1 = 2 * l2 * w + 2 * l * (t + t2);
      const lose2 = 2 * l2 * (t + t2) + l ** 2;
      const lose3 = 2 * l2 * l;
      const lose4 = l2 ** 2;
      return (
        4 * win4 +
        3 * win3 +
        2 * win2 +
        win1 -
        d -
        lose1 -
        2 * lose2 -
        3 * lose3 -
        4 * lose4
      );
    }

    const win2 = w ** 2;
    const win1 = 2 * w * t;
    const lose1 = 2 * l * t;
    const lose2 = l ** 2;
    return 2 * win2 + win1 - d - lose1 - 2 * lose2;
  }

  calcSplitVariance(split: {
    noDouble: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    };
    double: { winProb: number; tieProb: number; loseProb: number; DBJ: number };
  }) {
    const w2 = split.double.winProb;
    const t2 = split.double.tieProb;
    const l2 = split.double.loseProb;
    const w = split.noDouble.winProb;
    const t = split.noDouble.tieProb;
    const l = split.noDouble.loseProb;
    const EV = this.calcSplitEV(split);

    if (this.dealerSettings.DAS) {
      const win4 = w2 ** 2;
      const win3 = 2 * w2 * w;
      const win2 = 2 * w2 * (t + t2) + w ** 2;
      const tie = 2 * w2 * l2 + 2 * w * l + (t + t2) ** 2;
      const lose2 = 2 * l2 * (t + t2) + l ** 2;
      const lose3 = 2 * l2 * l;
      const lose4 = l2 ** 2;
      return (
        1 +
        15 * (win4 + lose4) +
        8 * (win3 + lose3) +
        3 * (win2 + lose2) -
        tie -
        EV ** 2
      );
    }

    const win2 = w ** 2;
    const tie = 2 * w * l + t ** 2;
    const lose2 = l ** 2;
    return 1 + 3 * (win2 + lose2) - tie - EV ** 2;
  }

  /**
   * Computes the probability of drawing each card rank (A through 10) as the
   * next card from the shoe. Under US peek rules, adjusts probabilities to
   * account for the fact that the dealer has already peeked and confirmed they
   * do not have a blackjack — this changes the effective distribution of
   * remaining cards when the upcard is an Ace or 10.
   */
  getNextCardProb(shoe: Card[], upCard: number) {
    let nextCardProbs = [];
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if ((upCard != 10 && upCard != 1) || this.dealerSettings.ENHC) {
        const count = shoe.filter((c) => c.rank === nextRank).length;
        nextCardProbs.push(count / shoe.length);
      } else if (upCard === 10) {
        const count = shoe.filter((c) => c.rank === nextRank).length;
        const aceCount = shoe.filter((c) => c.rank === 1).length;
        const cardsRemaning = shoe.length;
        if (nextRank === 1) nextCardProbs.push(aceCount / (cardsRemaning - 1));
        else {
          nextCardProbs.push(
            (count * (1 - 1 / (cardsRemaning - aceCount))) /
              (cardsRemaning - 1),
          );
        }
      } else if (upCard === 1) {
        const count = shoe.filter((c) => c.rank === nextRank).length;
        const tenCount = shoe.filter((c) => c.rank === 10).length;
        const cardsRemaning = shoe.length;
        if (nextRank === 10) nextCardProbs.push(tenCount / (cardsRemaning - 1));
        else {
          nextCardProbs.push(
            (count * (1 - 1 / (cardsRemaning - tenCount))) /
              (cardsRemaning - 1),
          );
        }
      }
    }
    // return this.normalize(nextCardProbs);
    return nextCardProbs;
  }

  /**
   * Returns true if the given hand is eligible to be doubled down,
   * based on whether it is a 2-card hand and the total is in the
   * configured list of allowed double totals.
   */
  canDouble(cards: Card[]) {
    return cards.length === 2;
  }

  /**
   * Generates a fresh unshuffled shoe containing the correct number of cards
   * for the configured deck count. Face cards (J, Q, K) are stored with rank 10.
   * Returns an array of Card objects representing the full shoe.
   */
  genShoe() {
    let shoe = [];
    for (let deck = 0; deck < this.dealerSettings.decks; deck++) {
      for (let s = 1; s <= 4; s++) {
        for (let r = 1; r <= 13; r++) {
          const rank = r >= 11 && r <= 13 ? 10 : r;
          const card: Card = { rank: rank };
          shoe.push(card);
        }
      }
    }
    return shoe;
  }

  /**
   * Removes a list of cards from a shoe in-place, one at a time.
   * Optionally tracks the running joint probability of drawing those specific
   * cards in sequence (multiplying prob by each card's probability before removal).
   * Throws an error if any card is not found in the shoe.
   * Returns the updated probability if one was provided.
   */
  removeCardsFromShoe(shoe: Card[], cards: Card[], prob?: number) {
    for (let card of cards) {
      const count = shoe.filter((c) => c.rank === card.rank).length;
      if (count === 0) throw new Error(`No ${card.rank} card found in shoe!`);
      if (prob) prob *= count / shoe.length;
      const index = shoe.findIndex((c) => c.rank === card.rank);
      shoe.splice(index, 1);
    }
    return prob;
  }

  /**
   * Determines whether a hand is soft (contains an ace counted as 11).
   * Calculates the hand total treating aces as 11, then reduces by 10
   * for each ace if the total exceeds 21. Returns true if any ace
   * is still being counted as 11 after this reduction.
   */
  isSoft(cards: Card[]) {
    let total = 0;
    let numAces = 0;

    for (const card of cards) {
      total += card.rank === 1 ? 11 : card.rank;
      if (card.rank === 1) numAces++;
    }

    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }

    return numAces > 0;
  }

  /**
   * Calculates the blackjack total of a hand, treating aces as 11
   * and reducing to 1 as needed to avoid busting. Returns the highest
   * possible total that does not exceed 21.
   */
  total(cards: Card[]) {
    let total = 0;
    let numAces = 0;

    for (let card of cards) {
      if (card.rank === 1) {
        total += 11;
        numAces++;
      } else {
        total += card.rank;
      }
    }

    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }

    return total;
  }

  /**
   * Recursively generates all possible dealer hands from a given starting hand,
   * following the dealer hit/stand rules (hit soft 17 if H17, stand on hard 17+).
   * Builds a tree of all possible card sequences, tracking the probability of
   * each card drawn at each step. Under ENHC rules with a player blackjack,
   * the dealer stops after revealing the hole card. Populates the outcomes and
   * probabilities arrays passed in by reference.
   */
  dealerOutcomeGenerator(
    dealerHand: Card[],
    outcomes: Card[][],
    handProbs: number[],
    probabilities: number[][],
    shoe: Card[],
    playerBJ: boolean,
  ): void {
    if (playerBJ && dealerHand.length >= 2) {
      outcomes.push(dealerHand);
      probabilities.push(handProbs);
      return;
    }

    const currentTotal = this.total(dealerHand);
    const isSoft17 = currentTotal === 17 && this.isSoft(dealerHand);
    if (
      currentTotal > 17 ||
      (currentTotal === 17 && (!isSoft17 || this.dealerSettings.S17))
    ) {
      outcomes.push(dealerHand);
      probabilities.push(handProbs);
      return;
    }

    for (let i = 1; i <= 10; i++) {
      const cardIndex = shoe.findIndex((shoeCard) => shoeCard.rank === i);
      if (cardIndex === -1) continue;
      const countInShoe = shoe.filter((card) => card.rank === i).length;
      let totalCards = shoe.length;
      const newProbabilities = [...handProbs, countInShoe / totalCards];

      const newShoe = [
        ...shoe.slice(0, cardIndex),
        ...shoe.slice(cardIndex + 1),
      ];
      const newCards = [...dealerHand, { rank: i }];

      this.dealerOutcomeGenerator(
        newCards,
        outcomes,
        newProbabilities,
        probabilities,
        newShoe,
        playerBJ,
      );
    }
  }

  /**
   * Returns an array of hand totals for a list of dealer hands,
   * using the standard blackjack total calculation.
   */
  getDealerTotals(outcomes: Card[][]) {
    let totals = [];
    for (let hand of outcomes) {
      totals.push(this.total(hand));
    }
    return totals;
  }

  /**
   * Converts a 2D probability matrix (one array of per-card probabilities per hand)
   * into a 1D array of total hand probabilities by multiplying the probabilities
   * of each card drawn within each hand together.
   */
  getTotalProbabilities(probabilities: number[][]) {
    let totalProbs = Array(probabilities.length).fill(1);
    for (let handIndex = 0; handIndex < probabilities.length; handIndex++) {
      for (let prob of probabilities[handIndex]) {
        totalProbs[handIndex] *= prob;
      }
    }
    return totalProbs;
  }

  /**
   * Aggregates dealer hand outcomes into a 7-element probability array:
   * [bust, 17, 18, 19, 20, 21 (non-BJ), blackjack].
   * Sums the probabilities of all hands that fall into each category,
   * treating 2-card 21s as blackjack and all other 21s as regular 21.
   */
  getDealerOutcomeCounts(
    outcomes: Card[][],
    probabilities: number[],
    normalize?: boolean,
  ) {
    const totals = this.getDealerTotals(outcomes);
    let counts = [0, 0, 0, 0, 0, 0, 0];
    for (let i = 0; i < totals.length; i++) {
      if (totals[i] >= 17 && totals[i] <= 20) {
        counts[totals[i] - 16] += probabilities[i];
      } else if (totals[i] === 21) {
        outcomes[i].length == 2
          ? (counts[6] += probabilities[i])
          : (counts[5] += probabilities[i]);
      } else {
        counts[0] += probabilities[i];
      }
    }
    if (!this.dealerSettings.ENHC) counts[6] = 0;
    return normalize ? this.normalize(counts) : counts;
  }

  /**
   * Normalizes an array of numbers so they sum to 1.
   * Modifies the array in place and returns it.
   */
  normalize(arr: number[]) {
    let sum = arr.reduce((acc, val) => acc + val, 0);
    for (let i = 0; i < arr.length; i++) {
      arr[i] = arr[i] / sum;
    }
    return arr;
  }

  /**
   * Returns true if two hands have the same card ranks (order-independent).
   * Sorts both hands by rank before comparing, so [3,5] and [5,3] are considered equal.
   */
  handsEqual(a: { rank: number }[], b: { rank: number }[]): boolean {
    if (a.length !== b.length) return false;
    const ranksA = a.map((c) => c.rank).sort();
    const ranksB = b.map((c) => c.rank).sort();
    return ranksA.every((rank, i) => rank === ranksB[i]);
  }

  /**
   * Finds the index of a hand in a precomputed data array by comparing card ranks.
   * Sorts the hand before searching so card order doesn't affect the lookup.
   * Returns -1 if the hand is not found.
   */
  getHandIndex(hand: Card[], data: any[]) {
    hand.sort((a, b) => a.rank - b.rank);
    return data.findIndex((h) => this.handsEqual(h[0], hand));
  }

  /**
   * Looks up precomputed EV data for a specific hand vs dealer upcard from a
   * loaded data file. Automatically selects the hard or soft data table based
   * on whether the hand is soft. Throws an error if the hand is not found in
   * the data, which would indicate a missing combination in the precomputed tables.
   */
  getData(cards: Card[], upCard: number, data: any) {
    let dataSet = this.getDataSet((data as any).probs);
    const softHand = this.isSoft(cards);
    if (softHand) {
      const handIndex = this.getHandIndex(cards, dataSet.soft[upCard - 1]);
      if (handIndex === -1) throw Error("No hand in data");
      return dataSet.soft[upCard - 1][handIndex][2];
    } else {
      const handIndex = this.getHandIndex(cards, dataSet.hard[upCard - 1]);
      if (handIndex === -1) throw Error("No hand in data");
      return dataSet.hard[upCard - 1][handIndex][2];
    }
  }
}
