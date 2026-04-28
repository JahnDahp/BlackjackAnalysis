import { Worker } from "worker_threads";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";
import { DealerSettingsObject } from "../SettingsObjects.js";
import { BlackjackSimulator } from "./BlackjackSimulator.js";

export class Simulator {
  static readonly STAND = 0;
  static readonly HIT = 1;
  static readonly DOUBLE = 2;

  dealerSettings: DealerSettingsObject;
  hardHands: { hand: number[]; normalizedProb: number }[][][];
  softHands: { hand: number[]; normalizedProb: number }[][][];

  protected constructor(dealerSettings: DealerSettingsObject) {
    this.dealerSettings = dealerSettings;
    this.hardHands = this.getOnlyTopCompositions(false);
    this.softHands = this.getOnlyTopCompositions(true);
  }

  static async create(dealerSettings: any): Promise<Simulator> {
    const instance = new Simulator(dealerSettings);
    return instance;
  }

  run(
    iterations: number,
    hand: number[],
    upCard: number,
    choice: number,
    hardChoices: number[],
    softChoices: number[],
  ) {
    let sim = new BlackjackSimulator(this.dealerSettings);
    let totalGain = 0;
    for (let i = 0; i < iterations; i++) {
      const gain = sim.startSim(hand, upCard, choice, hardChoices, softChoices);
      totalGain += gain;
    }
    return totalGain / iterations;
  }

  ///
  /// OLD
  ///

  // calcHSD() {
  //   let strategyTable = [];

  //   const hardHands = this.getOnlyTopCompositions(false);
  //   const softHands = this.getOnlyTopCompositions(true);

  //   for (let upCard = 1; upCard <= 10; upCard++) {
  //     let hardValues = [];
  //     let softValues = [];
  //     let hardChoices = [
  //       -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
  //     ];
  //     let softChoices = [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1];

  //     for (let handTotal = 21; handTotal >= 11; handTotal--) {
  //       let standEV = 0;
  //       let hitEV = 0;
  //       let doubleEV = 0;
  //       for (let composition of hardHands[upCard - 1][handTotal - 4]) {
  //         standEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.STAND,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         hitEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.HIT,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         doubleEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.DOUBLE,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //       }
  //       const maxEV = Math.max(standEV, hitEV, doubleEV);
  //       const choice =
  //         maxEV === standEV
  //           ? Simulator.STAND
  //           : maxEV === hitEV
  //             ? Simulator.HIT
  //             : Simulator.DOUBLE;
  //       hardValues.unshift({
  //         choice: choice,
  //         EVs: [standEV, hitEV, doubleEV],
  //       });
  //       hardChoices[handTotal - 4] = choice;
  //       console.log(
  //         `Hard ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  //       );
  //     }

  //     for (let handTotal = 21; handTotal >= 12; handTotal--) {
  //       let standEV = 0;
  //       let hitEV = 0;
  //       let doubleEV = 0;
  //       for (let composition of softHands[upCard - 1][handTotal - 12]) {
  //         standEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.STAND,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         hitEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.HIT,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         doubleEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.DOUBLE,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //       }
  //       const maxEV = Math.max(standEV, hitEV, doubleEV);
  //       const choice =
  //         maxEV === standEV
  //           ? Simulator.STAND
  //           : maxEV === hitEV
  //             ? Simulator.HIT
  //             : Simulator.DOUBLE;
  //       softValues.unshift({
  //         choice: choice,
  //         EVs: [standEV, hitEV, doubleEV],
  //       });
  //       softChoices[handTotal - 12] = choice;
  //       console.log(
  //         `Soft ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  //       );
  //     }

  //     for (let handTotal = 10; handTotal >= 4; handTotal--) {
  //       let standEV = 0;
  //       let hitEV = 0;
  //       let doubleEV = 0;
  //       for (let composition of hardHands[upCard - 1][handTotal - 4]) {
  //         standEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.STAND,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         hitEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.HIT,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //         doubleEV +=
  //           this.run(
  //             100000,
  //             composition.hand,
  //             upCard,
  //             Simulator.DOUBLE,
  //             hardChoices,
  //             softChoices,
  //           ) * composition.normalizedProb;
  //       }
  //       const maxEV = Math.max(standEV, hitEV, doubleEV);
  //       const choice =
  //         maxEV === standEV
  //           ? Simulator.STAND
  //           : maxEV === hitEV
  //             ? Simulator.HIT
  //             : Simulator.DOUBLE;
  //       hardValues.unshift({
  //         choice: choice,
  //         EVs: [standEV, hitEV, doubleEV],
  //       });
  //       hardChoices[handTotal - 4] = choice;
  //       console.log(
  //         `Hard ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  //       );
  //     }
  //     strategyTable.push({ hard: hardValues, soft: softValues });
  //   }

