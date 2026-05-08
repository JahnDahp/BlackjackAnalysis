import { workerData, parentPort } from "worker_threads";
import { DealerSettingsObject } from "../SettingsObjects.js";
import { BlackjackSimulator } from "./BlackjackSimulator.js";

// workerData: { dealerSettings, upCard, hardHands, softHands }
// hardHands[upCard-1][handTotal-4] = [{hand, normalizedProb}]
// softHands[upCard-1][handTotal-12] = [{hand, normalizedProb}]

const {
  dealerSettings,
  upCard,
  hardHandsForUpCard,
  softHandsForUpCard,
}: {
  dealerSettings: DealerSettingsObject;
  upCard: number;
  hardHandsForUpCard: { hand: number[]; normalizedProb: number }[][];
  softHandsForUpCard: { hand: number[]; normalizedProb: number }[][];
} = workerData;

function run(
  iterations: number,
  hand: number[],
  upCard: number,
  choice: number,
  hardChoices: number[],
  softChoices: number[],
): number {
  const sim = new BlackjackSimulator(dealerSettings);
  let totalGain = 0;
  for (let i = 0; i < iterations; i++) {
    totalGain += sim.startSim(hand, upCard, choice, hardChoices, softChoices);
  }
  return totalGain / iterations;
}

function log(msg: string) {
  process.stdout.write(msg + "\n");
}

const STAND = 0;
const HIT = 1;
const DOUBLE = 2;

const hardValues: { choice: number; EVs: number[] }[] = [];
const softValues: { choice: number; EVs: number[] }[] = [];

const hardChoices: number[] = new Array(18).fill(-1);
const softChoices: number[] = new Array(10).fill(-1);

// Hard 21..11 (top half, computed first for use as future choices)
for (let handTotal = 21; handTotal >= 11; handTotal--) {
  let standEV = 0,
    hitEV = 0,
    doubleEV = 0;
  for (const comp of hardHandsForUpCard[handTotal - 4]) {
    standEV +=
      run(100000, comp.hand, upCard, STAND, hardChoices, softChoices) *
      comp.normalizedProb;
    hitEV +=
      run(100000, comp.hand, upCard, HIT, hardChoices, softChoices) *
      comp.normalizedProb;
    doubleEV +=
      run(100000, comp.hand, upCard, DOUBLE, hardChoices, softChoices) *
      comp.normalizedProb;
  }
  const maxEV = Math.max(standEV, hitEV, doubleEV);
  const choice = maxEV === standEV ? STAND : maxEV === hitEV ? HIT : DOUBLE;
  hardValues.unshift({ choice, EVs: [standEV, hitEV, doubleEV] });
  hardChoices[handTotal - 4] = choice;
  log(
    `[upCard=${upCard}] Hard ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  );
}

// Soft 21..12
for (let handTotal = 21; handTotal >= 12; handTotal--) {
  let standEV = 0,
    hitEV = 0,
    doubleEV = 0;
  for (const comp of softHandsForUpCard[handTotal - 12]) {
    standEV +=
      run(100000, comp.hand, upCard, STAND, hardChoices, softChoices) *
      comp.normalizedProb;
    hitEV +=
      run(100000, comp.hand, upCard, HIT, hardChoices, softChoices) *
      comp.normalizedProb;
    doubleEV +=
      run(100000, comp.hand, upCard, DOUBLE, hardChoices, softChoices) *
      comp.normalizedProb;
  }
  const maxEV = Math.max(standEV, hitEV, doubleEV);
  const choice = maxEV === standEV ? STAND : maxEV === hitEV ? HIT : DOUBLE;
  softValues.unshift({ choice, EVs: [standEV, hitEV, doubleEV] });
  softChoices[handTotal - 12] = choice;
  log(
    `[upCard=${upCard}] Soft ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  );
}

// Hard 10..4 (lower half)
for (let handTotal = 10; handTotal >= 4; handTotal--) {
  let standEV = 0,
    hitEV = 0,
    doubleEV = 0;
  for (const comp of hardHandsForUpCard[handTotal - 4]) {
    standEV +=
      run(100000, comp.hand, upCard, STAND, hardChoices, softChoices) *
      comp.normalizedProb;
    hitEV +=
      run(100000, comp.hand, upCard, HIT, hardChoices, softChoices) *
      comp.normalizedProb;
    doubleEV +=
      run(100000, comp.hand, upCard, DOUBLE, hardChoices, softChoices) *
      comp.normalizedProb;
  }
  const maxEV = Math.max(standEV, hitEV, doubleEV);
  const choice = maxEV === standEV ? STAND : maxEV === hitEV ? HIT : DOUBLE;
  hardValues.unshift({ choice, EVs: [standEV, hitEV, doubleEV] });
  hardChoices[handTotal - 4] = choice;
  log(
    `[upCard=${upCard}] Hard ${handTotal} vs ${upCard}: ${["S", "H", "D"][choice]}`,
  );
}

parentPort!.postMessage({ upCard, hard: hardValues, soft: softValues });
