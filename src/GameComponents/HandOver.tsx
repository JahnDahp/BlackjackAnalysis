import { useState } from "react";
import Textbox from "../PlayComponents/Textbox";
import { BankrollSettingsObject } from "../SettingsObjects";
import { BlackjackGame } from "./Blackjack";
import Button from "./Button";
import "../GameStyles/Game.css";

interface Props {
  blackjackGame: BlackjackGame | null;
  bankrollSettingsObject: BankrollSettingsObject;
  setShowStrategyErrorMessage: (val: boolean) => void;
  setShowDeviationErrorMessage: (val: boolean) => void;
  setBlackjackGame: React.Dispatch<React.SetStateAction<BlackjackGame | null>>;
}

const HandOver = ({
  blackjackGame,
  bankrollSettingsObject,
  setShowStrategyErrorMessage,
  setShowDeviationErrorMessage,
  setBlackjackGame,
}: Props) => {
  const [betInput, setBetInput] = useState("");

  function refreshGame() {
    setBlackjackGame((prev) =>
      Object.assign(Object.create(Object.getPrototypeOf(prev!)), prev),
    );
  }

  function clampBetValue(raw: string): string {
    let bet = parseFloat(raw);
    if (isNaN(bet) || bet <= bankrollSettingsObject.tableMin)
      return String(bankrollSettingsObject.tableMin);
    bet -= bet % 5;
    bet = Math.max(bet, bankrollSettingsObject.tableMin);
    bet = Math.min(bet, bankrollSettingsObject.tableMax);
    bet = Math.min(bet, blackjackGame?.bankroll ?? bet);
    bet -= bet % 5;
    return String(bet);
  }

  return (
    blackjackGame?.handOver && (
      <div>
        {blackjackGame.nextShuffle && (
          <div className="game-play-bar" style={{ width: "212px" }}>
            <h1 className="game-label" style={{ marginTop: "40px" }}>
              {`Shuffle on next hand`}
            </h1>
          </div>
        )}
        <div className="game-play-bar" style={{ width: "212px" }}>
          {blackjackGame.bankroll < bankrollSettingsObject.tableMin ? (
            <h1
              className="game-label"
              style={{ top: "50%" }}
            >{`Not enough money`}</h1>
          ) : (
            <>
              <Button
                name="Play"
                onClick={() => {
                  blackjackGame.initialBet = parseInt(clampBetValue(betInput));
                  blackjackGame.choice = BlackjackGame.PLAY_GAME;
                  blackjackGame.playGame();
                  setShowStrategyErrorMessage(false);
                  setShowDeviationErrorMessage(false);
                  refreshGame();
                }}
                width="100px"
              />
              <Textbox
                value={betInput}
                placeholder="Bet"
                onChange={(val) => setBetInput(val)}
                onBlur={() => setBetInput(clampBetValue(betInput))}
              />
            </>
          )}
        </div>
      </div>
    )
  );
};

export default HandOver;
