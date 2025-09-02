import { useState } from "react";
import "../PlayStyles/Play.css";
import Navbar from "../HomeComponents/Navbar";
import { DealerSettingsObject } from "../SettingsObjects";
import CumulativeSettings from "./CumulativeSettings";
import SettingsCard from "../PlayComponents/SettingsCard";
import HandSettings from "./HandSettings";

interface Props {
  dealerSettingsObject: DealerSettingsObject;
  setDealerSettingsObject: React.Dispatch<
    React.SetStateAction<DealerSettingsObject>
  >;
}

const Calculator = ({
  dealerSettingsObject,
  setDealerSettingsObject,
}: Props) => {
  const [selectedHeader, setSelectedHeader] = useState(0);

  const headers = ["Cumulative", "Hand"];

  const calculatorSettings = [
    {
      label: "Number of decks",
      options: ["1 deck", "2 decks", "4 decks", "6 decks", "8 decks"],
    },
    {
      label: "Dealer action on soft 17",
      options: ["Stay soft 17", "Hit soft 17"],
    },
    {
      label: "European no hole card",
      options: ["Yes", "No"],
    },
    { label: "Player may double after splitting", options: ["Yes", "No"] },
    {
      label: "Player may double on",
      options: ["8, 9, 10, 11", "9, 10, 11", "10, 11", "Any total"],
    },
    {
      label: "Player can split to",
      options: ["0 hands", "2 hands", "4 hands", "6 hands", "8 hands"],
    },
    { label: "Late surrender allowed", options: ["Yes", "No"] },
    { label: "Blackjack pays", options: ["3:2", "6:5", "2:1", "1:1"] },
    { label: "Player can resplit aces", options: ["Yes", "No"] },
    { label: "Player can draw on split aces", options: ["Yes", "No"] },
  ];

  const renderContent = () => {
    switch (selectedHeader) {
      case 0:
        return (
          <CumulativeSettings
            dealerSettings={calculatorSettings}
            dealerSettingValues={dealerSettingsObject}
            dealerUpdateSetting={(updates) =>
              setDealerSettingsObject((prev) => ({ ...prev, ...updates }))
            }
          />
        );
      case 1:
        return (
          <HandSettings
            dealerSettings={calculatorSettings}
            dealerSettingValues={dealerSettingsObject}
            dealerUpdateSetting={(updates) =>
              setDealerSettingsObject((prev) => ({ ...prev, ...updates }))
            }
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="play">
      <Navbar />
      <div className="play-content">
        <div className="play-settings-card">
          <SettingsCard
            headers={headers}
            selectedHeader={selectedHeader}
            setSelectedHeader={setSelectedHeader}
          />
        </div>
        <div className="play-settings-body">{renderContent()}</div>
      </div>
    </div>
  );
};

export default Calculator;