  //   const hardTotals = Array.from({ length: 18 }, (_, i) => i + 4);
  //   const softTotals = Array.from({ length: 10 }, (_, i) => i + 12);
  //   const upCardOrder = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1]; // indices into strategyTable: upCard N is at index N-1

  //   const pad = (s: string, n: number) => s.padStart(n);

  //   console.log("Hard choices:");
  //   console.log("     " + upCardOrder.map((u) => pad(String(u), 3)).join(""));
  //   hardTotals.forEach((total, totalIdx) => {
  //     const row = upCardOrder
  //       .map((u) =>
  //         pad(["S", "H", "D"][strategyTable[u - 1].hard[totalIdx].choice], 3),
  //       )
  //       .join("");
  //     console.log(pad(String(total), 4) + " " + row);
  //   });

  //   console.log("Soft choices:");
  //   console.log("     " + upCardOrder.map((u) => pad(String(u), 3)).join(""));
  //   softTotals.forEach((total, totalIdx) => {
  //     const row = upCardOrder
  //       .map((u) =>
  //         pad(["S", "H", "D"][strategyTable[u - 1].soft[totalIdx].choice], 3),
  //       )
  //       .join("");
  //     console.log(pad(String(total), 4) + " " + row);
  //   });

  //   return strategyTable;
  // }

  calcError(iterations: number) {
    let sim = new BlackjackSimulator(this.dealerSettings);

    const actualStand = 0.453917;
    const actualDouble = -1.700555;

    for (let k = 0; k < 4; k++) {
      let standError = 0;
      let hitError = 0;
      let doubleError = 0;

      for (let j = 0; j < 10; j++) {
        let totalGain = 0;
        for (let i = 0; i < iterations * 10 ** k; i++) {
          const gain = sim.startSim([10, 10], 10, Simulator.STAND, [], []);
          totalGain += gain;
        }
        const EV = totalGain / (iterations * 10 ** k);
        standError += Math.abs(EV - actualStand);
      }
      for (let j = 0; j < 10; j++) {
        let totalGain = 0;
        for (let i = 0; i < iterations * 10 ** k; i++) {
          const gain = sim.startSim([10, 10], 10, Simulator.DOUBLE, [], []);
          totalGain += gain;
        }
        const EV = totalGain / (iterations * 10 ** k);
        doubleError += Math.abs(EV - actualDouble);
      }

      standError /= 10;
      hitError /= 10;
      doubleError /= 10;

      console.log(
        "Iterations:",
        iterations * 10 ** k,
        "standError:",
        standError,
        "hitError:",
        hitError,
        "doubleError:",
        doubleError,
      );
    }
  }

