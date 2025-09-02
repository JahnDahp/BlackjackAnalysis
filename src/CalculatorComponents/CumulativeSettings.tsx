import "../PlayStyles/SettingsBody.css";
import "../CalculatorStyles/CalculatorSettingsBody.css";
import { DealerSettingsObject, Setting } from "../SettingsObjects";
import Dropdown from "../PlayComponents/Dropdown";
import { Probabilities } from "./Dealer";
import { useEffect, useState } from "react";
import Button from "../GameComponents/Button";
import OddTableCell from "./OddTableCell";

function getPercent(value: number | null, baseDecimals: number): string {
  if (value === null || value === undefined) return "";
  const percent = value * 100;
  const integerDigits = Math.floor(Math.abs(percent)).toString().length;
  const adjustedDecimals = Math.max(baseDecimals + 1 - integerDigits, 0);
  return percent.toFixed(adjustedDecimals) + "%";
}

interface Props {
  dealerSettings: Setting[];
  dealerSettingValues: DealerSettingsObject;
  dealerUpdateSetting: (updates: Partial<DealerSettingsObject>) => void;
}

const CumulativeSettings = ({
  dealerSettings,
  dealerSettingValues,
  dealerUpdateSetting,
}: Props) => {
  const [dealerData, setDealerData] = useState<any>(null);
  const [standData, setStandData] = useState<any>(null);
  const [hitData, setHitData] = useState<any>(null);
  const [doubleData, setDoubleData] = useState<any>(null);
  const [splitData, setSplitData] = useState<any>(null);
  const [dealerProbs, setDealerProbs] = useState<any>(null);
  const [standProbs, setStandProbs] = useState<any>(null);
  const [hitProbs, setHitProbs] = useState<any>(null);
  const [doubleProbs, setDoubleProbs] = useState<any>(null);
  const [splitProbs, setSplitProbs] = useState<any>(null);
  const [dealerProbabilities, setDealerProbabilities] =
    useState<Probabilities | null>(null);

  useEffect(() => {
    async function loadProbabilities() {
      const prob = await Probabilities.create(dealerSettingValues);
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

  const keyMap = [
    "decks",
    "S17",
    "ENHC",
    "DAS",
    "doubles",
    "splits",
    "LS",
    "BJPay",
    "RSA",
    "drawAces",
  ] as const;
  const upCardLabels = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10"];
  const outcomeLabels = ["Bust", "17", "18", "19", "20", "21", "BJ"];
  const hardHandLabels = [
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
  ];
  const hardHandDoubleLabels = [
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
  ];
  const softHandLabels = [
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
  ];
  const pairLabels = [
    "A,A",
    "2,2",
    "3,3",
    "4,4",
    "5,5",
    "6,6",
    "7,7",
    "8,8",
    "9,9",
    "X,X",
  ];

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
      case "doubles":
        if (Array.isArray(value)) {
          const str = value.join(", ");
          if (str === "8, 9, 10, 11") return "8, 9, 10, 11";
          if (str === "9, 10, 11") return "9, 10, 11";
          if (str === "10, 11") return "10, 11";
          if (
            str ===
            "2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21"
          )
            return "Any total";
        }
        return options[0];
      case "splits":
        switch (value) {
          case 0:
            return "1 hands";
          case 1:
            return "2 hands";
          case 3:
            return "4 hands";
          case 5:
            return "6 hands";
          case 7:
            return "8 hands";
          default:
            return String(value);
        }
      case "LS":
      case "RSA":
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
    } else if (key == "splits") {
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

  const runSimulation = async () => {
    const sim = await Probabilities.create(dealerSettingValues);
    setDealerProbabilities(sim);
    setDealerProbs(sim.getDealerData());
    setStandProbs(sim.getCumulativeProbs("stand"));
    setHitProbs(sim.getCumulativeProbs("hit"));
    setDoubleProbs(sim.getCumulativeProbs("double"));
    setSplitProbs(sim.getSplitProbs());
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
      {dealerProbabilities && (
        <div className="settings-body-title" key={"button"}>
          <span className="settings-body-label">
            {"Run cumulative simulation"}
          </span>
          <div className="settings-body-button">
            <Button
              name="Run"
              onClick={() => {
                runSimulation();
              }}
              width="160px"
            />
          </div>
        </div>
      )}
      {dealerProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Dealer" key={"dealer"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {outcomeLabels.map((outLabel, outIndex) => {
              if (outLabel === "BJ" && !dealerSettingValues.ENHC) return;
              return (
                <>
                  <OddTableCell value={outLabel} />
                  {upCardLabels.map((_, upIndex) => (
                    <OddTableCell
                      key={`${outIndex}-${upIndex}`}
                      value={String(
                        getPercent(dealerProbs[upIndex][outIndex], 4)
                      )}
                    />
                  ))}
                </>
              );
            })}
          </>
        </div>
      )}
      {standProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Stand" key={"stand"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {hardHandLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(standProbs?.hard[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {standProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="StandS" key={"stand-s"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {softHandLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(standProbs?.soft[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {hitProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Hit" key={"hit"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {hardHandLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(hitProbs?.hard[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {hitProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="HitS" key={"hit-s"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {softHandLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(hitProbs?.soft[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {doubleProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Double" key={"double"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {hardHandDoubleLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(doubleProbs?.hard[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {doubleProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="DoubleS" key={"double-s"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {softHandLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(
                      getPercent(doubleProbs?.soft[upIndex][outIndex] ?? 0, 4)
                    )}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
      {splitProbs && (
        <div className="calculator-settings-body-table">
          <>
            <OddTableCell value="Splits" key={"split"} />
            {upCardLabels.map((upLabel, upIndex) => (
              <OddTableCell key={`${upIndex}`} value={upLabel} />
            ))}
            {pairLabels.map((outLabel, outIndex) => (
              <>
                <OddTableCell value={outLabel} />
                {upCardLabels.map((_, upIndex) => (
                  <OddTableCell
                    key={`${outIndex}-${upIndex}`}
                    value={String(getPercent(splitProbs[upIndex][outIndex], 4))}
                  />
                ))}
              </>
            ))}
          </>
        </div>
      )}
    </div>
  );
};

export default CumulativeSettings;
