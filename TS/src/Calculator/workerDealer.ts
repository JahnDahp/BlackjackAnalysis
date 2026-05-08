import { workerData, parentPort } from "worker_threads";
import { Calculator } from "./Calculator.js";

const { decks, S17, ENHC, baseSettings, dataDir } = workerData;
const settings = { ...baseSettings, decks, S17, ENHC };
const instance = Calculator.create(settings, dataDir);

console.log(
  `Starting dealer: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`,
);

const result = instance.runDealerSim(true);

console.log(`Done: ${decks}D ${S17 ? "S17" : "H17"} ${ENHC ? "ENHC" : "US"}`);
parentPort!.postMessage({ decks, S17, ENHC, result });
