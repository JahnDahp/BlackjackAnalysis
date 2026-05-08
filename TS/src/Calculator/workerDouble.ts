import { workerData, parentPort } from "worker_threads";
import { Calculator } from "./Calculator.js";

const { decks, S17, ENHC, baseSettings, dataDir } = workerData;
const settings = { ...baseSettings, decks, S17, ENHC };
const instance = Calculator.create(settings, dataDir);

console.log(
  `Starting double: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`,
);

const hard: any[] = [];
for (let upCard = 1; upCard <= 10; upCard++) {
  const upcardResults: any[] = [];
  for (let totalTarget = 4; totalTarget <= 21; totalTarget++) {
    const candidateHands = instance.runHandSim(
      totalTarget,
      upCard,
      false,
    ).allHands;
    for (const hand of candidateHands) {
      if (instance.total(hand.hand) === totalTarget && hand.hand.length === 2) {
        upcardResults.push([
          hand.hand,
          hand.totalProb,
          instance.calcDouble(hand.hand, upCard),
        ]);
      }
    }
  }
  hard.push(upcardResults);
}

const soft: any[] = [];
for (let upCard = 1; upCard <= 10; upCard++) {
  const upcardResults: any[] = [];
  for (let totalTarget = 12; totalTarget <= 21; totalTarget++) {
    const candidateHands = instance.runHandSim(
      totalTarget,
      upCard,
      true,
    ).allHands;
    for (const hand of candidateHands) {
      if (instance.total(hand.hand) === totalTarget && hand.hand.length === 2) {
        upcardResults.push([
          hand.hand,
          hand.totalProb,
          instance.calcDouble(hand.hand, upCard),
        ]);
      }
    }
  }
  soft.push(upcardResults);
}

console.log(`Done: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`);
parentPort!.postMessage({ decks, S17, ENHC, hard, soft });
