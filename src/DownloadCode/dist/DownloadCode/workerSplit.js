import { workerData, parentPort } from "worker_threads";
import { CalculatorLogic } from "./CalculatorLogicDownload.js";
process.on("uncaughtException", (err) => {
    parentPort.postMessage({
        type: "log",
        msg: `WORKER CRASH: ${err.message}\n${err.stack}`,
    });
    process.exit(1);
});
const { decks, S17, ENHC, baseSettings, dataDir } = workerData;
parentPort.postMessage({ type: "log", msg: `dataDir: ${dataDir}` });
const rules = `${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`;
let settings = { ...baseSettings, decks, S17, ENHC, DAS: true };
let instance = CalculatorLogic.create(settings, dataDir);
parentPort.postMessage({ type: "log", msg: `Starting DAS: ${rules}` });
const DAS = [];
for (let upCard = 1; upCard <= 10; upCard++) {
    const upcardResults = [];
    for (let totalTarget = 4; totalTarget <= 21; totalTarget++) {
        const candidateHands = instance.runHandSim(totalTarget, upCard, false).allHands;
        for (const hand of candidateHands) {
            if (instance.total(hand.hand) === totalTarget) {
                const handStr = hand.hand
                    .map((c) => c.rank)
                    .join(",");
                parentPort.postMessage({
                    type: "log",
                    msg: `DAS ${rules} | hand: [${handStr}] vs upCard: ${upCard}`,
                });
                upcardResults.push([
                    hand.hand,
                    hand.totalProb,
                    instance.calcSplit(hand.hand, upCard),
                ]);
            }
        }
    }
    DAS.push(upcardResults);
}
settings = { ...baseSettings, decks, S17, ENHC, DAS: false };
instance = CalculatorLogic.create(settings, dataDir);
parentPort.postMessage({ type: "log", msg: `Starting nDAS: ${rules}` });
const nDAS = [];
for (let upCard = 1; upCard <= 10; upCard++) {
    const upcardResults = [];
    for (let totalTarget = 4; totalTarget <= 21; totalTarget++) {
        const candidateHands = instance.runHandSim(totalTarget, upCard, false).allHands;
        for (const hand of candidateHands) {
            if (instance.total(hand.hand) === totalTarget) {
                const handStr = hand.hand
                    .map((c) => c.rank)
                    .join(",");
                parentPort.postMessage({
                    type: "log",
                    msg: `nDAS ${rules} | hand: [${handStr}] vs upCard: ${upCard}`,
                });
                upcardResults.push([
                    hand.hand,
                    hand.totalProb,
                    instance.calcSplit(hand.hand, upCard),
                ]);
            }
        }
    }
    nDAS.push(upcardResults);
}
parentPort.postMessage({ type: "log", msg: `Done: ${rules}` });
parentPort.postMessage({ decks, S17, ENHC, DAS, nDAS });
