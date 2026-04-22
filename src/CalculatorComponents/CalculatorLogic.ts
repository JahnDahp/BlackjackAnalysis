import { CalculatorLogicBase } from "./CalculatorLogicBase.js";

export class CalculatorLogic extends CalculatorLogicBase {
  static async create(dealerSettings: any): Promise<CalculatorLogic> {
    const instance = new CalculatorLogic(dealerSettings);
    const [dealerData, standData, hitData, doubleData, splitData] =
      await Promise.all([
        fetch("/data/dealer.json").then((res) => res.json()),
        fetch("/data/stand.json").then((res) => res.json()),
        fetch("/data/hit.json").then((res) => res.json()),
        fetch("/data/double.json").then((res) => res.json()),
        fetch("/data/split.json").then((res) => res.json()),
      ]);
    instance.dealerData = dealerData;
    instance.standData = standData;
    instance.hitData = hitData;
    instance.doubleData = doubleData;
    instance.splitData = splitData;
    return instance;
  }
}
