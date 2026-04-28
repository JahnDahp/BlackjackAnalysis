import { DealerSettingsObject } from "../SettingsObjects.js";

function shuffle(array: Card[]): Card[] {
  const result = [...array];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export class Card {
  rank: number;

  constructor(rank: number) {
    this.rank = rank;
  }

  getRank() {
    if (this.rank >= 11 && this.rank <= 13) return 10;
    if (this.rank === 1) return 11;
    return this.rank;
  }

  canSplit(card: Card) {
    return this.getRank() === card.getRank();
  }

  isAce() {
    return this.rank == 1;
  }
}

export class Shoe {
  shoe: Card[];
  deckNumber: number;

  constructor(deckNumber: number) {
    this.deckNumber = deckNumber;
    let shoe = [];
    for (let deck = 0; deck < deckNumber; deck++) {
      for (let s = 0; s < 4; s++) {
        for (let r = 1; r < 14; r++) {
          let card = new Card(r);
          shoe.push(card);
        }
      }
    }
    this.shoe = shuffle(shoe);
  }

  size() {
    return this.shoe.length;
  }

  empty() {
    return this.shoe.length === 0;
  }

  topPop(rank?: number): Card {
    if (rank !== undefined) {
      const matchingIndices = this.shoe
        .map((card, index) => (card.rank === rank ? index : -1))
        .filter((index) => index !== -1);

      if (matchingIndices.length === 0)
        throw new Error(`No card of rank ${rank} in shoe`);

      const randomIndex =
        matchingIndices[Math.floor(Math.random() * matchingIndices.length)];
      const [card] = this.shoe.splice(randomIndex, 1);
      return card;
    }

    const card = this.shoe.pop();
    if (!card) throw new Error("Shoe is empty");
    return card;
  }

  removeOneNot(excludeRank: number): void {
    const rankCounts: number[] = new Array(11).fill(0);
    for (const card of this.shoe) {
      if (card.rank !== excludeRank) rankCounts[card.rank]++;
    }

    const total = rankCounts.reduce((a, b) => a + b, 0);
    if (total === 0)
      throw new Error(`No card excluding rank ${excludeRank} in shoe`);

    let pick = Math.floor(Math.random() * total);
    for (let r = 1; r <= 10; r++) {
      pick -= rankCounts[r];
      if (pick < 0) {
        this.topPop(r);
        return;
      }
    }
  }
}

export class Hand {
  cards: Card[];
  bet: number;

  constructor(hand: Card[], bet: number) {
    this.cards = [];
    this.bet = bet;
    for (let card of hand) {
      this.hit(card);
    }
  }

  total() {
    let total = 0;
    let numSoftAces = 0;
    for (let card of this.cards) {
      if (card.getRank() === 11) numSoftAces++;
      total += card.getRank();
    }
    while (total > 21 && numSoftAces > 0) {
      total -= 10;
      numSoftAces--;
    }
    return total;
  }

  isSoft() {
    let total = 0;
    let numAces = 0;
    for (const card of this.cards) {
      if (card.rank === 1) {
        total += 11;
        numAces++;
      } else {
        total += card.getRank();
      }
    }
    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }
    return numAces > 0;
  }

  isBlackjack() {
    return this.total() === 21 && this.cards.length === 2;
  }

  hit(hitCard: Card) {
    this.cards.push(hitCard);
  }

  canSplit() {
    if (this.cards.length != 2) return false;
    return this.cards[0].getRank() === this.cards[1].getRank();
  }

  split(newCard1: Card, newCard2: Card) {
    let splitCard = this.cards[1];
    this.cards.pop();
    this.hit(newCard1);
    return new Hand([splitCard, newCard2], this.bet);
  }

  isBust() {
    return this.total() > 21;
  }
}

export class Dealer {
  cards: Card[];
  S17: boolean;

  constructor(up: Card, S17: boolean) {
    this.cards = [];
    this.S17 = S17;
    this.hit(up);
  }

  total(onlyUp: boolean) {
    if (onlyUp) return this.cards[0].getRank();
    let total = 0;
    let numSoftAces = 0;
    for (let card of this.cards) {
      if (card.getRank() === 11) numSoftAces++;
      total += card.getRank();
    }
    while (total > 21 && numSoftAces > 0) {
      total -= 10;
      numSoftAces--;
    }
    return total;
  }

  isSoft() {
    let total = 0;
    let numAces = 0;
    for (const card of this.cards) {
      if (card.rank === 1) {
        total += 11;
        numAces++;
      } else {
        total += card.getRank();
      }
    }
    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }
    return numAces > 0;
  }

  isBlackjack() {
    if (this.cards.length < 2) return false;
    return this.total(false) === 21 && this.cards.length === 2;
  }

  hit(hitCard: Card) {
    this.cards.push(hitCard);
  }

  isBust() {
    return this.total(false) > 21;
  }

  stop() {
    if (this.total(false) > 17) return true;
    if (this.total(false) < 17) return false;
    if (this.isSoft()) return this.S17;
    return true;
  }
}