  runHandSim(totalTarget: number, upCard: number, softHands: boolean) {
    const allHands: any[] = [];
    let nextCardProbs = Array(10).fill(0);
    const seenCombos = new Set<string>();

    const totalCards = this.dealerSettings.decks * 52;
    const rankCounts: number[] = Array(11).fill(0);
    for (let r = 1; r <= 10; r++) {
      rankCounts[r] =
        r === 10
          ? this.dealerSettings.decks * 16
          : this.dealerSettings.decks * 4;
    }

    for (let playerRank = 1; playerRank <= 10; playerRank++) {
      const playerCount = rankCounts[playerRank];
      if (playerCount === 0) continue;
      const probPlayer = playerCount / totalCards;

      const countsAfterPlayer = [...rankCounts];
      countsAfterPlayer[playerRank]--;
      const totalAfterPlayer = totalCards - 1;

      const upCardCount = countsAfterPlayer[upCard];
      if (upCardCount === 0) continue;
      const probUpCard = upCardCount / totalAfterPlayer;

      const countsAfterDealer = [...countsAfterPlayer];
      countsAfterDealer[upCard]--;
      const totalAfterDealer = totalAfterPlayer - 1;

      const recurse = (
        hand: number[],
        counts: number[],
        remaining: number,
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
            const key = [...hand].sort((a, b) => a - b).join(",");
            if (!seenCombos.has(key)) {
              seenCombos.add(key);
              allHands.push({ hand, totalProb });
              const weight = totalProb;
              for (let nextRank = 1; nextRank <= 10; nextRank++) {
                if (counts[nextRank] === 0) continue;
                const prob = counts[nextRank] / remaining;
                nextCardProbs[nextRank - 1] += prob * weight;
              }
            }
          }
          return;
        }

        for (let rank = minRank; rank <= 10; rank++) {
          if (counts[rank] === 0) continue;
          const prob = counts[rank] / remaining;
          const newCounts = [...counts];
          newCounts[rank]--;
          recurse(
            [...hand, rank],
            newCounts,
            remaining - 1,
            [...handProbs, prob],
            rank,
          );
        }
      };

