import "../PlayStyles/SettingsBody.css";
import { GameSettingsObject, Setting } from "../SettingsObjects";
import Dropdown from "./Dropdown";
import Textbox from "./Textbox";

interface Props {
  gameSettings: Setting[];
  gameSettingValues: GameSettingsObject;
  gameUpdateSetting: (updates: Partial<GameSettingsObject>) => void;
}

const GameSettings = ({
  gameSettings,
  gameSettingValues,
  gameUpdateSetting,
}: Props) => {
  const keyMap = [
    "decks",
    "S17",
    "DAS",
    "doubles",
    "splits",
    "LS",
    "BJPay",
    "RSA",
    "drawAces",
    "pen",
  ] as const;

  const getInitialValue = (index: number, options: string[]): string => {
    const key = keyMap[index];
    const value = gameSettingValues[key];
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
      case "S17":
        return value ? "Stay soft 17" : "Hit soft 17";
      case "DAS":
      case "RSA":
      case "drawAces":
        return value ? "Yes" : "No";
      case "LS":
        return String(value);
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
      case "pen":
        return String(value);
      default:
        return options[0];
    }
  };

  const parseValues = (value: string, key: string) => {
    let parsedValue: any = value;
    if (key == "decks") {
      parsedValue =
        value === "1 deck"
          ? 1
          : value === "2 decks"
            ? 2
            : value === "4 decks"
              ? 4
              : value === "6 decks"
                ? 6
                : value === "8 decks"
                  ? 8
                  : parseFloat(value);
    } else if (key == "splits") {
      parsedValue = parseInt(value) - 1;
    } else if (["S17", "DAS", "RSA", "drawAces"].includes(key)) {
      parsedValue = value === "Yes" || value === "Stay soft 17";
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
    } else if (key == "pen") {
      if (parseInt(value) < 26) parsedValue = 26;
      else if (parseInt(value) > gameSettingValues.decks * 52 - 26)
        parsedValue = gameSettingValues.decks * 52 - 26;
      else parsedValue = parseInt(value);
    }
    console.log(parsedValue);
    return parsedValue;
  };

  return (
    <div className="settings-body">
      {gameSettings.map(({ label, options }, index) => {
        if (index === gameSettings.length - 1) {
          return (
            <div className="settings-body-title" key={index}>
              <span className="settings-body-label">{label}</span>
              <div className="settings-body-textbox">
                <Textbox
                  placeholder={options[0] || "Enter value"}
                  value={String(gameSettingValues.pen)}
                  onChange={(val) => {
                    if (val === "") {
                      gameUpdateSetting({ pen: 0 });
                      return;
                    }
                    const num = parseInt(val);
                    if (!isNaN(num)) {
                      gameUpdateSetting({ pen: num });
                    }
                  }}
                  onBlur={() => {
                    let current, min, max: number;
                    current = gameSettingValues.pen;
                    min = 26;
                    max = gameSettingValues.decks * 52 - 26;
                    let clamped = Math.min(Math.max(current, min), max);
                    if (clamped !== current) {
                      gameUpdateSetting({ pen: clamped });
                    }
                  }}
                />
              </div>
            </div>
          );
        }
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
                  if (key === "decks") {
                    const newDecks = parseValues(value, "decks") as number;
                    const minPen = 26;
                    const maxPen = newDecks * 52 - 26;
                    const currentPen = gameSettingValues.pen;
                    const clampedPen = Math.min(
                      Math.max(currentPen, minPen),
                      maxPen,
                    );
                    gameUpdateSetting({
                      decks: newDecks,
                      pen: clampedPen,
                    });
                  } else {
                    gameUpdateSetting({ [key]: parseValues(value, key) });
                  }
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default GameSettings;
