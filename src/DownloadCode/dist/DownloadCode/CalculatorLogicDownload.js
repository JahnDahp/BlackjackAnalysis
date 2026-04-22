import * as fs from "fs";
import * as path from "path";
import { CalculatorLogicBase } from "../CalculatorComponents/CalculatorLogicBase.js";
export class CalculatorLogic extends CalculatorLogicBase {
    static create(dealerSettings, dataDir) {
        const instance = new CalculatorLogic(dealerSettings);
        const read = (file) => JSON.parse(fs.readFileSync(path.join(dataDir, file), "utf-8"));
        instance.dealerData = read("dealer.json");
        instance.standData = read("stand.json");
        instance.hitData = read("hit.json");
        instance.doubleData = read("double.json");
        instance.splitData = read("split.json");
        return instance;
    }
}