      recurse(
        [playerRank],
        countsAfterDealer,
        totalAfterDealer,
        [probPlayer * probUpCard],
        1,
      );
    }

    const total = nextCardProbs.reduce((a, b) => a + b, 0);
    if (total > 0) {
      nextCardProbs = nextCardProbs.map((p) => p / total);
    }

    return { allHands, nextCardProbs };
  }

  async calcHSD() {
    // Pre-serialize hand compositions for all upcards so workers get plain data
    const hardHandsAll = this.hardHands; // [upCard-1][handTotal-4]
    const softHandsAll = this.softHands; // [upCard-1][handTotal-12]

    // Resolve the worker script path (works for both ts-node and compiled JS)
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    const workerScript = resolve(__dirname, "SimWorker.ts");

    // Spawn one worker per upcard (1..10), collect promises
    const workerPromises: Promise<{
      upCard: number;
      hard: any[];
      soft: any[];
    }>[] = Array.from({ length: 10 }, (_, i) => {
      const upCard = i + 1;
      return new Promise((resolve, reject) => {
        const worker = new Worker(
          `
          import { createRequire } from 'module';
          const require = createRequire(import.meta.url);
          require('tsx/cjs');
          require(${JSON.stringify(workerScript)});
          `,
          {
            eval: true,
            workerData: {
              dealerSettings: this.dealerSettings,
              upCard,
              hardHandsForUpCard: hardHandsAll[i],
              softHandsForUpCard: softHandsAll[i],
            },
          },
        );
        worker.on("message", resolve);
        worker.on("error", reject);
        worker.on("exit", (code) => {
          if (code !== 0)
            reject(
              new Error(`Worker for upCard=${upCard} exited with code ${code}`),
            );
        });
      });
    });

    console.log("Spawned 10 workers — computing all upcards in parallel...\n");
    const results = await Promise.all(workerPromises);

    // Build strategyTable indexed by upCard (1-based), preserving original structure
    const strategyTable: { hard: any[]; soft: any[] }[] = new Array(11);
    for (const { upCard, hard, soft } of results) {
      strategyTable[upCard] = { hard, soft };
    }

    // Log in canonical order: 2,3,4,5,6,7,8,9,10,A(1)
    const hardTotals = Array.from({ length: 18 }, (_, i) => i + 4);
    const softTotals = Array.from({ length: 10 }, (_, i) => i + 12);
    const upCardOrder = [2, 3, 4, 5, 6, 7, 8, 9, 10, 1];

    const pad = (s: string, n: number) => s.padStart(n);

    console.log("Hard choices:");
    console.log("     " + upCardOrder.map((u) => pad(String(u), 3)).join(""));
    hardTotals.forEach((total, totalIdx) => {
      const row = upCardOrder
        .map((u) =>
          pad(["S", "H", "D"][strategyTable[u].hard[totalIdx].choice], 3),
        )
        .join("");
      console.log(pad(String(total), 4) + " " + row);
    });

    console.log("\nSoft choices:");
    console.log("     " + upCardOrder.map((u) => pad(String(u), 3)).join(""));
    softTotals.forEach((total, totalIdx) => {
      const row = upCardOrder
        .map((u) =>
          pad(["S", "H", "D"][strategyTable[u].soft[totalIdx].choice], 3),
        )
        .join("");
      console.log(pad(String(total), 4) + " " + row);
    });

    // Return in original format (array indexed 0..9 = upCard 1..10)
    return Array.from({ length: 10 }, (_, i) => strategyTable[i + 1]);
  }

  orderMostProbableHands(
    totalTarget: number,
    upCard: number,
    soft: boolean,
  ): { hand: number[]; normalizedProb: number }[] {
    const { allHands } = this.runHandSim(totalTarget, upCard, soft);

    if (allHands.length === 0) return [];

    const totalProb = allHands.reduce((sum, h) => sum + h.totalProb, 0);

    return allHands
      .map(({ hand, totalProb: rawProb }) => ({
        hand,
        normalizedProb: totalProb === 0 ? 0 : rawProb / totalProb,
      }))
      .sort((a, b) => b.normalizedProb - a.normalizedProb);
  }

  getMaxCompositionsForThreshold(threshold: number, soft: boolean): number[][] {
    const totals = soft
      ? Array.from({ length: 10 }, (_, i) => i + 12)
      : Array.from({ length: 18 }, (_, i) => i + 4);
    const upCards = Array.from({ length: 10 }, (_, i) => i + 1);

    return upCards.map((upCard) =>
      totals.map((total) => {
        const compositions = this.orderMostProbableHands(total, upCard, soft);

        let cumulative = 0;
        const n =
          compositions.findIndex(({ normalizedProb }) => {
            cumulative += normalizedProb;
            return cumulative >= threshold;
          }) + 1;

        return n === 0 ? compositions.length : n;
      }),
    );
  }

  getOnlyTopCompositions(
    soft: boolean,
  ): { hand: number[]; normalizedProb: number }[][][] {
    const totals = soft
      ? Array.from({ length: 10 }, (_, i) => i + 12)
      : Array.from({ length: 18 }, (_, i) => i + 4);
    const upCards = Array.from({ length: 10 }, (_, i) => i + 1);

    const hardComps = this.getMaxCompositionsForThreshold(0.95, false);
    const softComps = this.getMaxCompositionsForThreshold(0.95, true);

    return upCards.map((upCard, upCardIdx) =>
      totals.map((total, totalIdx) => {
        const n = soft
          ? softComps[upCardIdx][totalIdx]
          : hardComps[upCardIdx][totalIdx];
        const compositions = this.orderMostProbableHands(total, upCard, soft);
        const sliced = compositions.slice(0, n);
        const sliceTotal = sliced.reduce((sum, c) => sum + c.normalizedProb, 0);
        return sliced.map((c) => ({
          hand: c.hand,
          normalizedProb: c.normalizedProb / sliceTotal,
        }));
      }),
    );
  }

  genShoe() {
    let shoe = [];
    for (let deck = 0; deck < this.dealerSettings.decks; deck++) {
      for (let s = 1; s <= 4; s++) {
        for (let r = 1; r <= 13; r++) {
          const rank = r >= 11 && r <= 13 ? 10 : r;
          const card = rank;
          shoe.push(card);
        }
      }
    }
    return this.shuffle(shoe);
  }

  removeCardsFromShoe(shoe: number[], cards: number[], prob?: number) {
    for (let card of cards) {
      const count = shoe.filter((c) => c === card).length;
      if (count === 0) throw new Error(`No ${card} card found in shoe!`);
      if (prob) prob *= count / shoe.length;
      const index = shoe.findIndex((c) => c === card);
      shoe.splice(index, 1);
    }
    return prob;
  }

  isSoft(cards: number[]) {
    let total = 0;
    let numAces = 0;

    for (const card of cards) {
      total += card === 1 ? 11 : card;
      if (card === 1) numAces++;
    }

    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }

    return numAces > 0;
  }

  total(cards: number[]) {
    let total = 0;
    let numAces = 0;

    for (let card of cards) {
      if (card === 1) {
        total += 11;
        numAces++;
      } else {
        total += card;
      }
    }

    while (total > 21 && numAces > 0) {
      total -= 10;
      numAces--;
    }

    return total;
  }

  shuffle(array: number[]): number[] {
    const result = [...array];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }
}
