import "../PlayStyles/SettingsBody.css";
import "../CalculatorStyles/CalculatorSettingsBody.css";
import { DealerSettingsObject, Setting } from "../SettingsObjects";
import Dropdown from "../PlayComponents/Dropdown";
import { CalculatorLogic } from "./CalculatorLogic";
import React, { useEffect, useState } from "react";
import Button from "../GameComponents/Button";
import PlayingCard from "../GameComponents/PlayingCard";
import OddTableCell from "./OddTableCell";

function getPercent(value: number | null, baseDecimals: number): string {
  if (value === null || value === undefined) return "";
  const percent = value * 100;
  const integerDigits = Math.floor(Math.abs(percent)).toString().length;
  const adjustedDecimals = Math.max(baseDecimals + 1 - integerDigits, 0);
  return percent.toFixed(adjustedDecimals) + "%";
}

interface Card {
  rank: number;
}

interface Props {
  dealerSettings: Setting[];
  dealerSettingValues: DealerSettingsObject;
  dealerUpdateSetting: (updates: Partial<DealerSettingsObject>) => void;
}

const HandSettings = ({
  dealerSettings,
  dealerSettingValues,
  dealerUpdateSetting,
}: Props) => {
  const [showError, setShowError] = useState<boolean>(false);
  const [table, setTable] = useState<(number | string)[][]>([]);
  const [choiceLabels, setChoiceLabels] = useState<string[]>([]);
  const [hand, setHand] = useState<Card[]>([]);
  const [dealerData, setDealerData] = useState<any>(null);
  const [standData, setStandData] = useState<any>(null);
  const [hitData, setHitData] = useState<any>(null);
  const [doubleData, setDoubleData] = useState<any>(null);
  const [splitData, setSplitData] = useState<any>(null);
  const [dealerProbabilities, setDealerProbabilities] =
    useState<CalculatorLogic | null>(null);

  useEffect(() => {
    async function loadProbabilities() {
      const prob = await CalculatorLogic.create(dealerSettingValues);
      setDealerProbabilities(prob);
    }
    loadProbabilities();
  }, [dealerSettingValues]);

  useEffect(() => {
    fetch("/data/dealer.json")
      .then((res) => res.json())
      .then(setDealerData);
    fetch("/data/stand.json")
      .then((res) => res.json())
      .then(setStandData);
    fetch("/data/hit.json")
      .then((res) => res.json())
      .then(setHitData);
    fetch("/data/double.json")
      .then((res) => res.json())
      .then(setDoubleData);
    fetch("/data/split.json")
      .then((res) => res.json())
      .then(setSplitData);
  }, []);

  if (!dealerData) return <div className="settings-body">Loading...</div>;
  if (!standData) return <div className="settings-body">Loading...</div>;
  if (!hitData) return <div className="settings-body">Loading...</div>;
  if (!doubleData) return <div className="settings-body">Loading...</div>;
  if (!splitData) return <div className="settings-body">Loading...</div>;

  const upCardLabels = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"];
  const keyMap = ["decks", "S17", "ENHC", "DAS", "BJPay", "drawAces"] as const;

  const getInitialValue = (index: number, options: string[]): string => {
    const key = keyMap[index];
    const value = dealerSettingValues[key];
    switch (key) {
      case "decks":
        switch (value) {
          case 1:
            return "1 deck";
          case 2:
            return "2 decks";
          case 4:
            return "4 decks";
          case 6:
            return "6 decks";
          case 8:
            return "8 decks";
          default:
            return String(value);
        }
      case "S17":
        return value ? "Stay soft 17" : "Hit soft 17";
      case "drawAces":
      case "ENHC":
      case "DAS":
        return value ? "Yes" : "No";
      case "BJPay":
        switch (value) {
          case 1.5:
            return "3:2";
          case 1.2:
            return "6:5";
          case 2:
            return "2:1";
          case 1:
            return "1:1";
          default:
            return String(value);
        }
      default:
        return options[0];
    }
  };

  const parseValues = (value: string, key: string) => {
    let parsedValue: any = value;
    if (key === "decks") {
      parsedValue =
        value === "1 deck"
          ? 1
          : value === "2 decks"
            ? 2
            : value === "4 decks"
              ? 4
              : value === "6 decks"
                ? 6
                : 8;
    } else if (key === "S17") {
      parsedValue = value === "Stay soft 17";
    } else if (
      key === "ENHC" ||
      key === "DAS" ||
      key === "LS" ||
      key === "RSA" ||
      key === "drawAces"
    ) {
      parsedValue = value === "Yes";
    } else if (key === "doubles") {
      switch (value) {
        case "8, 9, 10, 11":
          parsedValue = [8, 9, 10, 11];
          break;
        case "9, 10, 11":
          parsedValue = [9, 10, 11];
          break;
        case "10, 11":
          parsedValue = [10, 11];
          break;
        case "Any total":
          parsedValue = [
            2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
            21,
          ];
          break;
      }
    } else if (key === "splits") {
      parsedValue = parseInt(value) - 1;
    } else if (key === "BJPay") {
      parsedValue =
        value === "3:2"
          ? 1.5
          : value === "6:5"
            ? 1.2
            : value === "2:1"
              ? 2
              : value === "1:1"
                ? 1
                : parseFloat(value);
    }
    return parsedValue;
  };

  const isValidHand = () => {
    const total = hand.reduce((acc, curr) => acc + curr.rank, 0);
    if (total > 21) return true;
    if (hand.length < 2) return true;
    for (let i = 1; i < 10; i++) {
      let repeatedRanks = 0;
      for (let card of hand) {
        if (card.rank === i) repeatedRanks++;
      }
      if (repeatedRanks > dealerSettingValues.decks * 4) return true;
    }
    return false;
  };

  const getBestEV = (upCardResults: (number | string)[]) => {
    const numbers = upCardResults.filter(
      (v): v is number => typeof v === "number",
    );
    const max = Math.max(...numbers);
    return max === numbers[0]
      ? "Stand"
      : max === numbers[1]
        ? "Hit"
        : max === numbers[2]
          ? "Double"
          : max === numbers[3]
            ? "Split"
            : "Surr";
  };

  const getTableValues = async () => {
    const sim = await CalculatorLogic.create(dealerSettingValues);
    setDealerProbabilities(sim);

    if (!sim) return null;
    const table = [];
    for (let i = 2; i <= 11; i++) {
      const upCard = i === 11 ? 1 : i;
      let upCardResults: (number | string)[] = [];
      const isPair = hand.length === 2 && hand[0].rank === hand[1].rank;
      if (isPair) {
        const splitEV = sim.calcSplitEV(sim.getData(hand, upCard, splitData));
        upCardResults = [
          sim.calcStandEV(hand, sim.getData(hand, upCard, standData)),
          sim.calcHitEV(sim.getData(hand, upCard, hitData)),
          sim.calcDoubleEV(sim.getData(hand, upCard, doubleData)),
          splitEV,
          -0.5,
        ];
        setChoiceLabels(["Stand", "Hit", "Double", "Split", "Surr", "Best"]);
      } else {
        upCardResults = [
          sim.calcStandEV(hand, sim.getData(hand, upCard, standData)),
          sim.calcHitEV(sim.getData(hand, upCard, hitData)),
          sim.calcDoubleEV(sim.getData(hand, upCard, doubleData)),
          -0.5,
        ];
        setChoiceLabels(["Stand", "Hit", "Double", "Surr", "Best"]);
      }
      upCardResults.push(getBestEV(upCardResults));
      table.push(upCardResults);
    }
    return table;
  };

  const runSimulation = async () => {
    const tableValues = await getTableValues();
    if (tableValues) {
      setTable(tableValues);
    }
  };

  return (
    <div className="settings-body">
      {dealerSettings.map(({ label, options }, index) => {
        const key = keyMap[index];
        const initialValue = getInitialValue(index, options);
        return (
          <div className="settings-body-title" key={index}>
            <span className="settings-body-label">{label}</span>
            <div className="settings-body-dropdown">
              <Dropdown
                list={options}
                initial={initialValue}
                onSelect={(value) => {
                  dealerUpdateSetting({
                    [key]: parseValues(value, key),
                  });
                }}
              />
            </div>
          </div>
        );
      })}
      <div className="settings-body-title" key="select-cards">
        <span style={{ textWrap: "nowrap" }}>{"Select player cards"}</span>
        <div className="settings-body-playing-cards">
          {[...Array(10)].map((_, i) => (
            <div
              className="settings-body-playing-card"
              key={`select-card-${i}`}
            >
              <PlayingCard
                rank={i + 1}
                suit="hearts"
                onClick={() => {
                  setHand([...hand, { rank: i + 1 }]);
                }}
              />
            </div>
          ))}
        </div>
      </div>
      {hand?.length > 0 && (
        <div className="settings-body-title" key="hand-cards">
          <div className="settings-body-playing-cards">
            {hand.map((_, i) => (
              <div
                className="settings-body-playing-card"
                key={`hand-card-${i}`}
              >
                <PlayingCard
                  rank={hand[i].rank}
                  suit="hearts"
                  onClick={() => {
                    setHand(hand.slice(0, i).concat(hand.slice(i + 1)));
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
      {dealerProbabilities && (
        <div className="settings-body-title" key={"button"}>
          <span className="settings-body-label">{"Run hand simulation"}</span>
          <div className="settings-body-button">
            <Button
              name="Run"
              onClick={() => {
                const invalid = isValidHand();
                setShowError(invalid);
                if (invalid) return;
                runSimulation();
              }}
              width="160px"
            />
          </div>
        </div>
      )}
      {showError && (
        <div className="settings-body-title" key="player-cards">
          <span style={{ textWrap: "nowrap" }}>{"Invalid hand"}</span>
        </div>
      )}
      {table.length > 0 && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Choice" key={"hand-ev"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {choiceLabels.map((outLabel, outIndex) => (
              <React.Fragment key={`choice-${outIndex}`}>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={
                      typeof table[upIndex][outIndex] === "number"
                        ? String(getPercent(table[upIndex][outIndex] ?? 0, 4))
                        : table[upIndex][outIndex]
                    }
                  />
                ))}
              </React.Fragment>
            ))}
          </>
        </div>
      )}
    </div>
  );
};

export default HandSettings;
