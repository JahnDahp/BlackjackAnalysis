import { DealerSettingsObject } from "../SettingsObjects";
import loadData from "./LoadData";

interface Card {
  rank: number;
}

export class Probabilities {
  static readonly hands = [
    4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
    24, 25, 26, 27, 28, 29, 30, 31, /* These are Soft Totals: */ 12, 13, 14, 15,
    16, 17, 18, 19, 20, 21,
  ];
  static readonly SOFT_OFFSET = 28;
  static readonly SURRENDER_EV = -0.5;
  dealerSettings: DealerSettingsObject;
  dealerData: any = null;
  standData: any = null;
  hitData: any = null;
  doubleData: any = null;
  splitData: any = null;

  private constructor(dealerSettings: DealerSettingsObject) {
    this.dealerSettings = dealerSettings;
  }

  // Static factory method
  static async create(dealerSettings: DealerSettingsObject): Promise<Probabilities> {
    const instance = new Probabilities(dealerSettings); // pass settings here
    const data = await loadData();
    instance.dealerData = data.dealerData;
    instance.standData = data.standData;
    instance.hitData = data.hitData;
    instance.doubleData = data.doubleData;
    instance.splitData = data.splitData;
    return instance;
  }

  getDataSet(data: any) {
    switch (this.dealerSettings.decks) {
      case 1:
        if (this.dealerSettings.S17) {
          if (this.dealerSettings.ENHC) {
            return data.oneDeck.S17.enhc;
          } else {
            return data.oneDeck.S17.us;
          }
        } else {
          if (this.dealerSettings.ENHC) {
            return data.oneDeck.H17.enhc;
          } else {
            return data.oneDeck.H17.us;
          }
        }
      case 2:
        if (this.dealerSettings.S17) {
          if (this.dealerSettings.ENHC) {
            return data.twoDeck.S17.enhc;
          } else {
            return data.twoDeck.S17.us;
          }
        } else {
          if (this.dealerSettings.ENHC) {
            return data.twoDeck.H17.enhc;
          } else {
            return data.twoDeck.H17.us;
          }
        }
      case 4:
        if (this.dealerSettings.S17) {
          if (this.dealerSettings.ENHC) {
            return data.fourDeck.S17.enhc;
          } else {
            return data.fourDeck.S17.us;
          }
        } else {
          if (this.dealerSettings.ENHC) {
            return data.fourDeck.H17.enhc;
          } else {
            return data.fourDeck.H17.us;
          }
        }
      case 6:
        if (this.dealerSettings.S17) {
          if (this.dealerSettings.ENHC) {
            return data.sixDeck.S17.enhc;
          } else {
            return data.sixDeck.S17.us;
          }
        } else {
          if (this.dealerSettings.ENHC) {
            return data.sixDeck.H17.enhc;
          } else {
            return data.sixDeck.H17.us;
          }
        }
      case 8:
        if (this.dealerSettings.S17) {
          if (this.dealerSettings.ENHC) {
            return data.eightDeck.S17.enhc;
          } else {
            return data.eightDeck.S17.us;
          }
        } else {
          if (this.dealerSettings.ENHC) {
            return data.eightDeck.H17.enhc;
          } else {
            return data.eightDeck.H17.us;
          }
        }
    }
  }

  runSims() {
    // console.log(this.calculateStandForHandVar([{ rank: 10 }, { rank: 10 }], 1));
  }

