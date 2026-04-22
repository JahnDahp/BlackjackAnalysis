import { workerData, parentPort } from "worker_threads";
import { CalculatorLogic } from "./CalculatorLogicDownload.js";

const { decks, S17, ENHC, baseSettings, dataDir } = workerData;
const settings = { ...baseSettings, decks, S17, ENHC };
const instance = CalculatorLogic.create(settings, dataDir);

console.log(
  `Starting hit: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`,
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
      if (instance.total(hand.hand) === totalTarget) {
        upcardResults.push([
          hand.hand,
          hand.totalProb,
          instance.calcHit(hand.hand, upCard),
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
      if (instance.total(hand.hand) === totalTarget) {
        upcardResults.push([
          hand.hand,
          hand.totalProb,
          instance.calcHit(hand.hand, upCard),
        ]);
      }
    }
  }
  soft.push(upcardResults);
}

console.log(`Done: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`);
parentPort!.postMessage({ decks, S17, ENHC, hard, soft });
