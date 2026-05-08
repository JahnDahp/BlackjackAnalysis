import { Simulator } from "./Simulator.js";
import { DealerSettingsObject } from "../SettingsObjects.js";

const dealerSettings: DealerSettingsObject = {
  decks: 1,
  S17: true,
  ENHC: false,
  DAS: true,
  BJPay: 1.5,
  drawAces: false,
};

async function main() {
  console.log("Building hand compositions...");
  const sim = await Simulator.create(dealerSettings);
  console.log("Done. Starting parallel simulation...\n");
  await sim.calcHSD();
}

main().catch(console.error);
