import { workerData, parentPort } from "worker_threads";
import { CalculatorLogic } from "./CalculatorLogicDownload.js";

process.on("uncaughtException", (err) => {
  parentPort!.postMessage({
    type: "log",
    msg: `WORKER CRASH: ${err.message}\n${err.stack}`,
  });
  process.exit(1);
});

const { decks, S17, ENHC, baseSettings, dataDir } = workerData;
const rules = `${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`;
let settings = { ...baseSettings, decks, S17, ENHC, DAS: true };
let instance = CalculatorLogic.create(settings, dataDir);
parentPort!.postMessage({ type: "log", msg: `Starting DAS: ${rules}` });

const DAS: any[] = [];
for (let upCard = 1; upCard <= 10; upCard++) {
  const upcardResults: any[] = [];
  for (let pairVal = 1; pairVal <= 10; pairVal++) {
    parentPort!.postMessage({
      type: "log",
      msg: `DAS ${rules} | pair ${pairVal === 1 ? "A" : pairVal} vs ${upCard === 1 ? "A" : upCard}`,
    });
    const EV = instance.calcSplit(
      [{ rank: pairVal }, { rank: pairVal }],
      upCard,
    );
    upcardResults.push([[{ rank: pairVal }, { rank: pairVal }], EV]);
  }
  DAS.push(upcardResults);
}

settings = { ...baseSettings, decks, S17, ENHC, DAS: false };
instance = CalculatorLogic.create(settings, dataDir);

parentPort!.postMessage({ type: "log", msg: `Starting nDAS: ${rules}` });

const nDAS: any[] = [];
for (let upCard = 1; upCard <= 10; upCard++) {
  const upcardResults: any[] = [];
  for (let pairVal = 1; pairVal <= 10; pairVal++) {
    parentPort!.postMessage({
      type: "log",
      msg: `nDAS ${rules} | pair ${pairVal === 1 ? "A" : pairVal} vs ${upCard === 1 ? "A" : upCard}`,
    });
    const EV = instance.calcSplit(
      [{ rank: pairVal }, { rank: pairVal }],
      upCard,
    );
    upcardResults.push([[{ rank: pairVal }, { rank: pairVal }], EV]);
  }
  nDAS.push(upcardResults);
}

parentPort!.postMessage({ type: "log", msg: `Done: ${rules}` });
parentPort!.postMessage({ decks, S17, ENHC, DAS, nDAS });