export class BlackjackSimulator {
  static readonly STAND = 0;
  static readonly HIT = 1;
  static readonly DOUBLE = 2;
  static readonly SPLIT = 3;

  rules: DealerSettingsObject;
  shoe: Shoe;
  hands: Hand[];
  dealer: Dealer;
  hardChoices: number[];
  softChoices: number[];
  currentHand: number;
  upCard: number;
  gain: number;

  constructor(rules: DealerSettingsObject) {
    this.rules = rules;
    const temp = new Card(0);
    this.shoe = new Shoe(0);
    this.hands = [];
    this.dealer = new Dealer(temp, false);
    this.hardChoices = [];
    this.softChoices = [];
    this.currentHand = 0;
    this.upCard = 0;
    this.gain = 0;
  }

  startSim(
    hand: number[],
    upCard: number,
    choice: number,
    hardChoices: number[],
    softChoices: number[],
  ) {
    this.shoe = new Shoe(this.rules.decks);
    this.gain = 0;
    this.currentHand = 0;
    this.upCard = upCard;
    this.hardChoices = hardChoices;
    this.softChoices = softChoices;

    const playerCards = hand.map((r) => this.shoe.topPop(r));
    const d1 = this.shoe.topPop(upCard);

    if (!this.rules.ENHC) {
      if (upCard === 1) this.shoe.removeOneNot(10);
      else if (upCard === 10) this.shoe.removeOneNot(1);
    }

    this.hands.push(
      new Hand(playerCards, choice === BlackjackSimulator.DOUBLE ? 2 : 1),
    );
    this.dealer = new Dealer(d1, this.rules.S17);

    this.playSim(choice);

    return this.gain;
  }

  playSim(choice: number) {
    if (this.currentHand >= this.hands.length) {
      this.dealerHit();
      this.winLoss();
      return;
    }
    this.enactChoice(choice);
  }

  enactChoice(choice: number) {
    let numHands = this.hands.length;
    if (this.currentHand >= numHands) return;
    let hand = this.hands[this.currentHand];

    if (choice == BlackjackSimulator.HIT || choice == BlackjackSimulator.DOUBLE)
      hand.hit(this.shoe.topPop());
    if (
      choice == BlackjackSimulator.STAND ||
      choice == BlackjackSimulator.DOUBLE
    ) {
      this.currentHand++;
    }
    if (choice == BlackjackSimulator.SPLIT) {
      if (!hand.canSplit()) console.log("Cannot split hand!");
      let card1 = this.shoe.topPop();
      let card2 = this.shoe.topPop();
      let newHand = this.hands[this.currentHand].split(card1, card2);
      this.hands.push(newHand);

      if (hand.cards[0].isAce() && this.rules.drawAces === false) {
        this.currentHand += 2;
      }
    }
    if (this.hands[this.currentHand].isBust()) {
      this.currentHand++;
    }
    this.playSim(this.getNextChoice());
  }

  getNextChoice() {
    if (this.hardChoices.length === 0 || this.softChoices.length === 0) {
      this.currentHand++;
      return;
    }

    if (this.currentHand >= this.hands.length) return -1;

    const choice = this.hands[this.currentHand].isSoft()
      ? this.softChoices[this.hands[this.currentHand].total() - 12]
      : this.hardChoices[this.hands[this.currentHand].total() - 4];
    if (choice === -1) {
      this.currentHand++;
      return this.getNextChoice();
    }
    return choice;
  }

  winLoss() {
    let isNatural = this.hands[0].isBlackjack() && this.hands.length === 1;
    for (let hand of this.hands) {
      if (hand.isBust()) {
        this.gain -= hand.bet;
        return;
      }
      if (this.dealer.isBust()) {
        this.gain += hand.bet;
        return;
      }
      if (hand.total() < this.dealer.total(false)) {
        this.gain -= hand.bet;
        return;
      }
      if (hand.total() > this.dealer.total(false)) {
        if (isNatural) {
          this.gain += this.rules.BJPay;
          return;
        }
        this.gain += hand.bet;
        return;
      }
    }
  }

  dealerHit() {
    let isNatural = this.hands[0].isBlackjack() && this.hands.length === 1;
    if (this.rules.ENHC && isNatural) {
      this.dealer.hit(this.shoe.topPop());
      return;
    }
    let letDealerHit = false;
    for (let hand of this.hands) {
      if (!isNatural && !hand.isBust()) {
        letDealerHit = true;
        break;
      }
    }
    while (!this.dealer.stop() && letDealerHit)
      this.dealer.hit(this.shoe.topPop());
  }
}
