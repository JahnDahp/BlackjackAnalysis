import {
  CountingSettingsObject,
  GameSettingsObject,
  StrategySettingsObject,
} from "../SettingsObjects";

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
  suit: string;
  soft: boolean;

  constructor(rank: number, suit?: string) {
    this.rank = rank;
    suit ? (this.suit = suit) : (this.suit = "");
    this.soft = rank === 1;
  }

  getRank() {
    if (this.rank >= 11 && this.rank <= 13) return 10;
    if (this.soft) return 11;
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
  static readonly tagMap: Map<number, number> = new Map([
    [2, 0],
    [3, 1],
    [4, 2],
    [5, 3],
    [6, 4],
    [7, 5],
    [8, 6],
    [9, 7],
    [10, 8],
    [11, 9],
  ]);
  static readonly IRCMap: Map<number, number> = new Map([
    [1, 0],
    [2, 1],
    [4, 2],
    [6, 3],
    [8, 4],
  ]);

  shoe: Card[];
  deckNumber: number;
  countSystem: CountingSettingsObject;
  runningCount: number;

  constructor(deckNumber: number, countSystem: CountingSettingsObject) {
    const suits = ["spades", "clubs", "hearts", "diamonds"];
    this.deckNumber = deckNumber;
    this.countSystem = countSystem;
    const IRCIndex = Shoe.IRCMap.get(deckNumber) ?? 0;
    this.runningCount = countSystem.IRCs[IRCIndex];
    let shoe = [];
    for (let deck = 0; deck < deckNumber; deck++) {
      for (let s = 0; s < 4; s++) {
        for (let r = 1; r < 14; r++) {
          let card = new Card(r, suits[s]);
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

  topPop(count: boolean): Card {
    const card = this.shoe.pop();
    if (count) {
      const tagIndex = Shoe.tagMap.get(card?.getRank() ?? 2) ?? 0;
      this.runningCount += this.countSystem.tags[tagIndex];
    }
    if (!card) throw new Error("Shoe is empty");
    return card;
  }
}

export class Hand {
  cards: Card[];
  bet: number;

  constructor(one: Card, two: Card, initialBet?: number) {
    this.cards = [];
    initialBet ? (this.bet = initialBet) : (this.bet = 0);
    this.hit(one);
    this.hit(two);
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
    for (let card of this.cards) {
      if (card.soft) return true;
    }
    return false;
  }

  unSoft() {
    for (let card of this.cards) {
      if (card.soft) {
        card.soft = false;
        return;
      }
    }
  }

  isBlackjack() {
    return this.total() === 21 && this.cards.length === 2;
  }

  hit(hitCard: Card) {
    this.cards.push(hitCard);
  }

  canSplit() {
    if (this.cards.length != 2) return false;
    return this.cards[0].getRank() % 10 === this.cards[1].getRank() % 10;
  }

  split(newCard1: Card, newCard2: Card) {
    let splitCard = this.cards[1];
    this.cards.pop();
    this.hit(newCard1);
    return new Hand(splitCard, newCard2, this.bet);
  }

  isBust() {
    return this.total() > 21;
  }
}

export class Dealer {
  cards: Card[];
  S17: boolean;
  insure: boolean;

  constructor(up: Card, hole: Card, S17: boolean) {
    this.cards = [];
    this.S17 = S17;
    this.insure = true;
    this.hit(up);
    this.hit(hole);
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
    for (let card of this.cards) {
      if (card.soft) return true;
    }
    return false;
  }

  unSoft() {
    for (let card of this.cards) {
      if (card.soft) {
        card.soft = false;
        return;
      }
    }
  }

  isBlackjack() {
    return this.total(false) === 21 && this.cards.length === 2;
  }

  hit(hitCard: Card) {
    this.cards.push(hitCard);
  }

  isBust() {
    return this.total(false) > 21;
  }

  canInsure() {
    return this.cards[0].isAce() && this.insure;
  }

  stop() {
    if (this.total(false) > 17) return true;
    if (this.total(false) < 17) return false;
    if (this.isSoft()) return this.S17;
    return true;
  }
}

export class BlackjackGame {
  static readonly tagMap: Map<number, number> = new Map([
    [2, 0],
    [3, 1],
    [4, 2],
    [5, 3],
    [6, 4],
    [7, 5],
    [8, 6],
    [9, 7],
    [10, 8],
    [11, 9],
  ]);

  static readonly NONE = -1;
  static readonly HIT = 0;
  static readonly STAND = 1;
  static readonly DOUBLE = 2;
  static readonly SPLIT = 3;
  static readonly SURRENDER = 4;
  static readonly INSURANCE = 5;
  static readonly NO_INSURANCE = 6;
  static readonly PLAY_GAME = 7;
  static readonly DECK_SIZE = 52;
  static readonly EMPTY = -100;

  rules: GameSettingsObject;
  shoe: Shoe;
  discard: Card;
  hands: Hand[];
  currentHand: number;
  dealer: Dealer;
  choice: number;
  bankroll: number;
  initialBet: number;
  surrendered: boolean;
  insured: boolean;
  handOver: boolean;
  showHit: boolean;
  showStand: boolean;
  showDouble: boolean;
  showSplit: boolean;
  showSurrender: boolean;
  showInsurance: boolean;
  showHole: boolean;
  nextShuffle: boolean;
  lastGain: string;
  strategy: StrategySettingsObject;
  countSystem: CountingSettingsObject;
  holeTag: number;

  constructor(
    rules: GameSettingsObject,
    strategy: StrategySettingsObject,
    countSystem: CountingSettingsObject,
    bankroll: number,
  ) {
    let temp = new Card(0, "spades");
    this.strategy = strategy;
    this.countSystem = countSystem;
    this.holeTag = 0;
    this.rules = rules;
    this.initialBet = 0;
    this.bankroll = bankroll;
    this.dealer = new Dealer(temp, temp, rules.S17);
    this.hands = [];
    this.choice = BlackjackGame.NONE;
    this.currentHand = 0;
    this.surrendered = false;
    this.insured = false;
    this.shoe = new Shoe(rules.decks, countSystem);
    this.discard = this.shoe.topPop(false);
    this.handOver = true;
    this.showHit = false;
    this.showStand = false;
    this.showDouble = false;
    this.showSplit = false;
    this.showSurrender = false;
    this.showInsurance = false;
    this.showHole = false;
    this.nextShuffle = false;
    this.lastGain = "";
  }

  startHand() {
    this.bankroll -= this.initialBet;
    if (this.nextShuffle) {
      this.shoe = new Shoe(this.rules.decks, this.countSystem);
      this.discard = this.shoe.topPop(false);
      this.nextShuffle = false;
    }
    let p1 = this.shoe.topPop(true);
    let d1 = this.shoe.topPop(true);
    let p2 = this.shoe.topPop(true);
    let d2 = this.shoe.topPop(false);

    const tagIndex = Shoe.tagMap.get(d2?.getRank() ?? 2) ?? 0;
    this.holeTag = this.countSystem.tags[tagIndex];

    this.hands.length = 0;
    this.hands.push(new Hand(p1, p2, this.initialBet));
    this.dealer = new Dealer(d1, d2, this.rules.S17);
    this.choice = BlackjackGame.NONE;
    this.currentHand = 0;
    this.handOver = false;
    this.showHole = false;
  }

  playGame() {
    if (this.handOver && this.choice != BlackjackGame.PLAY_GAME) return;
    if (this.choice == BlackjackGame.PLAY_GAME) this.startHand();
    this.showButtons();
    this.getChoice();
    if (this.dealer.canInsure()) return;
    if (this.dealer.total(false) === 21) {
      this.endHand();
      return;
    }
    while (this.currentHand < this.hands.length) {
      const hand = this.hands[this.currentHand];
      const isAutoSkippedSplitAce =
        hand.cards.length === 2 &&
        hand.cards[0].isAce() &&
        this.rules.drawAces === false &&
        this.hands.length > 1 &&
        !(
          this.rules.RSA &&
          hand.cards[1].isAce() &&
          this.hands.length <= this.rules.splits &&
          this.bankroll - hand.bet >= 0
        );
      const shouldSkip = hand.isBust() || isAutoSkippedSplitAce;
      if (shouldSkip) this.currentHand++;
      else break;
    }
    if (this.currentHand >= this.hands.length) {
      this.endHand();
      return;
    }
    this.showButtons();
  }

  endHand() {
    this.showHit = false;
    this.showStand = false;
    this.showDouble = false;
    this.showSplit = false;
    this.showSurrender = false;
    this.showInsurance = false;
    this.showHole = true;
    this.shoe.runningCount += this.holeTag;
    this.handOver = true;
    let isNatural = this.hands[0].isBlackjack() && this.hands.length === 1;
    if (!this.initialWinLoss(isNatural)) {
      this.dealerHit(isNatural);
      this.winLoss();
    }
    if (this.initialBet > this.bankroll)
      this.initialBet = this.bankroll - (this.bankroll % 5);
    if (this.shoe.size() < this.rules.pen) this.nextShuffle = true;
  }

  showButtons() {
    this.showHit = false;
    this.showStand = false;
    this.showDouble = false;
    this.showSplit = false;
    this.showSurrender = false;
    this.showInsurance = false;
    let numHands = this.hands.length;
    if (this.currentHand >= numHands) return;
    let hand = this.hands[this.currentHand];
    if (this.dealer.canInsure()) {
      this.showInsurance = true;
      return;
    }
    this.showHit = true;
    this.showStand = true;
    if (hand.cards.length !== 2) return;
    if (this.rules.doubles.includes(hand.total())) this.showDouble = true;
    if ((!this.rules.DAS && numHands > 1) || this.bankroll - hand.bet < 0)
      this.showDouble = false;
    if (hand.canSplit() && numHands <= this.rules.splits) this.showSplit = true;
    if (hand.cards[0].isAce() && numHands > 1 && !this.rules.drawAces) {
      this.showHit = false;
      this.showDouble = false;
    }
    if (
      (!this.rules.RSA && hand.cards[1].isAce() && numHands > 1) ||
      this.bankroll - hand.bet < 0
    )
      this.showSplit = false;
    if (this.rules.LS === "Yes" && numHands == 1) this.showSurrender = true;
  }

  getChoice() {
    let numHands = this.hands.length;
    if (this.currentHand >= numHands) return;
    let hand = this.hands[this.currentHand];
    if (this.choice == BlackjackGame.INSURANCE) {
      this.bankroll -= hand.bet * 0.5;
      this.insured = true;
    }
    if (
      this.choice == BlackjackGame.INSURANCE ||
      this.choice == BlackjackGame.NO_INSURANCE
    ) {
      this.dealer.insure = false;
      this.showInsurance = false;
      this.choice = BlackjackGame.NONE;
      return;
    }
    if (
      hand.cards.length === 2 &&
      hand.cards[0].isAce() &&
      this.rules.drawAces === false &&
      this.choice === BlackjackGame.NONE &&
      numHands > 1
    ) {
      const canResplitAces =
        this.rules.RSA &&
        hand.cards[1].isAce() &&
        numHands <= this.rules.splits &&
        this.bankroll - hand.bet >= 0;

      if (!canResplitAces) {
        this.currentHand++;
      }
    }
    if (this.choice == BlackjackGame.HIT || this.choice == BlackjackGame.DOUBLE)
      hand.hit(this.shoe.topPop(true));
    if (this.choice == BlackjackGame.DOUBLE) {
      this.bankroll -= hand.bet;
      hand.bet = hand.bet * 2;
    }
    if (
      this.choice == BlackjackGame.STAND ||
      this.choice == BlackjackGame.DOUBLE ||
      this.choice == BlackjackGame.SURRENDER
    )
      this.currentHand++;
    if (this.choice == BlackjackGame.SURRENDER) this.surrendered = true;
    if (this.choice == BlackjackGame.SPLIT) {
      let card1 = this.shoe.topPop(true);
      let card2 = this.shoe.topPop(true);
      let newHand = this.hands[this.currentHand].split(card1, card2);
      this.hands.push(newHand);
      this.bankroll -= this.hands[this.currentHand].bet;
    }
    this.choice = BlackjackGame.NONE;

    if (
      hand.cards.length === 2 &&
      hand.cards[0].isAce() &&
      this.rules.drawAces === false &&
      this.hands.length > 1
    ) {
      const canResplitAces =
        this.rules.RSA &&
        hand.cards[1].isAce() &&
        this.hands.length <= this.rules.splits &&
        this.bankroll - hand.bet >= 0;

      if (!canResplitAces) {
        this.currentHand++;
      }
    }
  }

  winLoss() {
    let gain = 0;
    for (let i = 0; i < this.hands.length; i++) {
      let hand = this.hands[i];
      if (hand.isBust()) {
        gain -= hand.bet;
        continue;
      }
      if (this.dealer.isBust()) {
        this.bankroll += hand.bet * 2.0;
        gain += hand.bet;
        continue;
      }
      if (hand.total() < this.dealer.total(false)) {
        gain -= hand.bet;
        continue;
      }
      if (hand.total() > this.dealer.total(false)) {
        this.bankroll += hand.bet * 2.0;
        gain += hand.bet;
        continue;
      }
      if (hand.total() == this.dealer.total(false)) this.bankroll += hand.bet;
    }
    if (this.insured) {
      gain -= this.hands[0].bet * 0.5;
      this.insured = false;
    }
    gain >= 0 ? (this.lastGain = `+${gain}`) : (this.lastGain = String(gain));
  }

  initialWinLoss(isNatural: boolean) {
    let gain = 0;
    if (this.dealer.isBlackjack() && this.insured) {
      this.bankroll += this.hands[0].bet * 1.5;

      if (isNatural) {
        this.bankroll += this.hands[0].bet;
        gain += this.hands[0].bet;
      }
      this.insured = false;
      gain >= 0 ? (this.lastGain = `+${gain}`) : (this.lastGain = String(gain));
      return true;
    }
    if (isNatural && !this.dealer.isBlackjack()) {
      this.bankroll += this.hands[0].bet + this.hands[0].bet * this.rules.BJPay;
      if (this.insured) {
        this.insured = false;
        gain += this.hands[0].bet;
      } else gain += this.hands[0].bet * this.rules.BJPay;
      gain >= 0 ? (this.lastGain = `+${gain}`) : (this.lastGain = String(gain));
      return true;
    }
    if (this.surrendered) {
      this.bankroll += this.hands[0].bet * 0.5;
      this.surrendered = false;
      gain -= this.hands[0].bet * 0.5;
      gain >= 0 ? (this.lastGain = `+${gain}`) : (this.lastGain = String(gain));
      return true;
    }
    return false;
  }

  dealerHit(isNatural: boolean) {
    let letDealerHit = false;
    for (let hand of this.hands) {
      if (
        !isNatural &&
        !hand.isBust() &&
        this.choice != BlackjackGame.SURRENDER
      ) {
        letDealerHit = true;
        break;
      }
    }
    while (!this.dealer.stop() && letDealerHit)
      this.dealer.hit(this.shoe.topPop(true));
  }

  getRunningCount() {
    return this.shoe.runningCount;
  }

  getCorrectChoice() {
    if (this.handOver || this.currentHand >= this.hands.length) return -1;

    const hardMap: Map<number, number> = new Map([
      [21, 0],
      [20, 1],
      [19, 2],
      [18, 3],
      [17, 4],
      [16, 5],
      [15, 6],
      [14, 7],
      [13, 8],
      [12, 9],
      [11, 10],
      [10, 11],
      [9, 12],
      [8, 13],
      [7, 14],
      [6, 15],
      [5, 16],
      [4, 17],
    ]);
    const surrenderPairMap: Map<number, number> = new Map([
      [1, 18],
      [11, 18],
      [10, 19],
      [9, 20],
      [8, 21],
      [7, 22],
      [6, 23],
      [5, 24],
      [4, 25],
      [3, 26],
      [2, 27],
    ]);
    const pairMap: Map<number, number> = new Map([
      [1, 0],
      [11, 0],
      [10, 1],
      [9, 2],
      [8, 3],
      [7, 4],
      [6, 5],
      [5, 6],
      [4, 7],
      [3, 8],
      [2, 9],
    ]);
    const softMap: Map<number, number> = new Map([
      [21, 0],
      [20, 1],
      [19, 2],
      [18, 3],
      [17, 4],
      [16, 5],
      [15, 6],
      [14, 7],
      [13, 8],
      [12, 9],
    ]);

    const dealerIndex = this.dealer.total(true) - 2;
    const handTotal = this.hands[this.currentHand].total();
    const pairValue = this.hands[this.currentHand].cards[0].getRank();
    const isSoft = this.hands[this.currentHand].isSoft();

    if (this.showSurrender && !isSoft) {
      if (this.showSplit) {
        const pairSurrenderIndex = surrenderPairMap.get(pairValue);
        if (
          pairSurrenderIndex != undefined &&
          this.strategy.surrenderMatrix[pairSurrenderIndex][dealerIndex] == 1
        ) {
          return BlackjackGame.SURRENDER;
        }
      } else {
        const surrenderIndex = hardMap.get(handTotal);
        if (
          surrenderIndex != undefined &&
          this.strategy.surrenderMatrix[surrenderIndex][dealerIndex] == 1
        ) {
          return BlackjackGame.SURRENDER;
        }
      }
    }

    if (this.showSplit) {
      const pairIndex = pairMap.get(pairValue);
      if (
        pairIndex != undefined &&
        (this.strategy.splitMatrix[pairIndex][dealerIndex] == 1 ||
          (this.strategy.splitMatrix[pairIndex][dealerIndex] == 2 &&
            this.rules.DAS))
      ) {
        return BlackjackGame.SPLIT;
      }
    }

    if (isSoft) {
      const softIndex = softMap.get(handTotal);
      if (
        softIndex != undefined &&
        this.showDouble &&
        (this.strategy.softMatrix[softIndex][dealerIndex] == 2 ||
          this.strategy.softMatrix[softIndex][dealerIndex] == 3)
      ) {
        return BlackjackGame.DOUBLE;
      }
      if (
        softIndex != undefined &&
        this.showHit &&
        (this.strategy.softMatrix[softIndex][dealerIndex] == 2 ||
          this.strategy.softMatrix[softIndex][dealerIndex] == 1)
      ) {
        return BlackjackGame.HIT;
      }
      return BlackjackGame.STAND;
    }

    const hardIndex = hardMap.get(handTotal);
    if (
      hardIndex != undefined &&
      this.showDouble &&
      this.strategy.hardMatrix[hardIndex][dealerIndex] == 2
    ) {
      return BlackjackGame.DOUBLE;
    }
    if (
      hardIndex != undefined &&
      this.showHit &&
      (this.strategy.hardMatrix[hardIndex][dealerIndex] == 2 ||
        this.strategy.hardMatrix[hardIndex][dealerIndex] == 1)
    ) {
      return BlackjackGame.HIT;
    }
    return BlackjackGame.STAND;
  }

  getCorrectDeviation(trueCount?: number) {
    if (this.handOver || this.currentHand >= this.hands.length) return -1;

    const count = trueCount ?? this.getRunningCount();

    const hardHitStandMap: Map<number, number> = new Map([
      [21, 0],
      [20, 1],
      [19, 2],
      [18, 3],
      [17, 4],
      [16, 5],
      [15, 6],
      [14, 7],
      [13, 8],
      [12, 9],
    ]);
    const softHitStandMap: Map<number, number> = new Map([
      [21, 10],
      [20, 11],
      [19, 12],
      [18, 13],
      [17, 14],
      [16, 15],
      [15, 16],
      [14, 17],
      [13, 18],
      [12, 19],
    ]);
    const hardDoubleMap: Map<number, number> = new Map([
      [11, 0],
      [10, 1],
      [9, 2],
      [8, 3],
      [7, 4],
      [6, 5],
      [5, 6],
      [4, 7],
    ]);
    const softDoubleMap: Map<number, number> = new Map([
      [21, 8],
      [20, 9],
      [19, 10],
      [18, 11],
      [17, 12],
      [16, 13],
      [15, 14],
      [14, 15],
      [13, 16],
      [12, 17],
    ]);
    const surrenderMap: Map<number, number> = new Map([
      [21, 0],
      [20, 1],
      [19, 2],
      [18, 3],
      [17, 4],
      [16, 5],
      [15, 6],
      [14, 7],
      [13, 8],
      [12, 9],
      [11, 10],
      [10, 11],
      [9, 12],
      [8, 13],
      [7, 14],
      [6, 15],
      [5, 16],
      [4, 17],
    ]);
    const surrenderPairMap: Map<number, number> = new Map([
      [1, 18],
      [11, 18],
      [10, 19],
      [9, 20],
      [8, 21],
      [7, 22],
      [6, 23],
      [5, 24],
      [4, 25],
      [3, 26],
      [2, 27],
    ]);
    const pairMap: Map<number, number> = new Map([
      [1, 0],
      [11, 0],
      [10, 1],
      [9, 2],
      [8, 3],
      [7, 4],
      [6, 5],
      [5, 6],
      [4, 7],
      [3, 8],
      [2, 9],
    ]);

    const dealerIndex = this.dealer.total(true) - 2;
    const handTotal = this.hands[this.currentHand].total();
    const pairValue = this.hands[this.currentHand].cards[0].getRank();
    const isSoft = this.hands[this.currentHand].isSoft();

    if (this.showSurrender && !isSoft) {
      if (this.showSplit) {
        const pairSurrenderIndex = surrenderPairMap.get(pairValue);
        if (pairSurrenderIndex == undefined) throw Error("Invalid Index");
        let deviation =
          this.countSystem.surrenderMatrix[pairSurrenderIndex][dealerIndex];
        if (deviation != BlackjackGame.EMPTY && count >= deviation) {
          return BlackjackGame.SURRENDER;
        }
      } else {
        const surrenderIndex = surrenderMap.get(handTotal);
        if (surrenderIndex == undefined) throw Error("Invalid Index");
        let deviation =
          this.countSystem.surrenderMatrix[surrenderIndex][dealerIndex];
        if (deviation != BlackjackGame.EMPTY && count >= deviation) {
          return BlackjackGame.SURRENDER;
        }
      }
    }

    if (this.showSplit) {
      const pairIndex = pairMap.get(pairValue);
      if (pairIndex == undefined) throw Error("Invalid Index");
      let deviation = this.countSystem.splitMatrix[pairIndex][dealerIndex];
      console.log(`Dev: ${deviation}`);
      console.log(`Count: ${count}`);
      if (deviation != BlackjackGame.EMPTY && count >= deviation) {
        return BlackjackGame.SPLIT;
      }
    }

    if (isSoft || handTotal < 12) {
      if (isSoft) {
        const softDoubleIndex = softDoubleMap.get(handTotal);
        if (softDoubleIndex == undefined) throw Error("Invalid Index");
        let deviation =
          this.countSystem.doubleMatrix[softDoubleIndex][dealerIndex];
        if (deviation != BlackjackGame.EMPTY && count >= deviation) {
          return BlackjackGame.DOUBLE;
        }
      } else {
        const hardDoubleIndex = hardDoubleMap.get(handTotal);
        if (hardDoubleIndex == undefined) throw Error("Invalid Index");
        let deviation =
          this.countSystem.doubleMatrix[hardDoubleIndex][dealerIndex];
        if (deviation != BlackjackGame.EMPTY && count >= deviation) {
          return BlackjackGame.DOUBLE;
        }
      }
      return BlackjackGame.EMPTY;
    }

    if (isSoft) {
      const softHitStandIndex = softHitStandMap.get(handTotal);
      if (softHitStandIndex == undefined) throw Error("Invalid Index");
      let deviation =
        this.countSystem.hitStandMatrix[softHitStandIndex][dealerIndex];
      if (deviation != BlackjackGame.EMPTY && count >= deviation) {
        return BlackjackGame.STAND;
      }
    } else {
      const hardHitStandIndex = hardHitStandMap.get(handTotal);
      if (hardHitStandIndex == undefined) throw Error("Invalid Index");
      let deviation =
        this.countSystem.hitStandMatrix[hardHitStandIndex][dealerIndex];
      console.log(deviation);
      if (deviation != BlackjackGame.EMPTY && count >= deviation) {
        return BlackjackGame.STAND;
      }
    }
    return BlackjackGame.EMPTY;
  }
}