  downloadDealerProbabilities() {
    const deckKeys = [1, 2, 4, 6, 8];
    let currentDeckCount = [];
    for (let decks of deckKeys) {
      let currentS17 = [];
      for (let soft17 of [false, true]) {
        let currentEnhc = [];
        for (let euro of [false, true]) {
          this.dealerSettings = {
            ...this.dealerSettings,
            decks,
            S17: soft17,
            ENHC: euro,
          };
          console.log(
            `${decks}Decks, ${soft17 ? "S17" : "H17"}, ${euro ? "ENHC" : "US"}`
          );
          currentEnhc.push(this.runDealerSim());
        }
        const us = currentEnhc[0];
        const enhc = currentEnhc[1];
        currentS17.push({ us, enhc });
      }
      const H17 = currentS17[0];
      const S17 = currentS17[1];
      currentDeckCount.push({ H17, S17 });
    }
    const oneDeck = currentDeckCount[0];
    const twoDeck = currentDeckCount[1];
    const fourDeck = currentDeckCount[2];
    const sixDeck = currentDeckCount[3];
    const eightDeck = currentDeckCount[4];

    const cache = {
      outcomes: { oneDeck, twoDeck, fourDeck, sixDeck, eightDeck },
    };

    const blob = new Blob([JSON.stringify(cache)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dealer.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  downloadHandProbabilities(decision: string) {
    const deckKeys = [1, 2, 4, 6, 8];
    let currentDeckCount = [];
    for (let decks of deckKeys) {
      let currentS17 = [];
      for (let soft17 of [false, true]) {
        let currentEnhc = [];
        for (let euro of [false, true]) {
          this.dealerSettings = {
            ...this.dealerSettings,
            decks,
            S17: soft17,
            ENHC: euro,
          };

          const hard = [];
          for (let upCard = 1; upCard <= 10; upCard++) {
            const upcardResults = [];

            for (let totalTarget = 4; totalTarget <= 21; totalTarget++) {
              console.log(
                `${decks}Decks, ${soft17 ? "S17" : "H17"}, ${
                  euro ? "ENHC" : "US"
                }, Hard ${totalTarget} vs ${upCard === 1 ? "A" : upCard}`
              );
              const candidateHands = this.runHandSim(
                totalTarget,
                upCard,
                false
              ).allHands;

              for (let hand of candidateHands) {
                if (decision === "double" && hand.hand.length > 2) continue;
                const handTotal = this.total(hand.hand);
                if (handTotal === totalTarget) {
                  let calculation;
                  if (decision === "stand")
                    calculation = this.calcStand(hand.hand, upCard);
                  if (decision === "hit")
                    calculation = this.calcHit(hand.hand, upCard);
                  // if (decision === "double")
                  //   calculation = this.calculateDoubleForHand(
                  //     hand.hand,
                  //     upCard
                  //   );
                  upcardResults.push([hand.hand, hand.totalProb, calculation]);
                }
              }
            }
            hard.push(upcardResults);
          }

          const soft = [];
          for (let upCard = 1; upCard <= 10; upCard++) {
            const upcardResults = [];

            for (let totalTarget = 12; totalTarget <= 21; totalTarget++) {
              console.log(
                `${decks}Decks, ${soft17 ? "S17" : "H17"}, ${
                  euro ? "ENHC" : "US"
                }, Soft ${totalTarget} vs ${upCard === 1 ? "A" : upCard}`
              );
              const candidateHands = this.runHandSim(
                totalTarget,
                upCard,
                true
              ).allHands;

              for (let hand of candidateHands) {
                if (decision === "double" && hand.hand.length > 2) continue;
                const handTotal = this.total(hand.hand);
                if (handTotal === totalTarget) {
                  let calculation;
                  if (decision === "stand")
                    calculation = this.calcStand(hand.hand, upCard);
                  if (decision === "hit")
                    calculation = this.calcHit(hand.hand, upCard);
                  if (decision === "double")
                    calculation = this.calculateDoubleForHand(
                      hand.hand,
                      upCard
                    );
                  upcardResults.push([hand.hand, hand.totalProb, calculation]);
                }
              }
            }
            soft.push(upcardResults);
          }
          currentEnhc.push({ hard, soft });
        }
        const us = currentEnhc[0];
        const enhc = currentEnhc[1];
        currentS17.push({ us, enhc });
      }
      const H17 = currentS17[0];
      const S17 = currentS17[1];
      currentDeckCount.push({ H17, S17 });
    }
    const oneDeck = currentDeckCount[0];
    const twoDeck = currentDeckCount[1];
    const fourDeck = currentDeckCount[2];
    const sixDeck = currentDeckCount[3];
    const eightDeck = currentDeckCount[4];

    const cache = {
      EV: { oneDeck, twoDeck, fourDeck, sixDeck, eightDeck },
    };

    const blob = new Blob([JSON.stringify(cache)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${decision}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  downloadPairProbabilities() {
    const deckKeys = [1, 2, 4, 6, 8];
    let currentDeckCount = [];
    for (let decks of deckKeys) {
      let currentS17 = [];
      for (let soft17 of [false, true]) {
        let currentEnhc = [];
        for (let euro of [false, true]) {
          this.dealerSettings = {
            ...this.dealerSettings,
            decks,
            S17: soft17,
            ENHC: euro,
          };

          const fullTable = [];
          for (let upCard = 1; upCard <= 10; upCard++) {
            const upcardResults = [];

            for (let pairVal = 1; pairVal <= 10; pairVal++) {
              console.log(
                `${decks}Decks, ${soft17 ? "S17" : "H17"}, ${
                  euro ? "ENHC" : "US"
                }, Hard ${pairVal} vs ${upCard === 1 ? "A" : upCard}`
              );
              let EV = this.calculateSplitForHand(
                [{ rank: pairVal }, { rank: pairVal }],
                upCard,
                2
              );
              upcardResults.push([[{ rank: pairVal }, { rank: pairVal }], EV]);
            }
            fullTable.push(upcardResults);
          }
          currentEnhc.push(fullTable);
        }
        const us = currentEnhc[0];
        const enhc = currentEnhc[1];
        currentS17.push({ us, enhc });
      }
      const H17 = currentS17[0];
      const S17 = currentS17[1];
      currentDeckCount.push({ H17, S17 });
    }
    const oneDeck = currentDeckCount[0];
    const twoDeck = currentDeckCount[1];
    const fourDeck = currentDeckCount[2];
    const sixDeck = currentDeckCount[3];
    const eightDeck = currentDeckCount[4];

    const cache = {
      EV: { oneDeck, twoDeck, fourDeck, sixDeck, eightDeck },
    };

    const blob = new Blob([JSON.stringify(cache)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `split.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  runDealerSim() {
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
        false
      );
      upCardOutcomes.push(
        this.getOutcomeProbabilities(
          outcomes,
          this.getTotalProbabilities(probabilities)
        )
      );
    }
    return upCardOutcomes;
  }

  runDealerSimGivenHand(
    handTotal: number,
    dealerUpcard: number,
    soft: boolean
  ) {
    const handSim = this.runHandSim(handTotal, dealerUpcard, soft);
    const allHands = handSim.allHands;
    const nextCardProbs = handSim.nextCardProbs;
    const allHandOutcomes: (number | null)[][] = [];
    const handProbs: number[] = [];
    let BJCount = 0;

    for (let hand of allHands) {
      let shoe = this.genShoe();
      const isBlackjack =
        this.total(hand.hand) === 21 && hand.hand.length === 2;
      if (isBlackjack) BJCount++;
      let prob = 1;

      prob = this.removeCardsFromShoe(shoe, hand.hand, prob) ?? 1;
      prob =
        this.removeCardsFromShoe(shoe, [{ rank: dealerUpcard }], prob) ?? 1;

      const outcomes: Card[][] = [];
      const probabilities: number[][] = [];
      this.dealerOutcomeGenerator(
        [{ rank: dealerUpcard }],
        outcomes,
        [prob],
        probabilities,
        shoe,
        isBlackjack
      );
      const result = this.getOutcomeProbabilities(
        outcomes,
        this.getTotalProbabilities(probabilities)
      );
      allHandOutcomes.push(result);
      handProbs.push(prob);
    }

    const BJRatio = BJCount / allHands.length;
    const numOutcomes = 6 + (this.dealerSettings.ENHC ? 1 : 0);
    const trueOutcomeProbs = Array(numOutcomes).fill(0);
    const totalProb = handProbs.reduce((a, b) => a + b, 0);

    for (let outcome = 0; outcome < numOutcomes; outcome++) {
      for (let i = 0; i < allHandOutcomes.length; i++) {
        trueOutcomeProbs[outcome] +=
          (allHandOutcomes[i][outcome] ?? 0) * (handProbs[i] / totalProb);
      }
    }

    return { trueOutcomeProbs, BJRatio, nextCardProbs };
  }

  runDealerSimGivenCards(
    cards: Card[],
    dealerUpcard: number,
    excludeCards?: Card[]
  ) {
    let shoe = this.genShoe();
    const isBlackjack = this.total(cards) === 21 && cards.length === 2;
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
      isBlackjack
    );
    const result = this.getOutcomeProbabilities(
      outcomes,
      this.getTotalProbabilities(probabilities)
    );

    return { result, isBlackjack };
  }

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
        (c) => c.rank === playerRank
      );
      const playerCard = shoeAfterPlayer.splice(playerIndex, 1)[0];
      const probPlayer = playerCount / baseShoe.length;

      const upCardCount = shoeAfterPlayer.filter(
        (c) => c.rank === upCard
      ).length;
      if (upCardCount === 0) continue;
      const dealerIndex = shoeAfterPlayer.findIndex((c) => c.rank === upCard);
      shoeAfterPlayer.splice(dealerIndex, 1);
      const probUpCard = upCardCount / (baseShoe.length - 1);

      const recurse = (
        hand: Card[],
        shoe: Card[],
        handProbs: number[],
        minRank: number
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
                  (c) => c.rank === nextRank
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

  getDealerData() {
    return this.getDataSet((this.dealerData as any).outcomes);
  }

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
          false
        ).allHands;
        let EVs = [];
        let probs = [];
        for (let hand of candidateHands) {
          if (decision === "double" && hand.hand.length > 2) continue;
          const handTotal = this.total(hand.hand);
          if (handTotal === totalTarget) {
            EVs.push(this.getData(hand.hand, upCard, data));
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
          true
        ).allHands;
        let EVs = [];
        let probs = [];
        for (let hand of candidateHands) {
          if (decision === "double" && hand.hand.length > 2) continue;
          const handTotal = this.total(hand.hand);
          if (handTotal === totalTarget) {
            EVs.push(this.getData(hand.hand, upCard, data));
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

  getSplitData(cards: Card[], upCard: number) {
    let dataSet = this.getDataSet((this.splitData as any).EV);
    let EV = -100;
    const handIndex = this.getHandIndex(cards, dataSet[upCard - 1]);
    if (handIndex !== -1) {
      EV = dataSet[upCard - 1][handIndex][1];
    }
    return EV;
  }

  getSplitProbs() {
    const splits = [];
    let dataSet = this.getDataSet((this.splitData as any).EV);
    for (let upCard = 1; upCard <= 10; upCard++) {
      const upcardResults = [];
      for (let totalTarget = 1; totalTarget <= 10; totalTarget++) {
        let EV = -99;
        const handIndex = this.getHandIndex(
          [{ rank: totalTarget }, { rank: totalTarget }],
          dataSet[upCard - 1]
        );
        if (handIndex !== -1) {
          EV = dataSet[upCard - 1][handIndex][1];
        }
        upcardResults.push(EV);
      }
      splits.push(upcardResults);
    }
    return splits;
  }

  isBlackjack(cards: Card[], excludeCards: Card[] | undefined) {
    const total = this.total(cards);
    return cards.length === 2 && total === 21 && !excludeCards;
  }

  calcStand(
    cards: Card[],
    upCard: number,
    excludeCards?: Card[]
  ) {
    const total = this.total(cards);
    let winProb = 0;
    let tieProb = 0;
    let loseProb = 0;
    let DBJ = 0;
    let outcome = 0;

    if (total > 21) {
      loseProb = 1;
      return this.calcStandEV(cards, { winProb, tieProb, loseProb, DBJ }, excludeCards);
    }

    const dealerProbs = this.runDealerSimGivenCards(
      cards,
      upCard,
      excludeCards
    );

    DBJ = dealerProbs.result[6];

    if (this.isBlackjack(cards, excludeCards)) {
      winProb = 1;
      if (this.dealerSettings.ENHC) {
        tieProb = DBJ;
        winProb = 1 - tieProb;
      }
      return this.calcStandEV(cards, { winProb, tieProb, loseProb, DBJ }, excludeCards);
    }

    winProb += dealerProbs.result[outcome++] ?? 0;
    while (total > outcome + 16 && outcome < 6) {
      winProb += dealerProbs.result[outcome++] ?? 0;
    }
    if (total === outcome + 16 && outcome < 6) {
      tieProb = dealerProbs.result[outcome++] ?? 0;
    }
    while (total < outcome + 16 && outcome < 6) {
      loseProb += dealerProbs.result[outcome++] ?? 0;
    }
    if (this.dealerSettings.ENHC) {
      loseProb += dealerProbs.result[outcome] ?? 0;
    }
    return this.calcStandEV(cards, { winProb, tieProb, loseProb, DBJ }, excludeCards);
  }

  calcStandEV(
    hand: Card[],
    stand: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    },
    excludeCards?: Card[]
  ) {
    let BJPay = 1;
    if (this.isBlackjack(hand, excludeCards)) BJPay = this.dealerSettings.BJPay;
    return BJPay * (stand.winProb - stand.loseProb);
  }

  calcStandVariance(
    hand: Card[],
    stand: {
      winProb: number;
      tieProb: number;
      loseProb: number;
      DBJ: number;
    },
    excludeCards?: Card[]
  ) {
    return (
      1 - stand.tieProb - (this.calcStandEV(hand, stand, excludeCards) ^ 2)
    );
  }

  calcHit(
    cards: Card[],
    upCard: number,
    excludeCards?: Card[]
  ) {
    let winProb = 0;
    let tieProb = 0;
    let loseProb = 0;
    let DBJ = 0;

    let shoe = this.genShoe();
    if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
    this.removeCardsFromShoe(shoe, cards);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

    let nextCardProbs = this.getNextCardProb(shoe, upCard);

    let EV = 0;
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if (shoe.filter((c) => c.rank === nextRank).length === 0) continue;
      const hand = [...cards, { rank: nextRank }];

      let standEV;
      if (excludeCards) {
        standEV = this.calcStand(hand, upCard, excludeCards);
      } else {
        standEV = this.getData(hand, upCard, this.standData);
      }
      const hitEV = this.calcHit(hand, upCard, excludeCards);
      const maxEV = Math.max(hitEV, standEV);
      EV += maxEV * nextCardProbs[nextRank - 1]
    }
    return EV;
  }

  calcHitEV(hit: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return hit.winProb - hit.loseProb;
  }

  calcHitVariance(hit: {
    winProb: number;
    tieProb: number;
    loseProb: number;
    DBJ: number;
  }) {
    return 1 - hit.tieProb - (this.calcHitEV(hit) ^ 2);
  }

  calculateDoubleForHand(cards: Card[], upCard: number, excludeCards?: Card[]) {
    let shoe = this.genShoe();

    if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
    this.removeCardsFromShoe(shoe, cards);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

    let nextCardProbs = this.getNextCardProb(shoe, upCard);

    let hitEV = 0;
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if (shoe.filter((c) => c.rank === nextRank).length === 0) continue;

      let nextStand = 0;
      if (excludeCards) {
        nextStand = this.calcStand(
          [...cards, { rank: nextRank }],
          upCard,
          excludeCards
        );
      } else {
        nextStand = this.getData(
          [...cards, { rank: nextRank }],
          upCard,
          this.standData
        );
      }

      hitEV += nextStand * nextCardProbs[nextRank - 1];
    }
    return 2 * hitEV;
  }

  calculateSplitForHand(cards: Card[], upCard: number, hands: number) {
    if (cards.length != 2) return -99;
    if (cards[0].rank != cards[1].rank) return -99;
    if (hands > this.dealerSettings.splits + 1) return -99;

    let shoe = this.genShoe();
    this.removeCardsFromShoe(shoe, cards);
    this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

    let fullSplitEv = 0;
    let nextCardProbs = this.getNextCardProb(shoe, upCard);
    for (let nextRank = 1; nextRank <= 10; nextRank++) {
      if (nextCardProbs[nextRank - 1] === 0) continue;
      let EV = -99;
      if (cards[0].rank === 1 && !this.dealerSettings.drawAces) {
        EV = this.calcStand([cards[0], { rank: nextRank }], upCard, [
          cards[1],
        ]);
      } else {
        EV = this.getMaxHSD([cards[0], { rank: nextRank }], upCard, [
          cards[1],
        ]).EV;
      }
      fullSplitEv += EV * nextCardProbs[nextRank - 1];
    }
    return fullSplitEv * 2;
  }

  // calculateSplitForHandOldWay(
  //   cards: Card[],
  //   upCard: number,
  //   hands: number,
  //   excludeCards?: Card[]
  // ) {
  //   if (cards.length != 2) return -99;
  //   if (cards[0].rank != cards[1].rank) return -99;
  //   if (hands > this.dealerSettings.splits + 1) return -99;

  //   let shoe = this.genShoe();
  //   if (excludeCards) this.removeCardsFromShoe(shoe, excludeCards);
  //   this.removeCardsFromShoe(shoe, cards);
  //   this.removeCardsFromShoe(shoe, [{ rank: upCard }]);

  //   // ASSUMPTIONS: Each split hand is played with only one other pair card in mind. Every split is equal in EV.

  //   let fullSplitEv = 0;
  //   let nextCardProbs1 = this.getNextCardProb(shoe, upCard);
  //   for (let nextRank1 = 1; nextRank1 <= 10; nextRank1++) {
  //     if (nextCardProbs1[nextRank1 - 1] === 0) continue;
  //     let shoeCopy1 = [...shoe];
  //     this.removeCardsFromShoe(shoeCopy1, [{ rank: nextRank1 }]);
  //     const hand1 = [{ rank: cards[0].rank }, { rank: nextRank1 }];

  //     let nextCardProbs2 = this.getNextCardProb(shoeCopy1, upCard);

  //     for (let nextRank2 = 1; nextRank2 <= 10; nextRank2++) {
  //       if (nextCardProbs2[nextRank2 - 1] === 0) continue;
  //       let shoeCopy2 = [...shoeCopy1];
  //       this.removeCardsFromShoe(shoeCopy2, [{ rank: nextRank2 }]);
  //       const hand2 = [{ rank: cards[1].rank }, { rank: nextRank2 }];

  //       const allSplitHands = this.calculateHandsAfterSplit(
  //         hand1,
  //         upCard,
  //         shoeCopy2
  //       );
  //       const allHands = allSplitHands.allHands;
  //       const allProbs = this.normalize(allSplitHands.allProbs);

  //       let firstSplitEV = 0;
  //       for (let handIndex = 0; handIndex < allHands.length; handIndex++) {
  //         firstSplitEV += allHands[handIndex][1] * allProbs[handIndex];
  //       }

  //       let secondSplitEV = 0;
  //       for (let handIndex = 0; handIndex < allHands.length; handIndex++) {
  //         const maxEV = this.getMaxHSD(hand2, upCard, allHands[handIndex][0]);
  //         secondSplitEV += maxEV.EV * allProbs[handIndex];
  //       }
  //       fullSplitEv +=
  //         (firstSplitEV + secondSplitEV) *
  //         nextCardProbs1[nextRank1 - 1] *
  //         nextCardProbs2[nextRank2 - 1];
  //     }
  //   }
  //   return fullSplitEv;
  // }

  // calculateHandsAfterSplit(cards: Card[], upCard: number, shoe: Card[]) {
  //   let allHands: [Card[], number][] = [];
  //   let allProbs: number[] = [];

  //   const recurse = (
  //     currentCards: Card[],
  //     currentShoe: Card[],
  //     prob: number
  //   ) => {
  //     if (this.total(currentCards) > 21) {
  //       allHands.push([currentCards, -1]);
  //       allProbs.push(prob);
  //       return;
  //     }

  //     const maxEV = this.getMaxHSD(currentCards, upCard, [cards[0]]);
  //     if (maxEV.result === "S") {
  //       allHands.push([currentCards, maxEV.EV]);
  //       allProbs.push(prob);
  //       return;
  //     }

  //     let nextCardProbs = this.getNextCardProb(currentShoe, upCard);

  //     for (let nextRank = 1; nextRank <= 10; nextRank++) {
  //       const nextRankIndex = currentShoe.findIndex(
  //         (val) => val.rank === nextRank
  //       );
  //       if (nextRankIndex === -1) continue;
  //       const nextHand = [...currentCards, { rank: nextRank }];
  //       if (maxEV.result === "D") {
  //         allHands.push([nextHand, maxEV.EV]);
  //         allProbs.push(prob * nextCardProbs[nextRank - 1]);
  //       } else {
  //         const nextShoe = [...currentShoe];
  //         this.removeCardsFromShoe(nextShoe, [{ rank: nextRank }]);
  //         recurse(nextHand, nextShoe, prob * nextCardProbs[nextRank - 1]);
  //       }
  //     }
  //   };

  //   recurse(cards, shoe, 1);
  //   return { allHands, allProbs };
  // }

  getMaxHSD(cards: Card[], upCard: number, excludeCards?: Card[]) {
    let nextStand = 0;
    if (excludeCards) {
      nextStand = this.calcStand(cards, upCard, excludeCards);
    } else {
      nextStand = this.getData(cards, upCard, this.standData);
    }

    let nextHit = 0;
    if (excludeCards) {
      nextHit = this.calcHit(cards, upCard, excludeCards);
    } else {
      nextHit = this.getData(cards, upCard, this.hitData);
    }

    let nextDouble = null;
    if (this.canDouble(cards) && this.dealerSettings.DAS) {
      if (excludeCards) {
        nextDouble = this.calculateDoubleForHand(cards, upCard, excludeCards);
      } else {
        nextDouble = this.getData(cards, upCard, this.doubleData);
      }
    }
    const options = [nextStand, nextHit];
    if (nextDouble !== null) options.push(nextDouble);
    const EV = Math.max(...options);
    const result = EV === nextStand ? "S" : EV === nextHit ? "H" : "D";
    return { EV, result };
  }

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
            (count * (1 - 1 / (cardsRemaning - aceCount))) / (cardsRemaning - 1)
          );
        }
      } else if (upCard === 1) {
        const count = shoe.filter((c) => c.rank === nextRank).length;
        const tenCount = shoe.filter((c) => c.rank === 10).length;
        const cardsRemaning = shoe.length;
        if (nextRank === 10) nextCardProbs.push(tenCount / (cardsRemaning - 1));
        else {
          nextCardProbs.push(
            (count * (1 - 1 / (cardsRemaning - tenCount))) / (cardsRemaning - 1)
          );
        }
      }
    }
    return this.normalize(nextCardProbs);
  }

  canDouble(cards: Card[]) {
    return (
      cards.length === 2 &&
      this.dealerSettings.doubles.includes(this.total(cards))
    );
  }

  // Generates a random shoe of a given deck count
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

  removeCardsFromShoe(
    shoe: Card[],
    cards: Card[],
    prob?: number,
  ) {
    for (let card of cards) {
      const count = shoe.filter((c) => c.rank === card.rank).length;
      if (count === 0) throw new Error(`No ${card.rank} card found in shoe!`);
      if (prob) prob *= count / shoe.length;
      const index = shoe.findIndex((c) => c.rank === card.rank);
      shoe.splice(index, 1);
    }
    return prob;
  }

  // Determines if a hand is soft
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

  // Calculates the total of a hand
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

  // Returns an array of possible dealer hands,
  // and a probability matrix with the probability of each card being drawn in that hand
  dealerOutcomeGenerator(
    dealerHand: Card[],
    outcomes: Card[][],
    handProbs: number[],
    probabilities: number[][],
    shoe: Card[],
    playerBJ: boolean
  ): void {
    // If the player has a blackjack and the dealer's hole card is revealed, the dealer must stop drawing
    if (playerBJ && dealerHand.length >= 2) {
      outcomes.push(dealerHand);
      probabilities.push(handProbs);
      return;
    }

    // Logic to determine if a dealer should continue hitting
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

    // Loop to create every possible dealer hand
    for (let i = 1; i <= 10; i++) {
      // Calculates probability of each card
      const cardIndex = shoe.findIndex((shoeCard) => shoeCard.rank === i);
      if (cardIndex === -1) continue;
      const countInShoe = shoe.filter((card) => card.rank === i).length;
      let totalCards = shoe.length;
      const newProbabilities = [...handProbs, countInShoe / totalCards];

      // Updates the shoe and hand
      const newShoe = [
        ...shoe.slice(0, cardIndex),
        ...shoe.slice(cardIndex + 1),
      ];
      const newCards = [...dealerHand, { rank: i }];

      // Recursively calls the function with new dealer hand information
      this.dealerOutcomeGenerator(
        newCards,
        outcomes,
        newProbabilities,
        probabilities,
        newShoe,
        playerBJ
      );
    }
  }

  // Returns dealer hand totals
  getDealerTotals(outcomes: Card[][]) {
    let totals = [];
    for (let hand of outcomes) {
      totals.push(this.total(hand));
    }
    return totals;
  }

  // Computes the total probabilites of each hand from the probabilities of each card
  getTotalProbabilities(probabilities: number[][]) {
    let totalProbs = Array(probabilities.length).fill(1);
    for (let handIndex = 0; handIndex < probabilities.length; handIndex++) {
      for (let prob of probabilities[handIndex]) {
        totalProbs[handIndex] *= prob;
      }
    }
    return totalProbs;
  }

  // Returns normalized probabilities of a dealer reaching a given dealer outcome, Bust, 17, 18, 19, 20, 21, BJ
  getOutcomeProbabilities(outcomes: Card[][], probabilities: number[]) {
    let counts = this.getDealerOutcomeCounts(outcomes, probabilities);
    if (!this.dealerSettings.ENHC) {
      const DBJ = counts[6];
      counts = counts.slice(0, -1);
      return [...this.normalize(counts), DBJ];
    }
    return [...this.normalize(counts)];
  }

  // Returns the counted dealer outcomes
  getDealerOutcomeCounts(outcomes: Card[][], probabilities: number[]) {
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
    return counts;
  }

  // Normalizes an array of numbers
  normalize(arr: number[]) {
    let sum = arr.reduce((acc, val) => acc + val, 0);
    for (let i = 0; i < arr.length; i++) {
      arr[i] = arr[i] / sum;
    }
    return arr;
  }

  handsEqual(a: { rank: number }[], b: { rank: number }[]): boolean {
    if (a.length !== b.length) return false;
    const ranksA = a.map((c) => c.rank).sort();
    const ranksB = b.map((c) => c.rank).sort();
    return ranksA.every((rank, i) => rank === ranksB[i]);
  }

  getHandIndex(hand: Card[], data: any[]) {
    hand.sort((a, b) => a.rank - b.rank);
    return data.findIndex((h) => this.handsEqual(h[0], hand));
  }

  getData(
    cards: Card[],
    upCard: number,
    data: any
  ) {
    let dataSet = this.getDataSet((data as any).EV);
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
